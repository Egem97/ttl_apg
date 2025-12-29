import asyncio
import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, dcc, callback, Input, Output, State, ClientsideFunction, Patch, ALL, no_update
from components.grid import Row, Column
from components.simple_components import create_page_header
from constants import PAGE_TITLE_PREFIX
from helpers.helpers import generate_list_month,get_download_url_by_name,dataframe_filtro
from helpers.get_api import listar_archivos_en_carpeta_compartida
from helpers.get_token import get_access_token
from dash_ag_grid import AgGrid
from helpers.transform.costos import mayor_analitico_opex_transform,presupuesto_packing_transform,agrupador_costos_transform
from helpers.get_sheets import read_sheet
from helpers.transform.procesos_packing import *
from helpers.prediction_models import predict_kg_values, format_predictions_for_display, create_prediction_chart
from helpers.pdf_generator import create_pdf_from_dashboard_data

pd.options.mode.chained_assignment = None  # Evitar warnings de SettingWithCopyWarning
pd.options.compute.use_numba = True  

DRIVE_ID_COSTOS_PACKING = "b!DKrRhqg3EES4zcUVZUdhr281sFZAlBZDuFVNPqXRguBl81P5QY7KRpUL2n3RaODo"
ITEM_ID_COSTOS_PACKING = "01PNBE7BDDPRCTEUCL5ZFLQCKHUA4RJAF2"

dash.register_page(__name__, "/costos-packing", title=PAGE_TITLE_PREFIX + "Packing")

PAGE_ID = "costos-packing-"
DATA_SOURCE = "costos_packing"

def costos_packing_layout():
    return dmc.Container(
        children =[
            html.Div([
            dcc.Store(id=f"{PAGE_ID}dates-store"),      # Para datos de fechas generados
            dcc.Store(id=f"{PAGE_ID}raw-data-store"),   # Para datos crudos (carga única)
            dcc.Store(id=f"{PAGE_ID}filtered-data-store"), # Para datos filtrados
            dcc.Store(id=f"{PAGE_ID}cache-store"),      # Para cache de archivos cargados
            dcc.Store(id=f"{PAGE_ID}loading-trigger", data="init"),   # Para trigger de carga inicial
            dcc.Store(id=f"{PAGE_ID}modal-data-store"), # Para datos del modal
        ]),
        
    ],fluid=True)
    
layout = costos_packing_layout()