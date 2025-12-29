from types import NoneType
import asyncio
import dash
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State, ClientsideFunction,clientside_callback
from components.grid import Row, Column
from components.simple_components import create_page_header
from constants import PAGE_TITLE_PREFIX
from helpers.helpers import generate_list_month, get_download_url_by_name, dataframe_filtro
from helpers.get_api import listar_archivos_en_carpeta_compartida
from helpers.get_token import get_access_token
from dash_ag_grid import AgGrid
from helpers.get_sheets import read_sheet
import time
from datetime import datetime

# 🚀 Configuraciones de rendimiento optimizadas
pd.options.mode.chained_assignment = None  # Evitar warnings de SettingWithCopyWarning
pd.options.compute.use_numba = True  # Usar Numba para operaciones numéricas si está disponible
pd.options.mode.sim_interactive = True  # Optimizar para operaciones interactivas

# Configuraciones específicas para mejor rendimiento
HOVER_TEMPLATE_STYLE = {
    "bgcolor": "rgba(255, 255, 255, 0.95)",
    "bordercolor": "rgba(0, 0, 0, 0.1)",
    "font": {"size": 12, "color": "#2c3e50"},
    "align": "left"
}

# IDs de Google Drive
DRIVE_ID_CARPETA_STORAGE = "b!M5ucw3aa_UqBAcqv3a6affR7vTZM2a5ApFygaKCcATxyLdOhkHDiRKl9EvzaYbuR"
FOLDER_ID_CARPETA_STORAGE = "01XOBWFSBLVGULAQNEKNG2WR7CPRACEN7Q"

# Configuración de la página
dash.register_page(__name__, "/producto-terminado", title=PAGE_TITLE_PREFIX + "Producto Terminado")
app = dash.get_app()
PAGE_ID = "producto-terminado-"
DATA_SOURCE = "producto_terminado"

# 🗄️ Cache global optimizado para datos
_data_cache = {
    "data": None,
    "last_loaded": None,
    "cache_duration": 300  # 5 minutos en segundos
}

def is_cache_valid():
    """Verificar si el caché es válido"""
    if _data_cache["data"] is None or _data_cache["last_loaded"] is None:
        return False
    
    # Verificar si el caché ha expirado
    return time.time() - _data_cache["last_loaded"].timestamp() < _data_cache["cache_duration"]


def cleanup_memory():
    """Función para limpiar memoria y optimizar rendimiento"""
    import gc
    gc.collect()


def create_custom_layout():
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
        dmc.Container([
            Row([
                Column([
                    create_page_header(
                        title="Producto Terminado",
                        subtitle="Gestión y visualización de datos de producto terminado"
                    )
                ], size=6),
                Column([
                     dmc.Paper(
                        [
                            dmc.Group(
                                [dmc.Text("Test Card", c="dimmed", tt="uppercase", fw=700)],
                                justify="space-between"
                            ),
                            dmc.Group([dmc.Text("100000", size="lg", fw=700)], gap="xs"),
                            dmc.Group(
                                [
                                    dmc.Text(f"35%", size="xs"),
                                    dmc.Text("YoY change", size="xs", c="dimmed")
                                ],
                                c="teal" if 10000 > 0 else "red",
                                fw=500, gap=1,
                            )
                        ],
                        withBorder=True,
                        p="xs"
                    )
                ], size=3),
                Column([
                     dmc.Paper(
                        [
                            dmc.Group(
                                [dmc.Text("Test Card", c="dimmed", tt="uppercase", fw=700)],
                                justify="space-between"
                            ),
                            dmc.Group([dmc.Text("100000", size="lg", fw=700)], gap="xs"),
                            dmc.Group(
                                [
                                    dmc.Text(f"35%", size="xs"),
                                    dmc.Text("YoY change", size="xs", c="dimmed")
                                ],
                                c="teal" if 10000 > 0 else "red",
                                fw=500, gap=1,
                            )
                        ],
                        withBorder=True,
                        p="xs"
                    )
                ], size=3),
            ]),
            
            Row([
                Column([
                    dmc.LoadingOverlay(
                        
                        overlayProps={"radius": "sm", "blur": 2},
                        loaderProps={"variant": "bars", "size": "lg"},
                    ),
                    html.Div(id=f"{PAGE_ID}main-table")
                ], size=12),
            ]),
            # Indicador de carga
            
        ], fluid=True),
    ], fluid=True)

layout = create_custom_layout()

@callback(
    [
        Output(f"{PAGE_ID}raw-data-store", "data"),
        Output(f"{PAGE_ID}cache-store", "data"),
    ],
    Input(f"{PAGE_ID}loading-trigger", "id"),  # Se dispara una sola vez al cargar
    prevent_initial_call=False
)
async def load_all_data_once(_):
    try:
        print("🚀 Iniciando carga única de datos...")
        
        # 🗄️ Verificar caché primero
        if is_cache_valid():
            print("✅ Usando datos del caché")
            cache_info = {"loaded_at": _data_cache["last_loaded"].isoformat(), "files": [], "from_cache": True}
            return _data_cache["data"], cache_info
        
        print("🔄 Caché expirado o no disponible, cargando datos frescos...")
        
        # 🔑 Obtener token una sola vez
        access_token = await asyncio.to_thread(get_access_token)
        
        # 📁 Listar archivos una sola vez
        files_data = await asyncio.to_thread(
            listar_archivos_en_carpeta_compartida,
            access_token,
            DRIVE_ID_CARPETA_STORAGE,
            FOLDER_ID_CARPETA_STORAGE
        )
        
        # 📊 Cargar todos los archivos en paralelo (MUY EFICIENTE)
        print("📥 Iniciando carga paralela de archivos...")
        
        # Crear tareas para carga paralela
        async def load_excel_file(filename, sheet_name=None):
            url = await asyncio.to_thread(get_download_url_by_name, files_data, filename)
            if sheet_name:
                return await asyncio.to_thread(pd.read_excel, url, sheet_name=sheet_name)
            else:
                return await asyncio.to_thread(pd.read_excel, url)
        
        # Cargar archivos Excel en paralelo
        phl_pt_task = load_excel_file("REGISTRO DE PHL - PRODUCTO TERMINADO.xlsm", "TD-DATOS PT")
        
        # Ejecutar todas las tareas en paralelo
        phl_pt_df = await asyncio.gather(phl_pt_task)
        phl_pt_df = phl_pt_df[0]  # Extraer el DataFrame del resultado de gather
        
        print(f"📊 Datos cargados: {len(phl_pt_df)} filas")
        print(f"📋 Columnas disponibles: {list(phl_pt_df.columns)}")
        
        # Verificar si la columna existe antes de usarla
        if "F. PRODUCCION" in phl_pt_df.columns:
            print(f"📅 Fechas de producción únicas: {phl_pt_df['F. PRODUCCION'].unique()}")
            phl_pt_df = phl_pt_df[phl_pt_df["F. PRODUCCION"].notna()]
            print(f"📊 Datos después del filtro: {len(phl_pt_df)} filas")
        else:
            print("⚠️ Columna 'F. PRODUCCION' no encontrada en los datos")
        
        # Procesar columnas de fecha para AgGrid
        date_columns = [col for col in phl_pt_df.columns if "FECHA" in col.upper() or "F." in col]
        for col in date_columns:
            try:
                # Convertir a datetime y luego a string en formato ISO para AgGrid
                phl_pt_df[col] = pd.to_datetime(phl_pt_df[col], errors='coerce')
                phl_pt_df[col] = phl_pt_df[col].dt.strftime('%Y-%m-%d')
                print(f"✅ Columna {col} procesada como fecha")
            except Exception as e:
                print(f"⚠️ Error procesando columna de fecha {col}: {e}")
        
        # Aplicar transformación si es necesaria
        try:
            from helpers.transform.procesos_packing import phl_pt_transform
            phl_pt_df = await asyncio.to_thread(phl_pt_transform, phl_pt_df)
            print("✅ Transformación aplicada exitosamente")
        except Exception as e:
            print(f"⚠️ Error en transformación: {e}")
            # Continuar sin transformación si falla
        
        all_data = {
            "PHL PT": phl_pt_df.to_dict('records'),
        }
        
        # 🗄️ Actualizar caché
        _data_cache["data"] = all_data
        _data_cache["last_loaded"] = datetime.now()
        
        # 🧹 Limpiar memoria
        del phl_pt_df
        cleanup_memory()
        
        cache_info = {"loaded_at": _data_cache["last_loaded"].isoformat(), "files": [], "from_cache": False}
        print("✅ Carga de datos completada exitosamente")
        
        return all_data, cache_info
        
    except Exception as e:
        print(f"❌ Error en carga de datos: {e}")
        import traceback
        traceback.print_exc()
        return {}, {"error": str(e), "from_cache": False}


@callback(
    Output(f"{PAGE_ID}main-table", "children"),
    Input(f"{PAGE_ID}raw-data-store", "data"),
    prevent_initial_call=False
)
def update_main_table(raw_data):
    if not raw_data or "PHL PT" not in raw_data:
        return dmc.Alert(
            "No hay datos disponibles para mostrar",
            title="Sin datos",
            color="yellow",
            variant="light"
        )
    
    try:
        df = pd.DataFrame(raw_data.get("PHL PT", []))
        df["F. PRODUCCION"] = df["F. PRODUCCION"].astype(str)
        df["F. COSECHA"] = df["F. COSECHA"].str.strip()
        df = df.rename(columns={
            "F. PRODUCCION": "FECHA PRODUCCION",
            "F. COSECHA": "FECHA COSECHA",
        })
        print(df)
        
        # Debug: Verificar columnas de fecha
        #date_columns = [col for col in df.columns if "FECHA" in col.upper() or "F." in col]
        #print(f"🔍 Columnas de fecha encontradas: {date_columns}")
        #for col in date_columns:
        #    print(f"📅 Muestra de datos en {col}: {df[col].head(3).tolist()}")
        
        if df.empty:
            return dmc.Alert(
                "No hay registros de producto terminado para mostrar",
                title="Sin registros",
                color="blue",
                variant="light"
            )
        
        # Generar definiciones de columnas automáticamente
        
        
        print(f"📊 Mostrando tabla con {len(df)} filas y {len(df.columns)} columnas")
        
        return AgGrid(
            id=f"{PAGE_ID}main-ag-grid",
            rowData=df.to_dict("records"),
            columnDefs=[{"field": "CONTENERDOR", "pinned": True}, {"field": "SEMANA"}] +
                [{"field": i, 'type': 'rightAligned'} for i in df.columns if i != "CONTENERDOR"],
            columnSize="autoSize",
            defaultColDef={"filter": True},
            dashGridOptions={"animateRows": False, "rowSelection":'single'},
            #style={"height": "400px", "width": "100%"},
            
            className="ag-theme-alpine dbc-ag-grid",
            #theme="alpine"
        )
        
    except Exception as e:
        print(f"❌ Error al crear tabla: {e}")
        import traceback
        traceback.print_exc()
        return dmc.Alert(
            f"Error al cargar la tabla: {str(e)}",
            title="Error",
            color="red",
            variant="light"
        )

clientside_callback(
    ClientsideFunction(
        namespace="clientside",
        function_name="update_ag_grid_theme"
    ),
    Output(f"{PAGE_ID}main-ag-grid", "className"),
    Input("color-scheme-toggle", "checked")
)
def update_theme(switch_on):
    return "ag-theme-alpine-dark compact" if switch_on else "ag-theme-alpine compact"