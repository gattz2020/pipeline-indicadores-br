import pandas as pd
import numpy as np
import pytest
from datetime import datetime
from src.transform import clean_raw_data, transform_analytics
from src.extract import generate_date_chunks

def test_generate_date_chunks():
    chunks = generate_date_chunks("2020-01-01", "2025-12-31", chunk_years=2)
    assert len(chunks) == 3
    assert chunks[0][0] == "01/01/2020"
    assert chunks[0][1] == "31/12/2021"
    
def test_clean_raw_data():
    raw_data = pd.DataFrame({
        "codigo_serie": [1, 1, 432],
        "nome_serie": ["dolar_ptax_venda", "dolar_ptax_venda", "selic_meta"],
        "data_raw": ["01/01/2023", "01/01/2023", "02/01/2023"], # data duplicada no dolar
        "valor_raw": ["5.34", "", "13.75"], # string vazia e decimal
        "ingested_at": [datetime.now(), datetime.now(), datetime.now()]
    })
    
    clean_df = clean_raw_data(raw_data)
    
    # Verifica deduplicação
    assert len(clean_df) == 2
    
    # Verifica tipagem
    assert pd.api.types.is_datetime64_any_dtype(clean_df["data"])
    assert pd.api.types.is_numeric_dtype(clean_df["valor"])
    
    # Verifica valores
    assert clean_df[clean_df["codigo_serie"] == 1]["valor"].iloc[0] == 5.34
    assert clean_df[clean_df["codigo_serie"] == 432]["valor"].iloc[0] == 13.75

def test_transform_analytics():
    # Cria dados simulados para um mês (Janeiro/2023) e um pedaço de Fevereiro
    data = pd.DataFrame({
        "codigo_serie": [432, 432, 1, 1, 433, 189],
        "nome_serie": ["selic_meta", "selic_meta", "dolar_ptax_venda", "dolar_ptax_venda", "ipca_mensal", "igpm_mensal"],
        "data": pd.to_datetime(["2023-01-01", "2023-01-31", "2023-01-15", "2023-01-31", "2023-01-01", "2023-01-01"]),
        "valor": [13.75, 13.75, 5.0, 5.2, 0.53, 0.21]
    })
    
    df_analytics = transform_analytics(data)
    
    assert len(df_analytics) == 1
    assert df_analytics["mes"].iloc[0] == pd.Timestamp("2023-01-01")
    assert df_analytics["selic_meta_fim"].iloc[0] == 13.75
    assert df_analytics["dolar_medio"].iloc[0] == 5.1  # Média de 5.0 e 5.2
    assert df_analytics["dolar_fim"].iloc[0] == 5.2
    assert df_analytics["ipca_mensal"].iloc[0] == 0.53
    assert df_analytics["igpm_mensal"].iloc[0] == 0.21
    
    # No primeiro mês, a métrica 12m não fecha (são necessários 12 meses)
    assert pd.isna(df_analytics["ipca_12m"].iloc[0])
