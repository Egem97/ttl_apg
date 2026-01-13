import asyncio
import dash
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, dcc, callback, Input, Output, State
from components.grid import Row, Column
from constants import PAGE_TITLE_PREFIX
from helpers.helpers import generate_list_month
from dash_ag_grid import AgGrid
from helpers.get_sheets import read_sheet
import time
from datetime import datetime, timedelta
from helpers.pdf_generator import generate_boleta_pdf
import base64
from helpers.files import *


# 🚀 Configuraciones de rendimiento optimizadas
pd.options.mode.chained_assignment = None  # Evitar warnings de SettingWithCopyWarning
pd.options.compute.use_numba = True  # Usar Numba para operaciones numéricas si está disponible
pd.options.mode.sim_interactive = True  # Optimizar para operaciones interactivas


dash.register_page(__name__, "/apg/transform-materia-prima", title=PAGE_TITLE_PREFIX + "Transformación Materia Prima")
app = dash.get_app()
PAGE_ID = "transform-materia-prima-"
DATA_SOURCE = "transform_materia_prima"



def create_custom_layout():
    return dmc.Container(children=[

        html.Div([
            dcc.Store(id=f"{PAGE_ID}dates-store"),      # Para datos de fechas generados
            dcc.Store(id=f"{PAGE_ID}raw-data-store"),   # Para datos crudos (carga única)
            dcc.Store(id=f"{PAGE_ID}filtered-data-store"), # Para datos filtrados
            dcc.Store(id=f"{PAGE_ID}cache-store"),      # Para cache de archivos cargados
            dcc.Store(id=f"{PAGE_ID}loading-trigger", data="init"),   # Para trigger de carga inicial
            dcc.Store(id=f"{PAGE_ID}modal-data-store"), # Para datos del modal
        ]),
        dmc.Container([
            Row([
                Column([
                    DashIconify(icon="flat-ui:resume", width=30),
                    dmc.Title("Transformación Materia Prima", order=1, mb="xs")
                ], size=6),
                Column([
                    
                        dmc.DateInput(
                            id=f"{PAGE_ID}date-filter",
                            label="Fecha",
                            placeholder="Seleccionar fecha",
                            clearable=True,
                            style={"width": "100%"},
                            value=datetime.now().date() - timedelta(days=1),
                        ),
                       
                    
                ], size=3),
                Column([
                    dmc.Select(
                        id=f"{PAGE_ID}subsidiaria-filter",
                        label="Subsidiaria",
                        placeholder="Seleccionar subsidiaria",
                        searchable=True,
                        clearable=True,
                        style={"width": "100%"}
                    )
                ], size=3),
            ]),
            
            Row([
                Column([
                    html.Div(children=[
                        dmc.Loader(color="blue", size="md", type="oval",id=f"{PAGE_ID}loading-indicator"),
                        html.Div(id=f"{PAGE_ID}main-table"),
                    ]),
                    
                    dmc.Group([
                        dmc.Button(
                            "DESCARGAR CSV", 
                            id=f"{PAGE_ID}btn-csv", 
                            color="blue", 
                            variant="filled", 
                            leftSection=DashIconify(icon="fluent:document_print"),
                        ),
                    ]),
                    dcc.Download(id=f"{PAGE_ID}download-csv"),
                    
                    # Modal de Previsualización
                    dmc.Modal(
                        id=f"{PAGE_ID}preview-modal",
                        title="Previsualización de Boletas",
                        size="xl",
                        padding="md",
                        children=[
                            html.Iframe(
                                id=f"{PAGE_ID}pdf-preview-frame",
                                style={"width": "100%", "height": "600px", "border": "none"}
                            ),
                            dmc.Group([
                                dmc.Button(
                                    "Descargar PDF",
                                    id=f"{PAGE_ID}btn-confirm-download",
                                    color="blue",
                                )
                            ], grow=True)
                        ]
                    )
                    
                ], size=12)
            ])
        ],fluid=True)
    ],fluid=True)  


layout = create_custom_layout()

@callback(
    Output(f"{PAGE_ID}dates-store", "data"),
    Input(f"{PAGE_ID}loading-trigger", "data")
)
def load_data_to_store(_):
    df = load_data_cosecha_campo()
    return df.to_dict('records')

@callback(
    Output(f"{PAGE_ID}loading-indicator", "style"),
    Input(f"{PAGE_ID}dates-store", "data")
)
def toggle_loading_indicator(data):
    if data:
        return {'display': 'none'}
    return {'display': 'block'}

@callback(
    Output(f"{PAGE_ID}subsidiaria-filter", "data"),
    Input(f"{PAGE_ID}dates-store", "data")
)
def update_subsidiaria_options(data):
    if not data:
        return []
    df = pd.DataFrame(data)
    if "SUBSIDIARIA" in df.columns:
        unique_vals = sorted(df["SUBSIDIARIA"].dropna().unique().astype(str))
        return [{"label": val, "value": val} for val in unique_vals]
    return []

@callback(
    Output(f"{PAGE_ID}main-table", "children"),
    Input(f"{PAGE_ID}dates-store", "data"),
    Input(f"{PAGE_ID}date-filter", "value"),
    Input(f"{PAGE_ID}subsidiaria-filter", "value"),
)
def update_table(data, start_date, subsidiarias):
    if not data:
        return html.Div()
    
    df = pd.DataFrame(data)
    
    # Filtrar por fecha
    if start_date and "FECHA" in df.columns:
        try:
            df_temp = df.copy()
            df_temp["FECHA_DT"] = pd.to_datetime(df_temp["FECHA"], format='%d/%m/%Y', errors='coerce')
            start_date_dt = pd.to_datetime(start_date)
            
            if start_date_dt is not None:
                 df = df[df_temp["FECHA_DT"] == start_date_dt]
        except Exception as e:
            print(f"Error filtering date: {e}")
            
    # Filtrar por destinatario
    if subsidiarias and "SUBSIDIARIA" in df.columns:
        df = df[df["SUBSIDIARIA"] == subsidiarias]

    return AgGrid(
            id=f"{PAGE_ID}main-ag-grid",
            rowData=df.to_dict('records'),
            columnDefs=[{"field": x} for x in df.columns],
            columnSize="sizeToFit",
            
            dashGridOptions={
                
                "animateRows": True,
                "defaultColDef": {
                    "resizable": True,
                    "minWidth": 120
                }
            },
            style={"height": "400px"},
            className="ag-theme-quartz compact", 
        )

@callback(
    Output(f"{PAGE_ID}download-csv", "data"),
    Input(f"{PAGE_ID}btn-csv", "n_clicks"),
    State(f"{PAGE_ID}dates-store", "data"),
    State(f"{PAGE_ID}date-filter", "value"),
    State(f"{PAGE_ID}subsidiaria-filter", "value"),
    prevent_initial_call=True
)
def download_csv(n_clicks, data, start_date, subsidiaria):
    if not n_clicks or not data:
        return None
    
    df = pd.DataFrame(data)
    
    # Aplicar mismos filtros que la tabla
    if start_date and "FECHA" in df.columns:
        try:
            df_temp = df.copy()
            df_temp["FECHA_DT"] = pd.to_datetime(df_temp["FECHA"], format='%d/%m/%Y', errors='coerce')
            start_date_dt = pd.to_datetime(start_date)
            
            if start_date_dt is not None:
                 df = df[df_temp["FECHA_DT"] == start_date_dt]
        except Exception as e:
            print(f"Error filtering date in download: {e}")
            
    if subsidiaria and "SUBSIDIARIA" in df.columns:
        df = df[df["SUBSIDIARIA"] == subsidiaria]

    return dcc.send_data_frame(df.to_csv, f"ingresos_almacen_{int(time.time())}.csv", sep=";", index=False)

