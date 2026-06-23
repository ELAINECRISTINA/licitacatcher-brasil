from datetime import datetime, timedelta
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException,
    StaleElementReferenceException
)
import re
from dotenv import load_dotenv
load_dotenv()

import queue
import numpy as np
import threading
import time
import requests
import os

ILLEGAL_CHARACTERS_RE = re.compile(r'[\000-\010\013\014\016-\037]')

# ════════════════════════════════════════════════════════════════
# ⚙️  CONSTANTES
# ════════════════════════════════════════════════════════════════
BASE_XPATH            = '//*[@id="main-content"]/pncp-item-detail/div'
BTN_PROXIMA_ITENS     = '//pncp-pagination-table//div[6]/button[2]'
BTN_PROXIMA_ITENS_ALT = '//pncp-pagination-table//button[contains(@class,"next")]'
MAX_PAGINAS_LISTA     = 20

LOAD_XPATHS = [
    f'{BASE_XPATH}/div[3]/div[1]/p/strong',
    f'{BASE_XPATH}/div[3]/div[1]/p/span',
    f'{BASE_XPATH}/div[1]',
    f'{BASE_XPATH}/div[2]',
]

TERMOS_ITEM = [t.lower() for t in [
    "Pulverizador costal",
    "Pulverizador elétrico",
    "Jacto",
    "Guarany",
    "Felco",
    "Matabi",
    "Nagano",
    "Tesoura de poda",
    "Podador",
    "Aplicador de grânulos",
    "Adubadeira",
    "Espalhador de fertilizante",
    "Válvula reguladora",
    "Barra 500",
    "EPI agrícola",
]]

EXCL_ITEM = [t.lower() for t in [
    'limpa-vidro', 'limpa vidro', 'limpador de vidro',
    'detergente', 'sabão', 'desinfetante', 'desentupidor',
    'lauril', 'sulfato de sódio', 'tensoativo',
    'com gatilho', 'borrifador', 'aspecto físico: líquido',
    'roçadeira', 'rocadeira', 'motosserra',
    'pistão', 'pistao', 'virabrequim', 'carburador',
    'embreagem', 'vela de ignição',
    'corrente de motosserra', 'sabre de motosserra',
    'cirúrgic', 'cirurgic', 'bisturi', 'veterinár',
    'tesoura de costura', 'tesoura escolar',
    'tesoura de cabeleireiro', 'tesoura para unhas',
    'tesoura para papel',
    '500 ml', '500ml', '1 litro', '1litro',
    'multiuso', 'uso doméstico', 'automotivo',
    'serviço de', 'contratação de serviço', 'mão de obra',
    'pincel', 'caneta', 'material de escritório',
    'eletricista', 'plantão', 'óleo vegetal', 'óleo essencial',
    'óleo de', 'grape seed', 'plantadeira', 'freio', 'medicinais', 'gases',
    'talha', 'guincho', 'cultivador'
]]

CONTEXTO_AGRICOLA = [
    'pulveriz', 'costal', 'agrícol', 'agro',
    'jacto', 'guarany', 'matabi', 'nagano',
    'spray', 'vazão', 'pressão', 'bico',
    'calda', 'defensivo', 'insumo',
]

TERMOS_AMBIGUOS = {
    'válvula reguladora'              : CONTEXTO_AGRICOLA,
    'válvula de fluxo'                : CONTEXTO_AGRICOLA,
    'epi'                             : CONTEXTO_AGRICOLA,
    'iso 27065'                       : CONTEXTO_AGRICOLA,
    'equipamento de proteção individual': CONTEXTO_AGRICOLA,
}

# ════════════════════════════════════════════════════════════════
# ⚙️  CONFIGURAÇÕES DO CHROME
# ════════════════════════════════════════════════════════════════
chrome_options = Options()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("--blink-settings=imagesEnabled=false")
prefs = {
    "profile.managed_default_content_settings.images"      : 2,
    "profile.default_content_setting_values.notifications" : 2,
    "profile.managed_default_content_settings.stylesheets" : 2,
    "profile.managed_default_content_settings.javascript"  : 1,
}
chrome_options.add_experimental_option("prefs", prefs)

link = "https://pncp.gov.br/app/editais?pagina=1&q=&status=recebendo_proposta"

# ════════════════════════════════════════════════════════════════
# 📦  LISTAS GLOBAIS + LOCK DE THREAD
# ════════════════════════════════════════════════════════════════
_lock = threading.Lock()

local_list                : list = []
orgao_list                : list = []
unidade_list              : list = []
modalidade_list           : list = []
amparo_list               : list = []
tipo_list                 : list = []
disputa_list              : list = []
registro_list             : list = []
data_divulgacao_PNCP_list : list = []
situação_list             : list = []
inicio_list               : list = []
fim_list                  : list = []
id_PNCP_list              : list = []
fonte_list                : list = []
objeto_list               : list = []
termo_pesquisado          : list = []
title_list                : list = []
docs                      : list = []
item_desc_list            : list = []
item_quantity_list        : list = []
item_value_tot_list       : list = []
item_value_list           : list = []
item_licitacao_id_list    : list = []
value_is_present          : list = []


def limpa_variaveis():
    global local_list, orgao_list, unidade_list, modalidade_list, amparo_list
    global tipo_list, disputa_list, registro_list, data_divulgacao_PNCP_list
    global situação_list, inicio_list, fim_list, id_PNCP_list, fonte_list
    global objeto_list, termo_pesquisado, title_list, docs, item_desc_list
    global item_quantity_list, item_value_tot_list, item_value_list
    global item_licitacao_id_list, value_is_present

    local_list = [];               orgao_list = [];             unidade_list = []
    modalidade_list = [];          amparo_list = [];            tipo_list = []
    disputa_list = [];             registro_list = [];          data_divulgacao_PNCP_list = []
    situação_list = [];            inicio_list = [];            fim_list = []
    id_PNCP_list = [];             fonte_list = [];             objeto_list = []
    termo_pesquisado = [];         title_list = [];             docs = []
    item_desc_list = [];           item_quantity_list = [];     item_value_tot_list = []
    item_value_list = [];          item_licitacao_id_list = []; value_is_present = []


# ════════════════════════════════════════════════════════════════
# 🛠️  FUNÇÕES UTILITÁRIAS
# ════════════════════════════════════════════════════════════════
def limpa_arquivos():
    arquivos   = os.listdir("./files")
    licitacoes = [a for a in arquivos if "licitacoes" in a]
    produtos   = [a for a in arquivos if "produtos"   in a]

    licitacoes_df = []
    for path in licitacoes:
        try:
            licitacoes_df.append(pd.read_excel(f"./files/{path}"))
        except Exception:
            print("Erro no arquivo:", path)
    for path in licitacoes:
        if 'all' not in path:
            os.remove(f"./files/{path}")
    pd.concat(licitacoes_df, ignore_index=True).to_excel(
        "./files/licitacoes_all.xlsx", index=False
    )

    produtos_df = []
    for path in produtos:
        try:
            produtos_df.append(pd.read_excel(f"./files/{path}"))
        except Exception:
            print("Erro no arquivo:", path)
    for path in produtos:
        if 'all' not in path:
            os.remove(f"./files/{path}")
    pd.concat(produtos_df, ignore_index=True).to_excel(
        "./files/produtos_all.xlsx", index=False
    )


def clean_string(value):
    if isinstance(value, str):
        return re.sub(ILLEGAL_CHARACTERS_RE, '', value)
    return value


def safe_str(val):
    if isinstance(val, float):
        return np.nan
    return str(val) if val else np.nan


def limpar_titulo(texto):
    if not texto:
        return ""
    texto = re.sub(r'\s*Última atualização.*', '', texto,
                   flags=re.IGNORECASE | re.DOTALL)
    texto = re.sub(r'\s*Acessar\s+\S.*', '', texto,
                   flags=re.IGNORECASE)
    return texto.strip()


def limpar_objeto(texto):
    if not texto:
        return ""
    return re.sub(r'^Objeto:\s*', '', texto, flags=re.IGNORECASE).strip()


# ════════════════════════════════════════════════════════════════
# ✅  get_el_text COM RETRY PARA StaleElementReferenceException
# ════════════════════════════════════════════════════════════════
def get_el_text(driver, xpath, default=np.nan, retries=3):
    for tentativa in range(retries):
        try:
            return driver.find_element(By.XPATH, xpath).text.strip()
        except StaleElementReferenceException:
            if tentativa < retries - 1:
                time.sleep(0.5)
                continue
            return default
        except NoSuchElementException:
            return default
    return default


def get_el_span(driver, xpath_p, indice=1, default=np.nan):
    try:
        return driver.find_element(
            By.XPATH, f"{xpath_p}/span[{indice}]"
        ).text.strip()
    except (NoSuchElementException, StaleElementReferenceException):
        return default


# ════════════════════════════════════════════════════════════════
# 📅  COMPARAÇÃO DE DATA
# ════════════════════════════════════════════════════════════════
def comparar_data(data_str, dia_alvo):
    try:
        data_obj = datetime.strptime(data_str.strip(), "%d/%m/%Y")
        alvo_obj = datetime.strptime(dia_alvo.strip(), "%d/%m/%Y")
        if data_obj == alvo_obj:
            return 'alvo'
        elif data_obj > alvo_obj:
            return 'novo'
        else:
            return 'antigo'
    except Exception:
        return 'erro'


# ════════════════════════════════════════════════════════════════
# 🛠️  PAGINAÇÃO DA TABELA DE ITENS
# ════════════════════════════════════════════════════════════════
def botao_itens_habilitado(driver):
    for xpath in [BTN_PROXIMA_ITENS, BTN_PROXIMA_ITENS_ALT]:
        try:
            btn = driver.find_element(By.XPATH, xpath)
            pai = btn.find_element(By.XPATH, '..')
            desabilitado = (
                btn.get_attribute("disabled") == "true"
                or "disabled" in (pai.get_attribute("class") or "")
                or not btn.is_enabled()
            )
            if not desabilitado:
                return btn
        except (NoSuchElementException, StaleElementReferenceException):
            continue
    return None


def clicar_proxima_pagina_itens(driver, btn):
    try:
        driver.execute_script(
            "arguments[0].scrollIntoView({block:'center'});", btn
        )
        time.sleep(0.5)
        try:
            btn.click()
        except (ElementClickInterceptedException, StaleElementReferenceException):
            driver.execute_script("arguments[0].click();", btn)
        time.sleep(3)
        return True
    except Exception as e:
        print(f"  ⚠️  Erro ao avançar página de itens: {e}")
        return False


# ════════════════════════════════════════════════════════════════
# 🛠️  FUNÇÕES AUXILIARES
# ════════════════════════════════════════════════════════════════
def catch_append(driver, xpath, list_to_append):
    try:
        list_to_append.append(
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, xpath))
            ).text
        )
    except Exception:
        list_to_append.append(np.nan)


def is_equal(id_PNCP_list, href):
    def process_id(id_PNCP):
        id_PNCP    = id_PNCP.split("-")
        del id_PNCP[1]
        id_PNCP[1] = id_PNCP[1].split("/")
        temp           = id_PNCP[1][0].replace("0", "")
        id_PNCP[1][0]  = id_PNCP[1][1]
        id_PNCP[1][1]  = temp
        return '/'.join(
            [str(i) if isinstance(i, str) else '/'.join(i) for i in id_PNCP]
        )

    processed_ids = [process_id(i) for i in id_PNCP_list]
    href = ''.join(c for c in href if not c.isalpha())
    sv = 0
    for i, c in enumerate(href):
        if c.isdigit():
            break
        sv += 1
    href = href[sv:]
    return any(pid == href for pid in processed_ids)


def click_and_catch_edital(driver):
    docs_temp: list = []
    try:
        button_arquivos = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH,
                '//*[@id="main-content"]/pncp-item-detail/div'
                '/pncp-tab-set/div/nav/ul/li[2]/button'
            ))
        )
        driver.execute_script("arguments[0].focus();", button_arquivos)
        driver.execute_script("arguments[0].click();", button_arquivos)

        c = 1
        while True:
            try:
                fp = (
                    f'//*[@id="main-content"]/pncp-item-detail/div/pncp-tab-set/div'
                    f'/pncp-tab[2]/div/div/pncp-table/div/div/ngx-datatable/div/datatable-body'
                    f'/datatable-selection/datatable-scroller'
                    f'/datatable-row-wrapper[{c}]/datatable-body-row/div[2]/'
                )
                type_ = driver.find_element(
                    By.XPATH, f'{fp}datatable-body-cell[3]/div/span'
                )
                if type_.text == "Edital":
                    doc = driver.find_element(
                        By.XPATH, f'{fp}datatable-body-cell[4]/div/div/a'
                    )
                    docs_temp.append(doc.get_attribute("href"))
                c += 1
            except Exception:
                break

        docs.append(";".join(docs_temp))

    except Exception as e:
        print("  ❌ Não clicou no botão de arquivos:", e)
    return None


# ════════════════════════════════════════════════════════════════
# 🔬  FILTRO INTELIGENTE DE ITENS
# ════════════════════════════════════════════════════════════════
def item_relevante(desc_lower: str) -> bool:
    try:
        desc_lower = desc_lower.lower()
    except Exception:
        return False

    for excl in EXCL_ITEM:
        if excl in desc_lower:
            print(f"    🚫 Excluído por '{excl}': '{desc_lower[:60]}'")
            return False

    termos_simples = [t for t in TERMOS_ITEM if t not in TERMOS_AMBIGUOS]
    for t in termos_simples:
        if t in desc_lower:
            return True

    for termo, contextos in TERMOS_AMBIGUOS.items():
        if termo in desc_lower:
            contexto_encontrado = next(
                (ctx for ctx in contextos if ctx in desc_lower), None
            )
            if contexto_encontrado:
                print(f"    ✅ Ambíguo '{termo}' aceito — contexto: '{contexto_encontrado}'")
                return True
            else:
                print(f"    🚫 Ambíguo '{termo}' bloqueado — sem contexto agrícola")
                return False

    return False


# ════════════════════════════════════════════════════════════════
# 🚀  FUNÇÃO PRINCIPAL
# ════════════════════════════════════════════════════════════════
def licitarDigital(link, value, dia):
    count_break  = 0
    pagina_lista = 0
    B            = BASE_XPATH

    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print("❌ Erro ao iniciar o Driver:", e)
        return None

    driver.implicitly_wait(5)
    q = value.replace(" ", "%20")

    try:
        driver.get(
            f"https://pncp.gov.br/app/editais?pagina=1&q={q}&status=recebendo_proposta"
        )
    except Exception as e:
        print("Saiu sem encontrar licitação:", e)
        return driver.quit()

    while True:
        pagina_lista += 1

        if pagina_lista > MAX_PAGINAS_LISTA:
            print(f"  ⚠️  Limite de {MAX_PAGINAS_LISTA} páginas atingido. Encerrando.")
            return driver.quit()

        print(f"\n📄 Página lista [{pagina_lista}] | Termo: '{value}'")

        try:
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH,
                    '//*[@id="main-content"]/pncp-list/pncp-results-panel'
                    '/pncp-tab-set/div/pncp-show-messages/pncp-item-not-found/h2'
                ))
            )
            print("  ⚠️  Busca sem resultados.")
            return driver.quit()
        except Exception:
            pass

        count2 = 1

        while True:
            print(f"  🔁 Licitação [{count2}]")

            try:
                path = (
                    f'//*[@id="main-content"]/pncp-list/pncp-results-panel'
                    f'/pncp-tab-set/div/pncp-tab[1]/div/div[2]/div/div[2]'
                    f'/pncp-items-list/div/div[{count2}]/a'
                )
                licitação = WebDriverWait(driver, 15).until(
                    EC.presence_of_element_located((By.XPATH, path))
                )
                link2  = licitação.get_attribute('href')
                count2 += 1

                if is_equal(id_PNCP_list, link2):
                    print(f"  ↩️  Já coletada — pulando")
                    try:
                        btn_prox = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH,
                                '//pncp-pagination/nav/ul/li[last()]/button'
                            ))
                        )
                        li_pai    = btn_prox.find_element(By.XPATH, '..')
                        li_classe = li_pai.get_attribute("class") or ""
                        desabilitado = (
                            "disabled" in li_classe
                            or btn_prox.get_attribute("disabled") is not None
                        )
                        quanty = WebDriverWait(driver, 10).until(
                            EC.presence_of_element_located((By.XPATH,
                                '//*[@id="main-content"]/pncp-list/pncp-results-panel'
                                '/pncp-tab-set/div/pncp-tab[1]/div/div[1]/div/div[2]/span'
                            ))
                        ).text.split(" ")[0]
                        if desabilitado and (int(count2) >= int(quanty)):
                            return driver.quit()
                    except Exception:
                        pass
                    continue

            except Exception as e:
                print(f"  ⚠️  Fim das licitações desta página: {e}")
                try:
                    btn_prox = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,
                            '//pncp-pagination/nav/ul/li[last()]/button'
                        ))
                    )
                except Exception:
                    print("  ❌ Botão próxima página não encontrado. Encerrando.")
                    return driver.quit()

                li_pai     = btn_prox.find_element(By.XPATH, '..')
                li_classe  = li_pai.get_attribute("class") or ""
                desabilitado = (
                    "disabled" in li_classe
                    or btn_prox.get_attribute("disabled") is not None
                )

                if not desabilitado:
                    driver.execute_script("arguments[0].click();", btn_prox)
                    count_break = 0
                    count2      = 1
                    print("  ➡️  Avançando para próxima página da lista...")
                    time.sleep(3)
                    break
                else:
                    print("  🔴 Última página da lista. Encerrando.")
                    return driver.quit()

            try:
                driver.get(link2)
            except Exception as e:
                print(f"  ❌ Erro ao acessar licitação: {e}")
                continue

            carregou = False
            for tentativa in range(4):
                for xp in LOAD_XPATHS:
                    try:
                        WebDriverWait(driver, 8).until(
                            EC.visibility_of_element_located((By.XPATH, xp))
                        )
                        carregou = True
                        break
                    except Exception:
                        continue
                if carregou:
                    break
                print(f"  🔄 Tentativa {tentativa + 1}/4 — aguardando Angular...")
                time.sleep(2)

            if not carregou:
                print("  ❌ Página não carregou — voltando.")
                driver.back()
                continue

            time.sleep(1)

            title = limpar_titulo(get_el_text(driver, f'{B}/div[1]', default=""))

            local_co   = get_el_text(driver, f'{B}/div[3]/div[1]/p/span')
            orgao_co   = get_el_text(driver, f'{B}/div[3]/div[2]/p/span')
            unidade_co = get_el_text(driver, f'{B}/div[3]/div[3]/p/span')

            modalidade_co = get_el_text(driver, f'{B}/div[4]/div[1]/p/span')
            amparo_co     = get_el_text(driver, f'{B}/div[4]/div[2]/p/span')
            tipo_co       = get_el_text(driver, f'{B}/div[4]/div[3]/p/span')
            disputa_co    = get_el_text(driver, f'{B}/div[4]/div[4]/p/span')
            registro_co   = get_el_text(driver, f'{B}/div[4]/div[5]/p/span')

            data_divulgacao_co = get_el_text(driver, f'{B}/div[6]/div[1]/p/span')
            situacao_co        = get_el_text(driver, f'{B}/div[6]/div[2]/p/span')
            inicio_co          = get_el_span(driver, f'{B}/div[6]/div[3]/p', indice=1)
            fim_co             = get_el_span(driver, f'{B}/div[6]/div[4]/p', indice=1)

            id_PNCP_co = get_el_text(driver, f'{B}/div[7]/div[1]/p/span')
            fonte_co   = get_el_text(driver, f'{B}/div[7]/div[2]/p/span')

            objeto_co = limpar_objeto(
                get_el_text(driver, f'{B}/div[9]', default="")
            )

            data_str   = data_divulgacao_co if isinstance(data_divulgacao_co, str) else ""
            comparacao = comparar_data(data_str, dia)
            print(f"  📅 Data: '{data_str}' | Alvo: '{dia}' | Status: {comparacao}")

            if comparacao == 'alvo':
                pass
            elif comparacao == 'novo':
                print("  ⏩ Mais recente que o alvo — pulando sem contar break")
                driver.back()
                continue
            elif comparacao in ('antigo', 'erro'):
                count_break += 1
                print(f"  ⏭️  Mais antiga | count_break = {count_break}/5")
                driver.back()
                if count_break >= 5:
                    print("  🔴 5 licitações antigas consecutivas → encerrando")
                    return driver.quit()
                continue

            with _lock:
                if safe_str(id_PNCP_co) in id_PNCP_list:
                    print(f"  ↩️  Já salva por outra thread — pulando")
                    driver.back()
                    continue

                try:
                    title_list.append(title)
                    local_list.append(safe_str(local_co))
                    id_PNCP_list.append(safe_str(id_PNCP_co))
                    orgao_list.append(safe_str(orgao_co))
                    unidade_list.append(safe_str(unidade_co))
                    modalidade_list.append(safe_str(modalidade_co))
                    amparo_list.append(safe_str(amparo_co))
                    tipo_list.append(safe_str(tipo_co))
                    disputa_list.append(safe_str(disputa_co))
                    registro_list.append(safe_str(registro_co))
                    data_divulgacao_PNCP_list.append(safe_str(data_divulgacao_co))
                    situação_list.append(safe_str(situacao_co))
                    inicio_list.append(safe_str(inicio_co))
                    fim_list.append(safe_str(fim_co))
                    fonte_list.append(safe_str(fonte_co))
                    objeto_list.append(objeto_co)
                    count_break = 0
                    print(f"  ✅ Salva: {title[:60]}")
                except Exception as e:
                    print(f"  ❌ Erro ao salvar licitação: {e}")
                    driver.back()
                    continue

            time.sleep(0.5)
            try:
                input_element = driver.find_element(
                    By.XPATH, '//input[@type="text" and @aria-autocomplete="list"]'
                )
                driver.execute_script("arguments[0].focus();", input_element)
                time.sleep(0.5)
                input_element.click()
                input_element.send_keys(Keys.ARROW_UP)
                input_element.send_keys(Keys.ARROW_UP)
                input_element.send_keys(Keys.ENTER)
                time.sleep(0.5)
            except Exception:
                pass

            try:
                btn_aba_itens = WebDriverWait(driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH,
                        '//*[@id="main-content"]/pncp-item-detail/div'
                        '/pncp-tab-set/div/nav/ul/li[1]/button'
                    ))
                )
                driver.execute_script("arguments[0].click();", btn_aba_itens)
                print("  🖱️  Aba de itens clicada — aguardando tabela...")

                try:
                    WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.XPATH,
                            '//*[@id="main-content"]/pncp-item-detail/div'
                            '/pncp-tab-set/div/pncp-tab[1]/div/div'
                            '/pncp-table/div/div/ngx-datatable/div/datatable-body'
                            '/datatable-selection/datatable-scroller'
                            '/datatable-row-wrapper[1]'
                        ))
                    )
                    print("  ✅ Tabela de itens carregada")
                except TimeoutException:
                    print("  ℹ️  Tabela sem itens — continuando")

            except Exception:
                print("  ⚠️  Não encontrou botão da aba de itens — tentando assim mesmo")

            # ════════════════════════════════════════════════════════════════
            # 📦  COLETA DE ITENS — ✅ COM RETRY POR LINHA (StaleElement fix)
            # ════════════════════════════════════════════════════════════════
            looping               = True
            pagina_anterior_itens = None

            while looping:
                countP        = 1
                have_products = True
                linhas_pagina = []

                while have_products:
                    xpath_row = (
                        f'//*[@id="main-content"]/pncp-item-detail/div'
                        f'/pncp-tab-set/div/pncp-tab[1]/div/div'
                        f'/pncp-table/div/div/ngx-datatable/div/datatable-body'
                        f'/datatable-selection/datatable-scroller'
                        f'/datatable-row-wrapper[{countP}]/datatable-body-row/div[2]'
                    )

                    # ✅ Retry completo por linha — re-localiza tudo do zero se DOM mudar
                    leu = False
                    for tentativa in range(3):
                        try:
                            WebDriverWait(driver, 10).until(
                                EC.presence_of_element_located((By.XPATH, xpath_row))
                            )
                            desc    = get_el_text(driver, f'{xpath_row}/datatable-body-cell[2]/div/span', default="")
                            quant   = get_el_text(driver, f'{xpath_row}/datatable-body-cell[3]/div/span', default="")
                            valor   = get_el_text(driver, f'{xpath_row}/datatable-body-cell[4]/div/span', default="")
                            val_tot = get_el_text(driver, f'{xpath_row}/datatable-body-cell[5]/div/span', default="")
                            linhas_pagina.append((desc, quant, valor, val_tot))
                            leu = True
                            break
                        except StaleElementReferenceException:
                            print(f"    🔄 StaleElement linha {countP} — tentativa {tentativa + 1}/3")
                            time.sleep(0.8)
                        except (TimeoutException, NoSuchElementException):
                            have_products = False
                            break

                    if not leu and have_products:
                        print(f"    ⚠️  Linha {countP} ignorada após 3 tentativas stale")

                    if have_products:
                        countP += 1

                if linhas_pagina == pagina_anterior_itens and pagina_anterior_itens is not None:
                    if len(pagina_anterior_itens) > 0:
                        print("  ⚠️  Página de itens repetida — encerrando loop de itens.")
                    else:
                        print("  ℹ️  Sem itens nesta licitação.")
                    looping = False
                    break

                pagina_anterior_itens = linhas_pagina[:]

                with _lock:
                    salvos = 0
                    for desc, quant, valor, val_tot in linhas_pagina:
                        desc_lower = desc.lower() if isinstance(desc, str) else ""

                        if any(excl in desc_lower for excl in EXCL_ITEM):
                            print(f"    🚫 Item excluído: '{desc[:60]}'")
                            continue

                        if not any(t in desc_lower for t in TERMOS_ITEM):
                            print(f"    ⏭️  Item irrelevante: '{desc[:60]}'")
                            continue

                        item_desc_list.append(desc if desc else np.nan)
                        item_quantity_list.append(quant if quant else np.nan)
                        item_value_list.append(valor if valor else np.nan)
                        item_value_tot_list.append(val_tot if val_tot else np.nan)
                        termo_pesquisado.append(value)
                        item_licitacao_id_list.append(safe_str(id_PNCP_co))
                        salvos += 1

                    print(f"    ✅ {salvos}/{len(linhas_pagina)} itens salvos após filtro")

                total = len(item_desc_list)
                print(f"  📦 {len(linhas_pagina)} itens coletados | total acumulado: {total}")

                btn = botao_itens_habilitado(driver)
                if btn is not None:
                    if not clicar_proxima_pagina_itens(driver, btn):
                        looping = False
                else:
                    looping = False

            click_and_catch_edital(driver)
            driver.back()
            time.sleep(0.5)


# ════════════════════════════════════════════════════════════════
# 🧵  WORKERS (THREADS)
# ════════════════════════════════════════════════════════════════
def run_workers(dia):
    termos_de_pesquisa = [
        "Pulverizador costal",
        "Pulverizador elétrico",
        "Jacto",
        "Guarany",
        "Felco",
        "Matabi",
        "Nagano",
        "Tesoura de poda",
        "Podador",
        "Aplicador de grânulos",
        "Adubadeira",
        "Espalhador de fertilizante",
        "Válvula reguladora",
        "Barra 500",
        "EPI agrícola",
    ]
    task_queue = queue.Queue()
    for termo in termos_de_pesquisa:
        task_queue.put(termo)

    def worker():
        while not task_queue.empty():
            try:
                termo = task_queue.get_nowait()
            except queue.Empty:
                break
            licitarDigital(link, termo, dia)
            task_queue.task_done()
            print(f"✅ TERMINOU: '{termo}'")

    num_threads = 6
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=worker)
        t.start()
        threads.append(t)

    task_queue.join()
    for t in threads:
        t.join()


# ════════════════════════════════════════════════════════════════
# 📊  GERAÇÃO DO EXCEL
# ════════════════════════════════════════════════════════════════
def make_excel():
    Licitação = {
        "local"               : local_list,
        "orgao"               : orgao_list,
        "unidade"             : unidade_list,
        "modalidade"          : modalidade_list,
        "amparo"              : amparo_list,
        "tipo"                : tipo_list,
        "disputa"             : disputa_list,
        "registro"            : registro_list,
        "data_divulgacao_PNCP": data_divulgacao_PNCP_list,
        "situação"            : situação_list,
        "inicio"              : inicio_list,
        "fim"                 : fim_list,
        "id_PNCP"             : id_PNCP_list,
        "fonte"               : fonte_list,
        "objeto"              : objeto_list,
        "Documentos"          : docs,
        "Titulo Edital"       : title_list,
    }
    Produtos_Licitação = {
        "id_PNCP"          : item_licitacao_id_list,
        "Produto"          : item_desc_list,
        "Valor"            : item_value_list,
        "Valor Total"      : item_value_tot_list,
        "Quantidade"       : item_quantity_list,
        "Termo Pesquisado" : termo_pesquisado,
    }

    df = pd.DataFrame(Licitação)
    df.drop_duplicates(subset='id_PNCP', inplace=True)

    df_2 = pd.DataFrame(Produtos_Licitação)
    df_2.drop_duplicates(subset=['id_PNCP', 'Produto'], inplace=True)
    df_2['Produto'] = df_2['Produto'].apply(clean_string)

    today = datetime.now().strftime("%Y-%m-%d")
    df.to_excel(f'LicitaCatcherBrasil/files/licitacoes-{today}.xlsx',  index=False)
    df_2.to_excel(f'LicitaCatcherBrasil/files/produtos-{today}.xlsx',  index=False)
    print(f"\n📊 Excel salvo: licitacoes-{today}.xlsx | produtos-{today}.xlsx")
    print(f"   Licitações: {len(df)} | Itens: {len(df_2)}")


# ════════════════════════════════════════════════════════════════
# 📧  ENVIO DE E-MAIL
# ════════════════════════════════════════════════════════════════
def send_mail():
    termos_de_pesquisa = [
        "Pulverizador costal",
        "Pulverizador elétrico",
        "Jacto",
        "Guarany",
        "Felco",
        "Matabi",
        "Nagano",
        "Tesoura de poda",
        "Podador",
        "Aplicador de grânulos",
        "Adubadeira",
        "Espalhador de fertilizante",
        "Válvula reguladora",
        "Barra 500",
        "EPI agrícola",
    ]

    termos_exclusão = [
        'limpa-vidro', 'limpa vidro', 'limpador de vidro',
        'detergente', 'sabão', 'desinfetante', 'desentupidor',
        'lauril', 'sulfato de sódio', 'tensoativo',
        'com gatilho',
        'borrifador',
        'aspecto físico: líquido',
        'roçadeira', 'rocadeira',
        'motosserra',
        'bate-libera',
        'fio de nylon',
        'nylon trançado',
        'cabeçote de corte', 'cabecote de corte',
        'lâmina de corte', 'lamina de corte',
        'kit cilindro', 'cilindro e pistão', 'cilindro e pistao',
        'pistão', 'pistao',
        'virabrequim',
        'carburador',
        'kit de reparo para carburador',
        'diafragma', 'membrana', 'agulha',
        'anéis', 'anel de pistão',
        'embreagem', 'kit embreagem', 'sapata de embreagem',
        'vela de ignição', 'vela de ignicao',
        'lima redonda', 'limatão', 'afiação de corrente',
        'polia arrastadora', 'polia de partida',
        'cordão de partida', 'cordao de partida',
        'tampa de partida', 'carcaça do arranque',
        'coletor de admissão', 'coletor de admissao',
        'retentor de virabrequim',
        'mangueira de combustível', 'mangueira de combustivel',
        'filtro de combustível', 'filtro de combustivel',
        'cabo de acelerador',
        'mola de embreagem', 'mola de pressão',
        'jogo de juntas', 'kit de juntas',
        'tampa de tanque',
        'defletor para roça', 'proteção para roça',
        'motor 2 tempos', 'motor dois tempos',
        'corrente de motosserra', 'sabre de motosserra',
        'guia de corrente',
        'cirúrgic', 'cirurgic',
        'instrumental cirúr', 'bisturi',
        'veterinár',
        'tesoura de costura', 'tesoura escolar',
        'tesoura de cabeleireiro', 'tesoura para unhas',
        'tesoura inoxidável para uso geral',
        'tesoura para papel',
        '34ml', '34 ml', '500 ml', '500ml',
        '1 litro', '1litro',
        'multiuso',
        'para uso doméstico', 'uso doméstico',
        'automotivo',
        'serviço de',
        'contratação de serviço',
        'mão de obra',
    ]

    termos_norm      = [t.lower() for t in termos_de_pesquisa]
    termos_excl_norm = [t.lower() for t in termos_exclusão]

    today    = datetime.now().strftime("%Y-%m-%d")
    data     = pd.read_excel(f"LicitaCatcherBrasil/files/licitacoes-{today}.xlsx")
    produtos = pd.read_excel(f"LicitaCatcherBrasil/files/produtos-{today}.xlsx")
    produtos['encontrou_termo'] = False

    for i, r in enumerate(produtos['Produto']):
        if not isinstance(r, str) or r.strip() == '':
            continue
        r_lower  = r.lower()
        excluido = any(excl in r_lower for excl in termos_excl_norm)
        if excluido:
            continue
        achou = any(termo in r_lower for termo in termos_norm)
        produtos.at[i, 'encontrou_termo'] = achou

    merge = pd.merge(data, produtos, on='id_PNCP', how='inner')
    merge.drop_duplicates(
        subset=['id_PNCP', 'Produto', 'Valor', 'Quantidade', 'Valor Total'],
        inplace=True
    )

    mensagens = []
    for id_pncp, grupo in merge.groupby('id_PNCP'):
        coluna_title = grupo['Titulo Edital'].iloc[0]
        coluna_local = grupo['local'].iloc[0]
        coluna_orgao = grupo['orgao'].iloc[0]

        docs_     = str(grupo['Documentos'].iloc[0]).split(';')
        docs_msgs = ''
        vars_     = id_pncp.split('-')
        id_       = vars_[0]
        temp_     = vars_[-1].split('/')
        ano       = temp_[-1]
        middle    = temp_[0].lstrip('0')

        for link_edital in docs_:
            if link_edital not in ('nan', ''):
                arch              = link_edital.split('/')[-1]
                link_edital_certo = (
                    f'https://pncp.gov.br/pncp-api/v1/orgaos/{id_}'
                    f'/compras/{ano}/{middle}/arquivos/{arch}'
                )
                docs_msgs += (
                    f"<a style='display:block;width:99%;text-decoration:none;"
                    f"background-color:#0A5193;color:#FFFFFF;padding:10px;"
                    f"border-radius:8px;text-align:center;margin-top:10px;'"
                    f" href='{link_edital_certo}'>Baixar Edital</a>"
                )

        mask      = grupo['encontrou_termo'] == True
        p_desc    = grupo.loc[mask, 'Produto'].reset_index(drop=True).tolist()
        p_qtd     = grupo.loc[mask, 'Quantidade'].reset_index(drop=True).tolist()
        p_val     = grupo.loc[mask, 'Valor'].reset_index(drop=True).tolist()
        p_val_tot = grupo.loc[mask, 'Valor Total'].reset_index(drop=True).tolist()

        if len(p_desc) >= 1:
            part_msg = "".join(
                f"<tr>"
                f"<td style='padding:8px;text-align:left;'>{p_desc[i]}</td>"
                f"<td style='padding:8px;text-align:left;'>{p_qtd[i]}</td>"
                f"<td style='padding:8px;text-align:left;'>{p_val[i]}</td>"
                f"<td style='padding:8px;text-align:left;'>{p_val_tot[i]}</td>"
                f"</tr>"
                for i in range(len(p_desc))
            )
            mensagens.append(f"""
            <div style='margin-bottom:20px;border:1px solid #0A5193;
                        border-radius:8px;padding:15px;background-color:#f8f9fa;'>
                <ul style='list-style:none;padding:0;margin:0;'>
                    <li><strong style='color:#0A5193'>Id Licitação PNCP:</strong> {id_pncp}</li>
                    <li><strong style='color:#0A5193'>Edital:</strong> {coluna_title}</li>
                    <li><strong style='color:#0A5193'>Local:</strong> {coluna_local}</li>
                    <li><strong style='color:#0A5193'>Orgão:</strong> {coluna_orgao}</li>
                    <li><strong style='color:#0A5193'>Produtos:</strong></li>
                </ul>
                <table style='width:100%;margin-top:10px;border-collapse:collapse;'>
                    <thead><tr>
                        <th style='background-color:#0a5193;color:#FFF;padding:8px;text-align:left;'>Descrição</th>
                        <th style='background-color:#0a5193;color:#FFF;padding:8px;text-align:left;'>Quantidade</th>
                        <th style='background-color:#0a5193;color:#FFF;padding:8px;text-align:left;'>Valor</th>
                        <th style='background-color:#0a5193;color:#FFF;padding:8px;text-align:left;'>Valor Total</th>
                    </tr></thead>
                    <tbody>{part_msg}</tbody>
                </table>
                {docs_msgs}
            </div>""")

    email  = "<body style='font-family:Arial,sans-serif;margin:0;padding:0;background-color:#f2f2f2;'>"
    email += "<h1 style='color:#0A5193;text-align:center;'>Novas Licitações</h1>"
    for i, msg in enumerate(mensagens):
        email += msg
        if i < len(mensagens) - 1:
            email += "<hr style='border:1px solid #0A5193;'>"
    email += "</body>"

    webhook_url = os.getenv("WEBHOOK_LINK")
    payload     = (
        {"email": email.replace('\n', '')}
        if mensagens
        else {"email": "Não apareceram novas licitações"}
    )
    response = requests.post(
        webhook_url, json=payload,
        headers={"Content-Type": "application/json"}
    )

    if response.status_code in (200, 202):
        print("✅ E-mail enviado com sucesso")
    else:
        print(f"❌ Falha no envio. Status: {response.status_code}")


# ════════════════════════════════════════════════════════════════
# 🎯  EXECUTE + MAIN
# ════════════════════════════════════════════════════════════════
def execute_scripts(dia):
    run_workers(dia)
    make_excel()
    send_mail()


if __name__ == "__main__":
    COLETAR_DIA = "ontem"

    if COLETAR_DIA == "ontem":
        data_alvo = datetime.now() - timedelta(days=1)
    else:
        data_alvo = datetime.now()

    dia = data_alvo.strftime("%d/%m/%Y")
    print(f"\n{'='*55}")
    print(f"  🤖 LicitaCatcher Brasil")
    print(f"  📅 Coletando licitações de: {dia}")
    print(f"{'='*55}\n")
    execute_scripts(dia)