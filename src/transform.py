import pandas as pd
import numpy as np
import logging

logger = logging.getLogger(__name__)

def clean_raw_data(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Limpa e tipa os dados brutos da API.
    Remove duplicatas e garante que os valores numéricos estejam corretos.
    """
    if df_raw.empty:
        return df_raw
        
    df = df_raw.copy()
    
    # Conversão de data (a API retorna dd/mm/yyyy)
    df["data"] = pd.to_datetime(df["data_raw"], format="%d/%m/%Y")
    
    # Conversão de valor (a API retorna string, muitas vezes vazia ou com formato incorreto)
    # Alguns valores podem vir vazios ou incorretos, forçamos numérico (NaN se falhar)
    df["valor"] = pd.to_numeric(df["valor_raw"], errors="coerce")
    
    # Remove registros sem valor válido
    df = df.dropna(subset=["valor"])
    
    # Remove duplicatas (pode acontecer na sobreposição de chunks ou erro na origem)
    df = df.drop_duplicates(subset=["codigo_serie", "data"]).sort_values("data")
    
    # Seleciona apenas as colunas limpas
    df_clean = df[["codigo_serie", "nome_serie", "data", "valor"]].reset_index(drop=True)
    return df_clean

def transform_analytics(df_clean: pd.DataFrame) -> pd.DataFrame:
    """
    Agrega as séries em uma tabela unificada por mês.
    - Selic (diária): pega o valor do último dia útil do mês.
    - Dólar (diária): média do mês e último dia do mês.
    - IPCA/IGPM (mensais): valor do próprio mês e variação acumulada em 12 meses.
    - Juros reais: calculados ex-post.
    """
    if df_clean.empty:
        return pd.DataFrame()
        
    # Extrai ano e mês para agregação
    df_clean["ano_mes"] = df_clean["data"].dt.to_period("M")
    
    # 1. Indicadores mensais puros (IPCA e IGP-M)
    df_mensal = df_clean[df_clean["nome_serie"].isin(["ipca_mensal", "igpm_mensal"])]
    pivot_mensal = df_mensal.pivot(index="ano_mes", columns="nome_serie", values="valor").reset_index()
    
    # 2. Selic Meta (pegando o último dia do mês)
    df_selic = df_clean[df_clean["nome_serie"] == "selic_meta"].sort_values("data")
    selic_fim = df_selic.groupby("ano_mes").tail(1)[["ano_mes", "valor"]].rename(columns={"valor": "selic_meta_fim"})
    
    # 3. Dólar (média mensal e último dia do mês)
    df_dolar = df_clean[df_clean["nome_serie"] == "dolar_ptax_venda"].sort_values("data")
    dolar_medio = df_dolar.groupby("ano_mes")["valor"].mean().reset_index().rename(columns={"valor": "dolar_medio"})
    dolar_fim = df_dolar.groupby("ano_mes").tail(1)[["ano_mes", "valor"]].rename(columns={"valor": "dolar_fim"})
    
    # Junta tudo pela coluna ano_mes
    df_analytics = selic_fim.merge(dolar_medio, on="ano_mes", how="outer")\
                            .merge(dolar_fim, on="ano_mes", how="outer")\
                            .merge(pivot_mensal, on="ano_mes", how="outer")
    
    # Ordena o tempo
    df_analytics = df_analytics.sort_values("ano_mes").reset_index(drop=True)
    
    # Adiciona a coluna 'mes' como data (primeiro dia do mês) para facilitar gráficos e particionamento
    df_analytics["mes"] = df_analytics["ano_mes"].dt.to_timestamp()
    
    # Preenche NaN por precaução (compras de dolar podem ter feriados, mas na agregação mensal isso é raro)
    df_analytics = df_analytics.ffill()
    
    # Calcula inflação acumulada 12 meses ( (1 + i/100) * ... - 1 ) * 100
    # Usando janela rolante (rolling)
    def acumular_12m(x):
        if len(x) < 12:
            return np.nan
        return (np.prod(1 + x / 100.0) - 1) * 100.0

    df_analytics["ipca_12m"] = df_analytics["ipca_mensal"].rolling(window=12, min_periods=12).apply(acumular_12m)
    df_analytics["igpm_12m"] = df_analytics["igpm_mensal"].rolling(window=12, min_periods=12).apply(acumular_12m)
    
    # Calcula os juros reais ex-post (fórmula de Fisher simplificada para o período acumulado)
    # Considerando Selic como anual e subtraindo a inflação 12m
    # Juros Real = ( (1 + Selic_Meta/100) / (1 + IPCA_12M/100) - 1 ) * 100
    df_analytics["juros_real_ex_post"] = ((1 + df_analytics["selic_meta_fim"] / 100.0) / 
                                          (1 + df_analytics["ipca_12m"] / 100.0) - 1) * 100.0
                                          
    # Arredondamentos e limpeza final
    colunas_finais = [
        "mes", "selic_meta_fim", "dolar_medio", "dolar_fim", 
        "ipca_mensal", "ipca_12m", "igpm_mensal", "igpm_12m", "juros_real_ex_post"
    ]
    df_final = df_analytics[colunas_finais].copy()
    
    for col in df_final.columns:
        if col != "mes":
            df_final[col] = df_final[col].round(4)
            
    # Filtra linhas onde não temos inflação (normalmente o mês atual ainda não tem IPCA fechado)
    # Decisão de negócio: manter tudo, pois Selic e Dólar fecham antes do IPCA
    
    logger.info(f"Transformação Analytics concluída. Registros mensais: {len(df_final)}")
    return df_final
