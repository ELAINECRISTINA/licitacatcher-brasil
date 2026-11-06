# 🤖 LicitaCatcher Brasil

**Bot que monitora licitações públicas no PNCP (Portal Nacional de Contratações Públicas) e envia, todos os dias, um resumo por e-mail com as oportunidades relevantes para o seu negócio.**

Encontrar licitações dos seus produtos no PNCP exige abrir edital por edital, ler os itens e descartar o que não interessa. O LicitaCatcher faz isso automaticamente: varre os editais que estão recebendo propostas, filtra os itens pelos produtos de interesse e entrega uma tabela pronta para análise.

---

## ✨ O que ele faz

- 🔎 **Varre o PNCP** nos editais com status *recebendo proposta*, filtrando pela data de divulgação (por padrão, o dia anterior)
- 🎯 **Filtra itens com inteligência**:
  - lista de **termos de interesse** (produtos, marcas, categorias)
  - lista de **termos de exclusão**, para eliminar falsos positivos (ex.: "tesoura escolar" quando o foco é "tesoura de poda")
  - **termos ambíguos validados por contexto**: um item como "válvula reguladora" só entra se a descrição tiver contexto agrícola
- ⚡ **Coleta em paralelo** com múltiplas threads e fila de trabalho
- 📋 **Extrai os dados do edital**: órgão, unidade, local, modalidade, amparo legal, tipo, modo de disputa, datas de início e fim, ID PNCP, objeto, além dos itens com quantidade, valor unitário e valor total
- 📊 **Gera uma planilha Excel** com tudo consolidado
- 📧 **Envia um e-mail em HTML** com cada licitação encontrada, seus itens e documentos, via webhook

## 🛠️ Stack

`Python` · `Selenium` (Chrome headless) · `Pandas` · `NumPy` · `Requests` · `threading/queue` · `python-dotenv`

## 🚀 Como rodar

```bash
git clone https://github.com/ELAINECRISTINA/BOT-_licitacao.git
cd BOT-_licitacao
pip install selenium pandas numpy requests python-dotenv openpyxl
```

Crie um arquivo `.env` na raiz com o endereço do webhook que dispara o e-mail:

```env
WEBHOOK_LINK=https://seu-webhook-aqui
```

Execute:

```bash
python scraper.py
```

> É necessário ter o Google Chrome instalado. O Selenium 4 baixa o driver automaticamente.

## ⚙️ Personalização

No início do `scraper.py`:

| Constante | Para que serve |
|---|---|
| `TERMOS_ITEM` | Produtos e marcas que você quer encontrar |
| `EXCL_ITEM` | Palavras que descartam um item (falsos positivos) |
| `TERMOS_AMBIGUOS` | Termos que só valem se houver contexto do seu setor |
| `MAX_PAGINAS_LISTA` | Quantas páginas de editais varrer |
| `COLETAR_DIA` | `"ontem"` ou o dia atual |

Trocando as listas de termos, o bot serve para **qualquer setor**: material hospitalar, informática, construção civil, alimentos etc.

## 💡 Casos de uso

- Empresas que vendem para o governo e querem **não perder prazos**
- Times comerciais e de **Inteligência de Mercado** acompanhando a demanda pública por categoria
- Análise de **preços praticados** em compras públicas

## 🗺️ Próximos passos

- [ ] Migrar a coleta para a API oficial do PNCP
- [ ] Agendamento automático (GitHub Actions ou cron)
- [ ] Painel em Streamlit com o histórico de licitações

---

Feito por **Elaine Cristina** · [LinkedIn](https://www.linkedin.com/in/elaine-cristina-silva-1650bb170/)
