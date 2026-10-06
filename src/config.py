import os
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env, se existir
load_dotenv()

# ==========================================
# Configurações do Banco Central (SGS)
# ==========================================
BCB_API_URL = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json&dataInicial={data_inicial}&dataFinal={data_final}"
DATA_START_DEFAULT = "2015-01-01"

# Séries que iremos extrair (Código SGS, Nome, Frequência)
SERIES_CONFIG = {
    432: {"nome": "selic_meta", "frequencia": "diaria"},
    433: {"nome": "ipca_mensal", "frequencia": "mensal"},
    1: {"nome": "dolar_ptax_venda", "frequencia": "diaria"},
    189: {"nome": "igpm_mensal", "frequencia": "mensal"}
}

# ==========================================
# Configurações do Google BigQuery
# ==========================================
# Se a variável GCP_PROJECT_ID não estiver definida, o carregamento no BigQuery não será executado
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BQ_LOCATION = os.getenv("BQ_LOCATION", "US")
BQ_DATASET_RAW = os.getenv("BQ_DATASET_RAW", "indicadores_raw")
BQ_DATASET_ANALYTICS = os.getenv("BQ_DATASET_ANALYTICS", "indicadores_analytics")

# ==========================================
# Caminhos locais
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")
DOCS_DATA_DIR = os.path.join(BASE_DIR, "docs", "data")
SQL_DIR = os.path.join(BASE_DIR, "sql")
