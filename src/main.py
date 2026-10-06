import os
import argparse
import logging
from datetime import datetime
import time

from src.config import DATA_START_DEFAULT, DATA_DIR, REPORTS_DIR, DOCS_DATA_DIR, GCP_PROJECT_ID, BQ_LOCATION, BQ_DATASET_ANALYTICS
from src.extract import extract_all
from src.transform import clean_raw_data, transform_analytics
from src.load import save_local, load_to_bigquery, create_bigquery_views
from src.report import generate_excel_report, generate_dashboard_json

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def run_pipeline(target: str, start_date: str):
    start_time = time.time()
    logger.info(f"Iniciando pipeline de dados (Alvo: {target}) a partir de {start_date}")
    
    end_date = datetime.now().strftime("%Y-%m-%d")
    
    # 1. Extração
    logger.info("--- 1. EXTRAÇÃO ---")
    df_raw = extract_all(start_date, end_date)
    if df_raw.empty:
        logger.error("Nenhum dado extraído. Abortando pipeline.")
        exit(1)
        
    # 2. Transformação
    logger.info("--- 2. TRANSFORMAÇÃO ---")
    df_clean = clean_raw_data(df_raw)
    df_analytics = transform_analytics(df_clean)
    
    # 3. Carga e Relatórios (Local)
    logger.info("--- 3. CARGA LOCAL E RELATÓRIOS ---")
    
    save_local(df_raw, "indicadores_raw", os.path.join(DATA_DIR, "raw"))
    save_local(df_clean, "indicadores_clean", os.path.join(DATA_DIR, "clean"))
    save_local(df_analytics, "indicadores_analytics", os.path.join(DATA_DIR, "analytics"))
    
    report_path = os.path.join(REPORTS_DIR, "indicadores_economicos.xlsx")
    generate_excel_report(df_analytics, report_path)
    
    json_path = os.path.join(DOCS_DATA_DIR, "indicadores.json")
    generate_dashboard_json(df_analytics, json_path)
    
    # 4. BigQuery (Opcional)
    if target in ["bigquery", "all"]:
        logger.info("--- 4. CARGA NO BIGQUERY ---")
        if not GCP_PROJECT_ID:
            logger.warning("GCP_PROJECT_ID não definido. Pulando etapa do BigQuery.")
        else:
            load_to_bigquery(df_analytics, GCP_PROJECT_ID, BQ_DATASET_ANALYTICS, "tb_indicadores_mensais", BQ_LOCATION)
            create_bigquery_views(GCP_PROJECT_ID, BQ_DATASET_ANALYTICS, BQ_LOCATION)
            
    elapsed = time.time() - start_time
    logger.info(f"Pipeline concluído com sucesso em {elapsed:.2f} segundos.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Pipeline ETL de Indicadores Econômicos Brasileiros.")
    parser.add_argument("--target", choices=["local", "bigquery", "all"], default="local",
                        help="Destino dos dados: 'local' (apenas Parquet/Excel/JSON), 'bigquery', ou 'all' (ambos).")
    parser.add_argument("--start", type=str, default=DATA_START_DEFAULT,
                        help="Data de início (YYYY-MM-DD). Padrão: 2015-01-01.")
    
    args = parser.parse_args()
    run_pipeline(args.target, args.start)
