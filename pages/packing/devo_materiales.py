import asyncio
import dash
import pandas as pd
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State
from components.grid import Row, Column
from components.simple_components import create_page_header
from constants import PAGE_TITLE_PREFIX
from helpers.helpers import generate_list_month
from dash_ag_grid import AgGrid
from helpers.get_sheets import read_sheet
import time
from datetime import datetime
from helpers.pdf_generator import generate_boleta_pdf

# 🚀 Configuraciones de rendimiento optimizadas
pd.options.mode.chained_assignment = None  # Evitar warnings de SettingWithCopyWarning
pd.options.compute.use_numba = True  # Usar Numba para operaciones numéricas si está disponible
pd.options.mode.sim_interactive = True  # Optimizar para operaciones interactivas


dash.register_page(__name__, "/devolucion-materiales", title=PAGE_TITLE_PREFIX + "Devolucion Materiales")
app = dash.get_app()
PAGE_ID = "devolucion-materiales-"
DATA_SOURCE = "devolucion_materiales"

def load_data_devolucion_materiales():
    print("📊 Cargando datos de Google Sheets...")
    data_rp = read_sheet("1av24G3C1A_SORqJorNBlHr_OT0iUejP8kNL8msQBdKU", "BD")
    data_rp = pd.DataFrame(data_rp[1:], columns=data_rp[0])    
    data_rp['id'] = data_rp.index
    data_rp =data_rp.rename(columns={
        "NOMBRE DEL CONDUCTOR": "CONDUCTOR", 
        "# JABAS VACIAS": "JABAS VACIAS",
        "# JARRAS VACIAS": "JARRAS VACIAS",
        "# PARIHUELAS": "PARIHUELAS",
        "# ESQUINEROS": "ESQUINEROS",
        "# JABAS CON DESCARTE":"JABAS CON DESCARTE",
        "# JARRAS CON DESCARTE":"JARRAS CON DESCARTE",
        

    })
    
    data_rp["FECHA"] = pd.to_datetime(data_rp["FECHA"], errors='coerce', format='%d/%m/%Y')
    data_rp["FECHA"] = data_rp["FECHA"].dt.strftime('%d/%m/%Y')
    data_rp["HORA"] =  data_rp["HORA"].astype(str)
    data_rp["HORA"] =  data_rp["HORA"].replace("nan", "-")
    data_rp["HORA"] =  data_rp["HORA"].replace("NaT", "-")
    data_rp["HORA"] =  data_rp["HORA"].replace("", "-")
    data_rp["HORA"] = data_rp["HORA"].fillna("-")
    
    data_rp["JABAS VACIAS"] = data_rp["JABAS VACIAS"].fillna(0)
    data_rp["JABAS VACIAS"] = data_rp["JABAS VACIAS"].replace("", 0)
    data_rp["JABAS VACIAS"] = data_rp["JABAS VACIAS"].astype(int)
    
    data_rp["JARRAS VACIAS"] = data_rp["JARRAS VACIAS"].fillna(0)
    data_rp["JARRAS VACIAS"] = data_rp["JARRAS VACIAS"].replace("", 0)
    data_rp["JARRAS VACIAS"] = data_rp["JARRAS VACIAS"].astype(int)

    data_rp["PARIHUELAS"] = data_rp["PARIHUELAS"].fillna(0)
    data_rp["PARIHUELAS"] = data_rp["PARIHUELAS"].replace("", 0)
    data_rp["PARIHUELAS"] = data_rp["PARIHUELAS"].astype(int)

    data_rp["ESQUINEROS"] = data_rp["ESQUINEROS"].fillna(0)
    data_rp["ESQUINEROS"] = data_rp["ESQUINEROS"].replace("", 0)
    data_rp["ESQUINEROS"] = data_rp["ESQUINEROS"].astype(int)


    data_rp["JABAS CON DESCARTE"] = data_rp["JABAS CON DESCARTE"].fillna(0)
    data_rp["JABAS CON DESCARTE"] = data_rp["JABAS CON DESCARTE"].replace("", 0)
    data_rp["JABAS CON DESCARTE"] = data_rp["JABAS CON DESCARTE"].astype(int)

    data_rp["JARRAS CON DESCARTE"] = data_rp["JARRAS CON DESCARTE"].fillna(0)
    data_rp["JARRAS CON DESCARTE"] = data_rp["JARRAS CON DESCARTE"].replace("", 0)
    data_rp["JARRAS CON DESCARTE"] = data_rp["JARRAS CON DESCARTE"].astype(int)

    
    data_rp["PESO BRUTO"] = data_rp["PESO BRUTO"].replace("", 0)
    data_rp["PESO BRUTO"] = data_rp["PESO BRUTO"].fillna(0)
    data_rp["PESO BRUTO"] = data_rp["PESO BRUTO"].astype(float)

    
    
    data_rp["PESO NETO"] = data_rp["PESO NETO"].replace("", 0)
    data_rp["PESO NETO"] = data_rp["PESO NETO"].fillna(0)
    data_rp["PESO NETO"] = data_rp["PESO NETO"].astype(float)

    data_rp["OBSERVACIONES"] = data_rp["OBSERVACIONES"].replace("", "-")
    return data_rp

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
                    create_page_header(
                        title="Devolucion Materiales",
                        #subtitle="Gestión y visualización de datos de devolucion de materiales"
                    )
                ], size=6),
                Column([
                    dmc.DateInput(
                        id=f"{PAGE_ID}date-filter",
                        label="Fecha",
                        placeholder="Seleccionar fecha",
                        clearable=True,
                        style={"width": "100%"},
                        #value=datetime.now(),
                        #type="multiple",
                    )
                ], size=3),
                Column([
                    dmc.MultiSelect(
                        id=f"{PAGE_ID}destinatario-filter",
                        label="Destinatario",
                        placeholder="Seleccionar destinatario",
                        searchable=True,
                        clearable=True,
                        style={"width": "100%"}
                    )
                ], size=3),
            ]),
            
            Row([
                Column([
                    html.Div(children=[
                        dmc.Loader(color="red", size="md", type="oval",id=f"{PAGE_ID}loading-indicator"),
                        html.Div(id=f"{PAGE_ID}main-table"),
                    ]),
                    
                    #html.Pre(id="pre-row-selection-callbacks-selected-rows", style={'textWrap': 'wrap'}),
                    dmc.Group([
                        dmc.Button(
                            "Generar PDF Boletas", 
                            id=f"{PAGE_ID}btn-pdf", 
                            color="red", 
                            variant="outline", 
                            #leftIcon=dmc.ThemeIcon(
                             #   color="red", 
                             #   variant="light", 
                             #   radius="xl", 
                             #   size="sm", 
                             #   children=html.I(className="fas fa-file-pdf")
                            #)
                        ),
                    ]),
                    dcc.Download(id=f"{PAGE_ID}download-pdf"),
                    
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
    df = load_data_devolucion_materiales()
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
    Output(f"{PAGE_ID}destinatario-filter", "data"),
    Input(f"{PAGE_ID}dates-store", "data")
)
def update_destinatario_options(data):
    if not data:
        return []
    df = pd.DataFrame(data)
    if "DESTINATARIO" in df.columns:
        unique_vals = sorted(df["DESTINATARIO"].dropna().unique().astype(str))
        return [{"label": val, "value": val} for val in unique_vals]
    return []

@callback(
    Output(f"{PAGE_ID}main-table", "children"),
    Input(f"{PAGE_ID}dates-store", "data"),
    Input(f"{PAGE_ID}date-filter", "value"),
    Input(f"{PAGE_ID}destinatario-filter", "value"),
)
def update_table(data, start_date, destinatarios):
    if not data:
        return html.Div()
    
    df = pd.DataFrame(data)
    
    # Filtrar por fecha
    if start_date and "FECHA" in df.columns:
        df["FECHA"] = pd.to_datetime(df["FECHA"], errors='coerce')
        # Asegurarse de que start_date y end_date sean datetime si no lo son
        # dmc.DateRangePicker puede devolver strings
        if start_date:
            df = df[(df["FECHA"] >= start_date)]
            
    # Filtrar por destinatario
    if destinatarios and "DESTINATARIO" in df.columns:
        df = df[df["DESTINATARIO"].isin(destinatarios)]

    return AgGrid(
            id=f"{PAGE_ID}main-ag-grid",
            rowData=df.to_dict('records'),
            #height="550px",
            columnDefs=[{"field": x} for x in df.columns],
            columnSize="sizeToFit",
            
            dashGridOptions={
                #"domLayout": "autoHeight",
                "rowSelection": {'mode': 'multiRow'},
                "animateRows": True,
                #"pagination": True,
                #"paginationPageSize": 20,
                "defaultColDef": {
                    #"sortable": True,
                    #"filter": True,
                    "resizable": True,
                    "minWidth": 120
                }
            },
            style={"height": "400px"},
            className="ag-theme-alpine-dark compact" , 
            #className="ag-theme-alpine"
        )
"""
@callback(
    Output(f"{PAGE_ID}main-tabl2", "children"),
    Input(f"{PAGE_ID}main-ag-grid", "selectedRows"),
    Input(f"{PAGE_ID}dates-store", "data"),
)
def output_selected_rows(selected_rows, data):
    if not selected_rows or not data:
        return html.Div()
    
    try:
        # Aseguramos que los IDs sean del mismo tipo (int)
        # Nota: data_rp['id'] = data_rp.index genera enteros
        selected_list = [s['id'] for s in selected_rows]
        
        df = pd.DataFrame(data)
        
        # Filtrar usando isin
        # Si df['id'] es int y selected_list tiene ints, funcionará
        df = df[df['id'].isin(selected_list)]

        return AgGrid(
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
            style={"height": "550px"},
            className="ag-theme-alpine-dark compact",
        )
    except Exception as e:
        print(f"Error filtering rows: {e}")
        return html.Div(f"Error: {e}")
"""
@callback(
    Output(f"{PAGE_ID}download-pdf", "data"),
    Input(f"{PAGE_ID}btn-pdf", "n_clicks"),
    State(f"{PAGE_ID}main-ag-grid", "selectedRows"),
    prevent_initial_call=True
)
def download_pdf(n_clicks, selected_rows):
    print(selected_rows)
    if not n_clicks or not selected_rows:
        return None
        
    try:
        # Generar PDF usando la función del helper
        # Pasamos la lista de filas seleccionadas directamente
        pdf_buffer = generate_boleta_pdf(selected_rows)
        
        # Retornar el archivo para descarga
        return dcc.send_bytes(pdf_buffer.getvalue(), filename=f"boletas_despacho_{int(time.time())}.pdf")
    except Exception as e:
        print(f"Error generando PDF: {e}")
        return None