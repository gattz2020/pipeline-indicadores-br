import os
import json
import logging
import pandas as pd
from datetime import datetime
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.chart import LineChart, Reference

logger = logging.getLogger(__name__)

def generate_excel_report(df: pd.DataFrame, output_path: str):
    """
    Gera um relatório Excel profissional com formatação e gráficos,
    muito comum em demandas do Workana.
    """
    if df.empty:
        logger.warning("DataFrame vazio, relatório Excel não será gerado.")
        return
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    wb = Workbook()
    
    # Planilha principal de dados
    ws_data = wb.active
    ws_data.title = "Dados Mensais"
    
    # Aplica o cabeçalho e os dados
    for r in dataframe_to_rows(df, index=False, header=True):
        ws_data.append(r)
        
    # Estilização
    header_fill = PatternFill(start_color="112233", end_color="112233", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    # Formatando colunas e cabeçalho
    for col_idx, column in enumerate(ws_data.columns, 1):
        # Cabeçalho
        cell = column[0]
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        
        # Ajusta largura (básico)
        col_letter = cell.column_letter
        ws_data.column_dimensions[col_letter].width = 16
        
        # Formata números (tirando o cabeçalho)
        for row_cell in column[1:]:
            if col_idx == 1:
                row_cell.number_format = 'mm/yyyy'
                row_cell.alignment = Alignment(horizontal="center")
            else:
                row_cell.number_format = '#,##0.00'
                
    # Filtro e travamento de painéis
    ws_data.auto_filter.ref = ws_data.dimensions
    ws_data.freeze_panes = "B2"
    
    # Criando gráfico de Inflação (IPCA) x Juros (Selic)
    chart = LineChart()
    chart.title = "Selic vs IPCA (12 meses)"
    chart.style = 13
    chart.y_axis.title = "Porcentagem (%)"
    chart.x_axis.title = "Período"
    chart.width = 20
    chart.height = 10
    
    # Dados (ignorando o cabeçalho) - Colunas: 2 (Selic) e 6 (IPCA 12m)
    data_selic = Reference(ws_data, min_col=2, min_row=1, max_row=ws_data.max_row)
    data_ipca = Reference(ws_data, min_col=6, min_row=1, max_row=ws_data.max_row)
    cats = Reference(ws_data, min_col=1, min_row=2, max_row=ws_data.max_row)
    
    chart.add_data(data_selic, titles_from_data=True)
    chart.add_data(data_ipca, titles_from_data=True)
    chart.set_categories(cats)
    
    ws_data.add_chart(chart, "K2")
    
    wb.save(output_path)
    logger.info(f"Relatório Excel gerado em: {output_path}")

def generate_dashboard_json(df: pd.DataFrame, output_path: str):
    """
    Gera o arquivo JSON que alimentará o dashboard estático no GitHub Pages.
    """
    if df.empty:
        return
        
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Transforma datetime para string e limpa NaN
    df_json = df.copy()
    df_json['mes'] = df_json['mes'].dt.strftime('%Y-%m')
    df_json = df_json.fillna(0)
    
    # Pega os KPIs mais recentes (última linha com valores preenchidos)
    latest = df_json.iloc[-1].to_dict()
    
    # Prepara o payload
    payload = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "latest_kpis": latest,
        "history": df_json.to_dict(orient="records")
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        
    logger.info(f"Dados do dashboard gerados em: {output_path}")
