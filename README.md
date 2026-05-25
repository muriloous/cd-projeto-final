# Impacto do Clima na Produção Agrícola e Inflação no Brasil (2020–2024)

**Projeto Final — Estrutura de Dados-A1053-N-CIENCIA DE DADOS**

## Tema e Justificativa

O Brasil é um dos maiores produtores mundiais de soja, milho e café — culturas altamente sensíveis a variações climáticas. Secas prolongadas e excesso de chuva impactam diretamente a produtividade no campo e, com uma defasagem de meses, chegam ao bolso do consumidor via inflação de alimentos.

Este projeto investiga empiricamente essa cadeia causal usando dados públicos do **INMET** (Instituto Nacional de Meteorologia) e do **IBGE/SIDRA**, aplicando técnicas de séries temporais, correlação de Pearson e análise de defasagem (lag).

## Fontes de Dados

| Fonte | Dados | Tabela/Endpoint |
|---|---|---|
| [INMET](https://portal.inmet.gov.br/dadoshistoricos) | Precipitação e temperatura horárias por estação automática | Bulk CSV anual (1 ZIP/ano) |
| [IBGE SIDRA — Tabela 5457](https://sidra.ibge.gov.br/tabela/5457) | Produção Agrícola Municipal (PAM): quantidade, área, rendimento | Soja, Milho, Café — nível UF |
| [IBGE SIDRA — Tabela 7060](https://sidra.ibge.gov.br/tabela/7060) | IPCA Alimentação e Bebidas (variação mensal) por Região Metropolitana | Grupo 7170 (c315), variável 63 |
| [click_that_hood](https://github.com/codeforgermany/click_that_hood) | GeoJSON simplificado das UFs do Brasil (~50 KB) | brazil-states.geojson |

**Período coberto:** 2020–2024 | **Granularidade:** por UF (estado)

## Perguntas-Chave

1. Quais estados concentram a produção de soja, milho e café?
2. Anomalias de precipitação na janela da safra se correlacionam com queda de produtividade?
3. Com quantos meses de defasagem (lag) uma anomalia climática aparece no IPCA Alimentação?
4. A correlação de Pearson entre chuva na safra e produção é estatisticamente significativa por UF?
5. Como evoluiu o IPCA de Alimentação em anos de eventos climáticos extremos (2021 seca, 2023 La Niña)?

## Como rodar o projeto

### Pré-requisitos

- Python 3.11+
- Acesso à internet (para download de dados públicos)

### 1. Instalar dependências

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 2. Baixar dados do INMET

> Este passo baixa ~2 GB de dados históricos (11 ZIPs). Deixe rodando em background.

```bash
python scripts/fetch_inmet.py
```

### 3. Gerar os datasets processados

```bash
python scripts/build_dataset.py
```

Após a execução, os arquivos em `data/processed/` estarão prontos:
- `consolidated_mensal.csv` — clima + IPCA por UF×mês
- `consolidated_anual.csv` — clima da safra + PAM + IPCA por UF×ano×cultura
- `metadata.json` — informações sobre o build

### 4. Iniciar o dashboard

```bash
streamlit run app.py
```

Acesse `http://localhost:8501` no navegador.

### Atalhos úteis

```bash
# Rodar ETL sem re-baixar INMET (usa dados já no disco)
python scripts/build_dataset.py --skip-inmet

# Baixar apenas anos específicos do INMET
python scripts/fetch_inmet.py --anos 2022 2023 2024
```

## Estrutura do Projeto

```
├── app.py                    # Dashboard Streamlit (5 abas)
├── requirements.txt
├── scripts/
│   ├── fetch_inmet.py        # Download bulk INMET
│   └── build_dataset.py      # Orquestrador ETL
├── src/
│   ├── config.py             # Constantes: UFs, culturas, paths, janelas de safra
│   ├── data_fetch/           # Coleta: INMET, SIDRA PAM, SIDRA IPCA, GeoJSON
│   ├── processing/           # Limpeza, merge, análise (Pearson, lag)
│   └── viz/                  # Gráficos Plotly e mapas coropléticos
├── data/
│   ├── raw/                  # Dados brutos (não versionados)
│   └── processed/            # CSVs prontos para o dashboard
└── docs/screenshots/         # Capturas de tela do dashboard
```

## Decisões Técnicas Relevantes

**Janela de safra:** em vez de usar o ano civil, o clima é agregado pela janela temporal real de cada cultura (ex.: soja = outubro a abril). Isso torna as correlações mais defensáveis agronomicamente.

**IPCA por RM:** o IPCA não tem granularidade por estado — apenas por Região Metropolitana. UFs sem RM usam o índice nacional como referência (documentado nos metadados).

**Anomalias climáticas:** calculadas como desvio em relação à climatologia 2020–2024 de cada UF×mês, não ao ano civil.

## Screenshots

*(capturas serão adicionadas ao `docs/screenshots/` após a execução do dashboard)*

## Limitações Conhecidas

- O IPCA não cobre todos os estados (apenas RMs disponíveis no SIDRA). UFs sem RM usam o índice nacional.
- Dados do INMET de 2025 podem não estar disponíveis no bulk; análise cobre até 2024.
- PAM definitivo de 2024 pode estar com publicação pendente (IBGE publica com ~10 meses de atraso).

## Critérios Atendidos

| Critério | Como atendido |
|---|---|
| API pública | SIDRA/IBGE via `sidrapy`; INMET bulk download público |
| Armazenamento local | `data/raw/` (bruto) → `data/processed/` (processado) antes do dashboard |
| Limpeza/processamento | Remoção de -9999, agregação horário→mensal, anomalias, merge por janela de safra |
| ≥ 2 elementos interativos | Slider de período, multiselect de UFs, selectbox de cultura, slider de lag |
| KPIs e layout organizado | 4 métricas de destaque + títulos + explicações em cada aba |
| Correlação de Pearson | Matriz de correlação na Aba 5 |
| Lag temporal | Cross-correlation interativa na Aba 5 |
| Mapas de calor | Heatmap de anomalias (Aba 2) + choropleth (Abas 3 e 5) |
