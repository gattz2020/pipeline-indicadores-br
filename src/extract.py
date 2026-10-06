import logging
from datetime import datetime, timedelta
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from src.config import BCB_API_URL, SERIES_CONFIG

logger = logging.getLogger(__name__)

def create_session() -> requests.Session:
    """Cria uma sessão HTTP com retry automático para resiliência."""
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
    
    retry_strategy = Retry(
        total=4,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session

def generate_date_chunks(start_date: str, end_date: str, chunk_years: int = 5) -> list[tuple[str, str]]:
    """
    Divide um intervalo de datas em blocos menores.
    A API do Banco Central passou a restringir consultas a janelas máximas de 10 anos.
    """
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    chunks = []
    
    current_start = start
    while current_start <= end:
        current_end = current_start + timedelta(days=chunk_years * 365)
        if current_end > end:
            current_end = end
        
        chunks.append((
            current_start.strftime("%d/%m/%Y"),
            current_end.strftime("%d/%m/%Y")
        ))
        current_start = current_end + timedelta(days=1)
        
    return chunks

def fetch_series_data(session: requests.Session, codigo: int, data_inicial: str, data_final: str) -> pd.DataFrame:
    """Extrai os dados de uma série temporal da API SGS para um intervalo específico."""
    url = BCB_API_URL.format(codigo=codigo, data_inicial=data_inicial, data_final=data_final)
    response = session.get(url, timeout=15)
    response.raise_for_status()
    
    data = response.json()
    if not data:
        return pd.DataFrame(columns=["codigo_serie", "nome_serie", "data_raw", "valor_raw", "ingested_at"])
        
    df = pd.DataFrame(data)
    df.rename(columns={"data": "data_raw", "valor": "valor_raw"}, inplace=True)
    df["codigo_serie"] = codigo
    df["nome_serie"] = SERIES_CONFIG[codigo]["nome"]
    df["ingested_at"] = datetime.utcnow()
    
    return df

def extract_all(start_date: str, end_date: str) -> pd.DataFrame:
    """Extrai todas as séries configuradas, dividindo a requisição em blocos de datas."""
    session = create_session()
    chunks = generate_date_chunks(start_date, end_date, chunk_years=5)
    
    all_dfs = []
    
    for codigo, info in SERIES_CONFIG.items():
        logger.info(f"Extraindo série {codigo} ({info['nome']})...")
        series_dfs = []
        for chunk_start, chunk_end in chunks:
            logger.debug(f"  Buscando período {chunk_start} a {chunk_end}")
            try:
                df_chunk = fetch_series_data(session, codigo, chunk_start, chunk_end)
                if not df_chunk.empty:
                    series_dfs.append(df_chunk)
            except Exception as e:
                logger.error(f"Erro ao extrair {codigo} no período {chunk_start}-{chunk_end}: {e}")
                
        if series_dfs:
            df_series = pd.concat(series_dfs, ignore_index=True)
            all_dfs.append(df_series)
            
    if all_dfs:
        df_final = pd.concat(all_dfs, ignore_index=True)
        logger.info(f"Extração concluída. Total de registros: {len(df_final)}")
        return df_final
    else:
        logger.warning("Nenhum dado foi extraído.")
        return pd.DataFrame(columns=["codigo_serie", "nome_serie", "data_raw", "valor_raw", "ingested_at"])
