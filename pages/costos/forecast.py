from types import NoneType
import asyncio
import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State, ClientsideFunction
from components.grid import Row, Column
from components.simple_components import create_page_header
from constants import PAGE_TITLE_PREFIX
from helpers.helpers import generate_list_month,get_download_url_by_name,dataframe_filtro
from helpers.get_api import listar_archivos_en_carpeta_compartida
from helpers.get_token import get_access_token_packing
from dash_ag_grid import AgGrid
from helpers.transform.costos import mayor_analitico_opex_transform,presupuesto_packing_transform,agrupador_costos_transform
from helpers.get_sheets import read_sheet
from helpers.transform.procesos_packing import reporte_produccion_costos_transform
# 🚀 Configuraciones de rendimiento
pd.options.mode.chained_assignment = None  # Evitar warnings de SettingWithCopyWarning
pd.options.compute.use_numba = True  # Usar Numba para operaciones numéricas si está disponible
HOVER_TEMPLATE_STYLE = {
    "bgcolor": "rgba(255, 255, 255, 0.95)",
    "bordercolor": "rgba(0, 0, 0, 0.1)",
    #"borderwidth": 1,
    "font": {"size": 12, "color": "#2c3e50"},
    "align": "left"
}

DRIVE_ID_COSTOS_PACKING = "b!DKrRhqg3EES4zcUVZUdhr281sFZAlBZDuFVNPqXRguBl81P5QY7KRpUL2n3RaODo"
ITEM_ID_COSTOS_PACKING = "01PNBE7BDDPRCTEUCL5ZFLQCKHUA4RJAF2"

dash.register_page(__name__, "/costos-fore", title=PAGE_TITLE_PREFIX + "Costos**")
#dmc.add_figure_templates(default="mantine_light")

# Obtener la instancia de la app para clientside callbacks
app = dash.get_app()
PAGE_ID = "costos-forecast-"
DATA_SOURCE = "costos_forecast"

# Configuración para generate_list_month
START_YEAR = 2025  # Año desde cuando generar opciones
START_MONTH = 1    # Mes desde cuando generar opciones

# 🗄️ Cache global para datos
_data_cache = {
    "data": None,
    "last_loaded": None,
    "cache_duration": 300  # 5 minutos en segundos
}
def is_cache_valid():
    """Verificar si el caché es válido"""
    if _data_cache["data"] is None or _data_cache["last_loaded"] is None:
        return False
    
    from datetime import datetime, timedelta
    cache_age = datetime.now() - _data_cache["last_loaded"]
    return cache_age.total_seconds() < _data_cache["cache_duration"]

def create_custom_layout():
    """Layout personalizado con stores para filtros dependientes"""
    
    return dmc.Container([
        # 🗃️ Stores optimizados para eficiencia
        html.Div([
            dcc.Store(id=f"{PAGE_ID}dates-store"),      # Para datos de fechas generados
            dcc.Store(id=f"{PAGE_ID}raw-data-store"),   # Para datos crudos (carga única)
            dcc.Store(id=f"{PAGE_ID}filtered-data-store"), # Para datos filtrados
            dcc.Store(id=f"{PAGE_ID}cache-store"),      # Para cache de archivos cargados
            dcc.Store(id=f"{PAGE_ID}loading-trigger", data="init"),   # Para trigger de carga inicial
            dcc.Store(id=f"{PAGE_ID}modal-data-store"), # Para datos del modal
        ]),
        
        # 📊 Header personalizado
        dmc.Container([
                    Row([
                        Column([
                            create_page_header(
                                title="proyeccion de costos",
                                #subtitle="Filtros dependientes con generate_list_month"
                            )
                        ], size=5),
                    ]),
        ], fluid=True), 
            
    ], fluid=True)

    

layout = create_custom_layout()

