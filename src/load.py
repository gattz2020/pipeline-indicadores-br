import os
import logging
import pandas as pd
from datetime import datetime

logger = logging.getLogger(__name__)

def save_local(df: pd.DataFrame, table_name: str, folder_path: str):
    """
    Salva o DataFrame localmente em Parquet e CSV na pasta informada.
    """
    os.makedirs(folder_path, exist_ok=True)
    
    parquet_path = os.path.join(folder_path, f"{table_name}.parquet")
    csv_path = os.path.join(folder_path, f"{table_name}.csv")
    
    df.to_parquet(parquet_path, index=False)
    df.to_csv(csv_path, index=False, sep=";", decimal=",")
    
    logger.info(f"Salvo localmente: {parquet_path}")

def load_to_bigquery(df: pd.DataFrame, project_id: str, dataset_id: str, table_name: str, location: str = "US"):
    """
    Carrega o DataFrame para o BigQuery.
    Usa modo WRITE_TRUNCATE para compatibilidade com o modo Sandbox gratuito (que não permite DML).
    """
    try:
        from google.cloud import bigquery
        from google.cloud.exceptions import NotFound
    except ImportError:
        logger.error("Bibliotecas do BigQuery não encontradas. Instale google-cloud-bigquery.")
        return

    client = bigquery.Client(project=project_id, location=location)
    
    # Garante que o dataset existe
    dataset_ref = client.dataset(dataset_id)
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        logger.info(f"Criando dataset {dataset_id}...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = location
        client.create_dataset(dataset)
        
    table_id = f"{project_id}.{dataset_id}.{table_name}"
    
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
    )
    
    logger.info(f"Carregando dados na tabela {table_id} (BigQuery)...")
    job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
    job.result()  # Aguarda a conclusão
    
    table = client.get_table(table_id)
    logger.info(f"Carga concluída. {table.num_rows} linhas carregadas em {table_id}.")

def create_bigquery_views(project_id: str, dataset_id: str, location: str = "US"):
    """
    Cria ou atualiza views SQL no BigQuery para os dashboards (ex: Looker Studio).
    No modo Sandbox as views não expiram como as tabelas (tabelas expiram em 60 dias se não recriadas).
    """
    try:
        from google.cloud import bigquery
    except ImportError:
        return

    client = bigquery.Client(project=project_id, location=location)
    
    view_resumo = f"""
    CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.vw_resumo_anual` AS
    SELECT 
        EXTRACT(YEAR FROM mes) AS ano,
        AVG(selic_meta_fim) AS media_selic,
        AVG(dolar_medio) AS media_dolar,
        SUM(ipca_mensal) AS ipca_acumulado
    FROM `{project_id}.{dataset_id}.tb_indicadores_mensais`
    GROUP BY ano
    ORDER BY ano DESC
    """
    
    view_12m = f"""
    CREATE OR REPLACE VIEW `{project_id}.{dataset_id}.vw_ultimos_12_meses` AS
    SELECT *
    FROM `{project_id}.{dataset_id}.tb_indicadores_mensais`
    ORDER BY mes DESC
    LIMIT 12
    """
    
    for query in [view_resumo, view_12m]:
        try:
            job = client.query(query)
            job.result()
            logger.info("View SQL criada/atualizada com sucesso no BigQuery.")
        except Exception as e:
            logger.error(f"Erro ao criar view no BigQuery: {e}")

