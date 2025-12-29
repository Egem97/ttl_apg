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

# 🚀 Configuraciones de rendimiento
pd.options.mode.chained_assignment = None  # Evitar warnings de SettingWithCopyWarning
pd.options.compute.use_numba = True  # Usar Numba para operaciones numéricas si está disponible

HOVER_TEMPLATE_STYLE = {
    "bgcolor": "rgba(255, 255, 255, 0.95)",
    #"bordercolor": "rgba(0, 0, 0, 0.1)",
    #"borderwidth": 1,
    "font": {"size": 12, "color": "#2c3e50"},
    "align": "left"
}

DRIVE_ID_COSTOS_PACKING = "b!DKrRhqg3EES4zcUVZUdhr281sFZAlBZDuFVNPqXRguBl81P5QY7KRpUL2n3RaODo"
ITEM_ID_COSTOS_PACKING = "01PNBE7BDDPRCTEUCL5ZFLQCKHUA4RJAF2"


dash.register_page(__name__, "/costos-comparativo", title=PAGE_TITLE_PREFIX + "Comparativo")
app = dash.get_app()
PAGE_ID = "costos-comparativo-"
DATA_SOURCE = "costos_comparativo"
# Configuración para generate_list_month
START_YEAR = 2025  # Año desde cuando generar opciones
START_MONTH = 1  

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

def costos_comparativo_layout():
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
            dmc.Container([
                Row([
                    Column([
                        create_page_header(
                            title="💰 PPTO  vs Ejecutado",
                            #subtitle="Filtros dependientes con generate_list_month"
                        )
                    ], size=5),
                    
                    # 🔍 Filtros dependientes
                    Column([
                        dmc.Select(
                            id=f"{PAGE_ID}year",
                            label="Año",
                            placeholder="Seleccione Año",
                            clearable=False,
                            data=["2025"],  # Se llenará automáticamente
                            value="2025",
                            mb="md"
                        )
                    ], size=1),
                    
                    Column([
                        dmc.MultiSelect(
                            id=f"{PAGE_ID}month",
                                    label="Mes",
                            placeholder="Seleccione Mes",
                                    clearable=True,
                            data=[
                                {'label': 'Enero', 'value': '1'},
                                {'label': 'Febrero', 'value': '2'},
                                {'label': 'Marzo', 'value': '3'},
                                {'label': 'Abril', 'value': '4'},
                                {'label': 'Mayo', 'value': '5'},
                                {'label': 'Junio', 'value': '6'},
                                {'label': 'Julio', 'value': '7'},
                                {'label': 'Agosto', 'value': '8'},

                            ],
                            mb="md"
                        )
                    ], size=6),
                    
                ])
            ], fluid=True),
            dmc.Container([
                dmc.LoadingOverlay(
                                visible=True,
                                id="loading-overlay",
                                overlayProps={"radius": "sm", "blur": 2},
                                zIndex=100,
                    ),
                Row([
                    
                    Column([
                        
                            html.Div(id=f"{PAGE_ID}main-table")
                       
                    ],size=6),
                    Column([
                        dmc.Card([

                            dmc.ActionIcon(
                                    DashIconify(icon=f"feather:maximize"), 
                                    color="blue", 
                                    variant="default",
                                    id=f"{PAGE_ID}expand-chart-btn",
                                    n_clicks=0,
                                    mb=10,
                                    style={'position': 'absolute','z-index': '99'},
                                ),
                            dmc.SegmentedControl(
                                    id=f"{PAGE_ID}segmented-bar-comparativo",
                                    value="AGRUPADOR",
                                    data=[
                                        {"value": "AGRUPADOR", "label": "Agrupador"},
                                        {"value": "Mes", "label": "Mes"},
                                        
                                    ],
                                    mb=10,
                                    #color="#5c7cfa",
                                ),
                            dcc.Graph(id=f"{PAGE_ID}bar-comparativo")#,style={"height": "300px"}
                        ],withBorder=True,shadow="sm",radius="md",p=0,style={"position": "static"})
                    ],size=6),
                    
                ])
            
        ],fluid=True),
        
        # Modal para gráfico expandido
        dmc.Modal(
            id=f"{PAGE_ID}chart-modal",
            size="95%",
            title=dmc.Group([
                DashIconify(icon="mdi:chart-bar", width=24, color="#094782"),
                dmc.Text("Gráfico Comparativo - Vista Ampliada", fw=600, size="lg"),
                dmc.Badge("Análisis Detallado", color="blue", variant="light")
            ], justify="space-between", align="center"),
            children=[
                dmc.Container([
                    # Header con información del período
                    dmc.Paper([
                        dmc.Group([
                            dmc.Stack([
                                dmc.Text("📊 Análisis Comparativo", size="md", fw=600),
                                dmc.Text("Presupuesto vs Ejecutado por Categoría", size="sm", c="dimmed")
                            ], gap="xs"),
                            dmc.Group([
                                dmc.ActionIcon(
                                    DashIconify(icon="mdi:download"),
                                    id=f"{PAGE_ID}download-chart-btn",
                                    variant="light",
                                    color="blue",
                                    size="lg"
                                ),
                                dmc.ActionIcon(
                                    DashIconify(icon="mdi:fullscreen"),
                                    id=f"{PAGE_ID}fullscreen-chart-btn",
                                    variant="light",
                                    color="gray",
                                    size="lg"
                                ),
                                dmc.ActionIcon(
                                    DashIconify(icon="mdi:close"),
                                    id=f"{PAGE_ID}close-chart-modal-btn",
                                    variant="light",
                                    color="red",
                                    size="lg"
                                )
                            ], gap="xs")
                        ], justify="space-between", align="center")
                    ], p="md", withBorder=True, radius="md", mb="md"),
                    
                    # Gráfico expandido
                    dmc.Paper([
                        dmc.LoadingOverlay(
                            id=f"{PAGE_ID}chart-loading-overlay",
                            visible=False
                        ),
                            dcc.Graph(
                                id=f"{PAGE_ID}expanded-chart", 
                                style={"height": "75vh", "width": "100%"},
                                config={
                                    'displayModeBar': True,
                                    'displaylogo': False,
                                    'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'drawrect', 'eraseshape'],
                                    'modeBarButtonsToRemove': ['pan2d', 'select2d', 'lasso2d'],
                                    'toImageButtonOptions': {
                                        'format': 'png',
                                        'filename': 'grafico_comparativo',
                                        'height': 600,
                                        'width': 1000,
                                        'scale': 2
                                    }
                                }
                            ),
                            
                    ], p="md", withBorder=True, radius="md"),
                    
                    # Footer con estadísticas
                    dmc.Paper([
                        html.Div(id=f"{PAGE_ID}chart-stats", children=[
                            dmc.SimpleGrid([
                                dmc.Stack([
                                    dmc.Text("Total Presupuestado", size="sm", c="dimmed"),
                                    dmc.Text("$0.00", id=f"{PAGE_ID}total-presupuesto", size="lg", fw=700, c="blue")
                                ], gap="xs", align="center"),
                                dmc.Stack([
                                    dmc.Text("Total Ejecutado", size="sm", c="dimmed"),
                                    dmc.Text("$0.00", id=f"{PAGE_ID}total-ejecutado", size="lg", fw=700, c="green")
                                ], gap="xs", align="center"),
                                dmc.Stack([
                                    dmc.Text("Variación", size="sm", c="dimmed"),
                                    dmc.Text("0.0%", id=f"{PAGE_ID}variacion", size="lg", fw=700, c="gray")
                                ], gap="xs", align="center"),
                                dmc.Stack([
                                    dmc.Text("Categorías", size="sm", c="dimmed"),
                                    dmc.Text("0", id=f"{PAGE_ID}num-categorias", size="lg", fw=700)
                                ], gap="xs", align="center"),
                            ], cols=4, spacing="xl")
                        ])
                    ], p="md", withBorder=True, radius="md", mt="md")
                ], fluid=True, p=0)
            ],
            centered=True,
            overlayProps={"blur": 3, "opacity": 0.55, "color": "dark"},
            closeOnClickOutside=False,
            closeOnEscape=True,
            styles={
                "modal": {"backgroundColor": "#f8f9fa"},
                "header": {"backgroundColor": "#ffffff", "borderBottom": "1px solid #e9ecef"},
                "body": {"padding": "1rem"}
            }
        ),
        
        
        
        # Sección de Reportes
        dmc.Container([
            dmc.Divider(label="📄 Generación de Reportes", labelPosition="center", my="xl"),
            Row([
                Column([
                    dmc.Card([
                        dmc.Group([
                            dmc.Stack([
                                dmc.Text("Generar Reporte PDF", fw=600, size="lg"),
                                dmc.Text("Crea un reporte completo en formato PDF con análisis detallado de todos los gráficos y tablas", 
                                        size="sm", c="dimmed")
                            ], gap="xs"),
                            dmc.Group([
                                dmc.Button(
                                    "Vista Previa",
                                    id=f"{PAGE_ID}preview-pdf-btn",
                                    leftSection=DashIconify(icon="mdi:eye"),
                                    variant="outline",
                                    color="blue",
                                    size="md"
                                ),
                                dmc.Button(
                                    "Descargar PDF",
                                    id=f"{PAGE_ID}download-pdf-btn",
                                    leftSection=DashIconify(icon="mdi:file-pdf"),
                                    color="red",
                                    size="md"
                                )
                            ], gap="md")
                        ], justify="space-between", align="center")
                    ], withBorder=True, shadow="sm", radius="md", p="lg")
                ], size=12)
            ])
        ], fluid=True),
        
        # Modal para vista previa del PDF
        dmc.Modal(
            id=f"{PAGE_ID}pdf-preview-modal",
            size="90%",
            title=dmc.Group([
                DashIconify(icon="mdi:file-pdf", width=24),
                dmc.Text("Vista Previa del Reporte PDF", fw=600)
            ], gap="sm"),
            children=[
                    dmc.LoadingOverlay(
                        id=f"{PAGE_ID}pdf-loading-overlay",
                        visible=False
                    ),
                    dmc.Stack([
                        html.Div(id=f"{PAGE_ID}pdf-preview-content"),
                        dmc.Group([
                            dmc.Button(
                                "Descargar PDF",
                                id=f"{PAGE_ID}download-from-preview-btn",
                                leftSection=DashIconify(icon="mdi:download"),
                                color="red"
                            ),
                            dmc.Button(
                                "Cerrar",
                                id=f"{PAGE_ID}close-preview-btn",
                                variant="outline"
                            )
                        ], justify="center", mt="md")
                    ], gap="md"),
                    
            ],
            centered=True,
            overlayProps={"blur": 3, "opacity": 0.55, "color": "dark"},
            closeOnClickOutside=False,
            closeOnEscape=True,
        ),
        
        # Store para datos del PDF
        dcc.Store(id=f"{PAGE_ID}pdf-data-store"),
        dcc.Download(id=f"{PAGE_ID}pdf-download"),
        
        ],fluid=True,
    )

layout = costos_comparativo_layout()

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
            DRIVE_ID_COSTOS_PACKING,
            ITEM_ID_COSTOS_PACKING
        )
        
        # 📊 Cargar todos los archivos en paralelo (MUY EFICIENTE)
        print("📥 Iniciando carga paralela de archivos...")
        
        # Crear tareas para carga paralela
        async def load_excel_file(filename, sheet_name=None,skiprows=None):
            url = await asyncio.to_thread(get_download_url_by_name, files_data, filename)
            if sheet_name:
                return await asyncio.to_thread(pd.read_excel, url, sheet_name=sheet_name,skiprows=skiprows)
            else:
                return await asyncio.to_thread(pd.read_excel, url,skiprows=skiprows)
            
        
        # Cargar archivos Excel en paralelo
        mayor_analitico_task = load_excel_file("Mayor Analitico.xlsx")
        agrupador_costos_task = load_excel_file("AGRUPADOR_COSTOS.xlsx")
        presupuesto_packing_task = load_excel_file("PPTO PACKING.xlsx", "PRESUPUESTADO")
        kg_presupuesto_packing_task = load_excel_file("KG PPTO.xlsx",skiprows=1)
        
        
        # Ejecutar todas las tareas en paralelo
        mayor_analitico_df, agrupador_costos_df, presupuesto_packing_df, kg_presupuesto_packing_df = await asyncio.gather(
            mayor_analitico_task,
            agrupador_costos_task,
            presupuesto_packing_task,
            kg_presupuesto_packing_task
        )
        
        print("✅ Archivos Excel cargados en paralelo")
        
        # 📊 Cargar Google Sheets (esto es más rápido)
        print("📊 Cargando datos de Google Sheets...")
        data_rp = read_sheet("1OCBDYRmboSgcQIH0zJQqbAnwTB8f9zSIOaUWBWUXaUM", "RP")
        data_rp = pd.DataFrame(data_rp[1:], columns=data_rp[0])    
        df_rp = reporte_produccion_costos_transform(data_rp)
        
        # 🔄 Transformar datos en paralelo
        print("🔄 Transformando datos...")
        
        # Ejecutar transformaciones en paralelo
        presupuesto_task = asyncio.to_thread(presupuesto_packing_transform, presupuesto_packing_df)
        ma_task = asyncio.to_thread(mayor_analitico_opex_transform, mayor_analitico_df, agrupador_costos_df)
        agrupador_task = asyncio.to_thread(agrupador_costos_transform, agrupador_costos_df)
        kg_presupuesto_packing_task = asyncio.to_thread(kg_presupuesto_packing_transform, kg_presupuesto_packing_df)
        presupuesto_packing_df, ma_df, agrupador_costos_df, kg_presupuesto_packing_df = await asyncio.gather(
            presupuesto_task, ma_task, agrupador_task, kg_presupuesto_packing_task
        )
        
        # 📅 Procesar fechas
        ma_df["Fecha"] = pd.to_datetime(ma_df["Fecha"], errors='coerce')
        ma_df["Año"] = ma_df["Fecha"].dt.year
        ma_df["Mes"] = ma_df["Fecha"].dt.month
        ma_df["Semana"] = ma_df["Fecha"].dt.isocalendar().week
        
        # 🎯 Agrupar datos
        ma_df = ma_df.groupby(['Año','Mes','Semana','Fecha','Cod. Proyecto', 'Descripción Proyecto','Descripción Actividad','AGRUPADOR', 'SUB AGRUPADOR',])[["Dólares Cargo"]].sum().reset_index()
        
        # Debug: mostrar información de los datos cargados
        print(f"📊 Datos cargados - Mayor Analítico: {len(ma_df)} filas")
        if len(ma_df) > 0:
            print(f"📅 Años en Mayor Analítico: {sorted(ma_df['Año'].unique())}")
            print(f"📅 Meses en Mayor Analítico: {sorted(ma_df['Mes'].unique())}")
        
        print(f"📊 Datos cargados - Presupuesto Packing: {len(presupuesto_packing_df)} filas")
        if len(presupuesto_packing_df) > 0:
            print(f"📅 Años en Presupuesto: {sorted(presupuesto_packing_df['Año'].unique())}")
            print(f"📅 Meses en Presupuesto: {sorted(presupuesto_packing_df['Mes'].unique())}")
        
        print(f"📊 Datos cargados - Reporte Producción: {len(df_rp)} filas")
        
        # 📦 Preparar datos para retorno
        all_data = {
            "Mayor Analitico": ma_df.to_dict('records'),
            "Presupuesto Packing": presupuesto_packing_df.to_dict('records'),
            "Reporte Produccion": df_rp.to_dict('records'),
            "KG Presupuesto Packing": kg_presupuesto_packing_df.to_dict('records')
        }
        
        # 🗄️ Actualizar caché
        from datetime import datetime
        _data_cache["data"] = all_data
        _data_cache["last_loaded"] = datetime.now()
        
        # 🧹 Limpiar memoria
        del ma_df, mayor_analitico_df, agrupador_costos_df, presupuesto_packing_df
        
        cache_info = {"loaded_at": _data_cache["last_loaded"].isoformat(), "files": [], "from_cache": False}
        print("✅ Carga de datos completada exitosamente")
        
        return all_data, cache_info
        
    except Exception as e:
        print(f"🚨 Error en carga inicial: {e}")
        return {}, {"error": str(e)}

# 2. 🎯 Callback para filtrado LOCAL eficiente (sin llamadas API)
@callback(
    Output(f"{PAGE_ID}filtered-data-store", "data"),
    [
        Input(f"{PAGE_ID}year", "value"),
        Input(f"{PAGE_ID}month", "value"),
        Input(f"{PAGE_ID}raw-data-store", "data")
        #Input(f"{PAGE_ID}week", "value")
    ],
    #State(f"{PAGE_ID}raw-data-store", "data"),
    #prevent_initial_call=False  # Cargar datos inicialmente sin filtros
)
def filter_data_locally(year, month, raw_data):
        
        
        if not raw_data:
            print("⚠️ No hay datos crudos disponibles")
            return {}
        
        year_int = int(year) if year else None
        
        # Manejar MultiSelect para meses
        if month and isinstance(month, list) and len(month) > 0:
            month_ints = [int(m) for m in month]
        elif month and not isinstance(month, list):
            month_ints = [int(month)]
        else:
            month_ints = None
        
        print(f"🔍 Valores procesados - Año: {year_int}, Mes: {month_ints}")
        
        # 🚀 Crear DataFrames de manera más eficiente
        mayor_analitico_df = pd.DataFrame(raw_data.get("Mayor Analitico", []))
        reporte_produccion_df = pd.DataFrame(raw_data.get("Reporte Produccion", []))
        presupuesto_packing_df = pd.DataFrame(raw_data.get("Presupuesto Packing", []))
        kg_presupuesto_packing_df = pd.DataFrame(raw_data.get("KG Presupuesto Packing", []))
        
        # Verificar si hay datos
        if len(mayor_analitico_df) == 0 and len(reporte_produccion_df) == 0 and len(presupuesto_packing_df) == 0:
            print("⚠️ No hay datos para filtrar")
            return {}
        
        # 🎯 Aplicar filtros de manera más inteligente
        if year_int is not None:
            # Crear máscaras booleanas (más eficiente que query)
            year_mask = mayor_analitico_df['Año'] == year_int
            
            if month_ints is not None and len(month_ints) > 0:
                # Filtrar por año y meses específicos
                month_mask = mayor_analitico_df['Mes'].isin(month_ints)
                combined_mask = year_mask & month_mask
                print(f"🔍 Aplicando filtros por año ({year_int}) y meses ({month_ints})")
            else:
                # Solo filtrar por año
                combined_mask = year_mask
                print(f"🔍 Aplicando filtro solo por año ({year_int}) - sin filtro de meses")
            
            try:
                # Aplicar filtros usando máscaras booleanas (más rápido que query)
                mayor_analitico_df = mayor_analitico_df[combined_mask].copy()
                
                # Aplicar los mismos filtros a los otros DataFrames
                if len(reporte_produccion_df) > 0:
                    year_mask_rp = reporte_produccion_df['Año'] == year_int
                    if month_ints is not None and len(month_ints) > 0:
                        month_mask_rp = reporte_produccion_df['Mes'].isin(month_ints)
                        combined_mask_rp = year_mask_rp & month_mask_rp
                    else:
                        combined_mask_rp = year_mask_rp
                    reporte_produccion_df = reporte_produccion_df[combined_mask_rp].copy()
                
                if len(presupuesto_packing_df) > 0:
                    year_mask_pp = presupuesto_packing_df['Año'] == year_int
                    if month_ints is not None and len(month_ints) > 0:
                        month_mask_pp = presupuesto_packing_df['Mes'].isin(month_ints)
                        combined_mask_pp = year_mask_pp & month_mask_pp
                    else:
                        combined_mask_pp = year_mask_pp
                    presupuesto_packing_df = presupuesto_packing_df[combined_mask_pp].copy()
                
                print(f"✅ Filtros aplicados exitosamente")
                print(f"📊 Resultados - Mayor Analítico: {len(mayor_analitico_df)} filas, Presupuesto: {len(presupuesto_packing_df)} filas")
                
            except Exception as e:
                print(f"❌ Error aplicando filtros: {e}")
                print("📊 Mostrando todos los datos debido a error en filtros")
        else:
            print("📊 Sin filtros aplicados - mostrando todos los datos")
        
        # 📦 Preparar datos para retorno de manera más eficiente
        all_data_dict = {
            "Mayor Analitico": mayor_analitico_df.to_dict('records') if len(mayor_analitico_df) > 0 else [],
            "Reporte Produccion": reporte_produccion_df.to_dict('records') if len(reporte_produccion_df) > 0 else [],
            "Presupuesto Packing": presupuesto_packing_df.to_dict('records') if len(presupuesto_packing_df) > 0 else []
        }
        
        # 🧹 Limpiar memoria
        del mayor_analitico_df, reporte_produccion_df, presupuesto_packing_df
        
        return all_data_dict

# Callback para la tabla principal con datos de ejemplo
@callback(
    Output(f"{PAGE_ID}main-table", "children"),
    Output(f"{PAGE_ID}bar-comparativo", "figure"),
    Output("loading-overlay", "visible", allow_duplicate=True),
    Input(f"{PAGE_ID}filtered-data-store", "data"),
    Input(f"{PAGE_ID}segmented-bar-comparativo", "value"),
    prevent_initial_call=True
)
def update_main_table(filtered_data,segmented_bar_comparativo):
        df = pd.DataFrame(filtered_data.get("Presupuesto Packing", []))
        df_rp = pd.DataFrame(filtered_data.get("Reporte Produccion", []))
        df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
        df_kg = pd.DataFrame(filtered_data.get("KG Presupuesto Packing", []))
        
        
        
        presupuesto_group = df.groupby(["Año", "Mes", "ITEM_CORREGIDO", "MES"])[["IMPORTE"]].sum().reset_index()
        presupuesto_group = presupuesto_group.rename(columns={"ITEM_CORREGIDO": "Descripción Proyecto", "IMPORTE": "IMPORTE PRESUPUESTO"})
        mayor_analitico_group = df_ma.groupby(["Año", "Mes", "Descripción Proyecto", "AGRUPADOR"])[["Dólares Cargo"]].sum().reset_index()
        mayor_analitico_group = mayor_analitico_group.rename(columns={"Dólares Cargo": "IMPORTE MAYOR ANALITICO"})
        comparativo_ejec_presupuesto = pd.merge(
                presupuesto_group, 
                mayor_analitico_group, 
                on=["Año", "Mes", "Descripción Proyecto"], 
                how="left"
        )
        comparativo_ejec_presupuesto_table = comparativo_ejec_presupuesto.groupby(["AGRUPADOR"])[["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"]].sum().reset_index()
        
        # Crear una copia para el gráfico con valores numéricos
        df_grafico = comparativo_ejec_presupuesto.groupby([segmented_bar_comparativo])[["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"]].sum().reset_index()
        if segmented_bar_comparativo == "Mes":
            
            df_grafico = df_grafico[df_grafico["IMPORTE MAYOR ANALITICO"]>0]
        # Calcular totales antes de formatear
        total_presupuesto = comparativo_ejec_presupuesto_table["IMPORTE PRESUPUESTO"].sum()
        total_ejecutado = comparativo_ejec_presupuesto_table["IMPORTE MAYOR ANALITICO"].sum()
        
        # Formatear los valores numéricos antes de enviar a AgGrid
        comparativo_ejec_presupuesto_table["IMPORTE PRESUPUESTO"] = comparativo_ejec_presupuesto_table["IMPORTE PRESUPUESTO"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
        comparativo_ejec_presupuesto_table["IMPORTE MAYOR ANALITICO"] = comparativo_ejec_presupuesto_table["IMPORTE MAYOR ANALITICO"].apply(lambda x: f"${x:,.2f}" if pd.notna(x) else "$0.00")
        comparativo_ejec_presupuesto_table = comparativo_ejec_presupuesto_table.rename(columns={"IMPORTE PRESUPUESTO": "$ PPTO", "IMPORTE MAYOR ANALITICO": "$ Ejecutado"})
        """
        
        """
        
        ma_week_df = df_ma.groupby(["Año", "Semana", "Mes"])[["Dólares Cargo"]].sum().reset_index()
        rp_week_df = df_rp.groupby(["Año", "Mes", "SEMANA"])[["KG_EXPORTABLES","KG_PROCESADOS"]].sum().reset_index()
        rp_week_df = rp_week_df.rename(columns={"SEMANA": "Semana"})
        
        #rp_week_df.to_excel("rp_week_df.xlsx",index=False)
        # Crear fila de totales formateada
        fila_totales = {
            "AGRUPADOR": "TOTAL",
            "$ PPTO": f"${total_presupuesto:,.2f}",
            "$ Ejecutado": f"${total_ejecutado:,.2f}"
        }
        
        
        # Crear columnDefs con configuración específica para cada columna
        column_defs = []
        for col in comparativo_ejec_presupuesto_table.columns:
            if col in ["$ PPTO", "$ Ejecutado"]:
                # Columnas de importes ya formateadas como texto
                column_defs.append({
                    "field": col,
                    "headerName": col,
                    "type": "textColumn",
                    "cellStyle": {"textAlign": "right", "fontWeight": ""},
                    "width": 100
                })
            else:
                # Columnas de texto
                column_defs.append({
                    "field": col,
                    "headerName": col,
                    "type": "textColumn",
                    "width": 250
                })
        table_out = AgGrid(
                    id=f"{PAGE_ID}main-ag-grid",
                    rowData=comparativo_ejec_presupuesto_table.to_dict('records'),
                    columnDefs=column_defs,
                    dashGridOptions={
                        "domLayout": "autoHeight",
                        "rowSelection": "single",
                        "animateRows": True,
                        #"pagination": True,
                        "pinnedBottomRowData": [fila_totales],
                        "defaultColDef": {
                            "sortable": True,
                            "filter": True,
                            "resizable": True,
                            "minWidth": 100
                        }
                    },
                    #style={"height": "400px", "width": "100%"},
                    className="ag-theme-balham compac compact", 
                    #className="ag-theme-alpine"
                )
        # Crear el gráfico con los valores numéricos originales
        fig = px.bar(
            df_grafico, 
            x=segmented_bar_comparativo, 
            y=["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"], 
            title="Comparativo PPTO vs Ejecutado",
            template="mantine_light",
            barmode="group",
            height=250,
            color_discrete_map={
                "IMPORTE PRESUPUESTO": "#094782",  # Azul para presupuesto
                "IMPORTE MAYOR ANALITICO": "#0b72d7"  # Naranja para ejecutado
            },
            
        )
        fig.update_traces(cliponaxis=False, selector=dict(type='bar'))
        # Personalizar el gráfico
        fig.update_layout(
            margin=dict(t=40, b=0, l=0, r=0),
            xaxis_title="",
            yaxis_title="Importe ($)",
            legend_title="",
            hovermode="x unified",
            title=dict(
                text="Comparativo PPTO vs Ejecutado",
                font=dict(size=16, color="black", weight="bold")
            ),
            font=dict(
                size=9,
                color="black"
            ),
            # Mejorar el hoverlabel
            hoverlabel=dict(
                bgcolor="white",
                #bordercolor="black",
                #borderwidth=1,
                font_size=12,
                font_family="Arial, sans-serif"
            )
        )
        
        # Configurar el eje Y para mostrar valores completos sin abreviación
        fig.update_yaxes(
            tickformat=",",
            tickmode="auto",
            nticks=10
        )
        
        # Configurar leyenda
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
        ))
        
        # Agregar etiquetas de datos en las barras
        fig.update_traces(
            texttemplate='%{y:,.0f}',
            textposition='outside',
            textfont=dict(size=8, color="black"),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         'Categoría: %{x}<br>' +
                         'Importe: $%{y:,.2f}<br>' +
                         '<extra></extra>'
        )
        
        # Actualizar las etiquetas de la leyenda
        fig.data[0].name = "Presupuesto"
        fig.data[1].name = "Ejecutado"
        return (table_out,fig,False)

def create_expanded_chart(df_grafico):
    """Crear versión expandida del gráfico para el modal"""
    fig = px.bar(
        df_grafico, 
        x="AGRUPADOR", 
        y=["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"], 
        title="Comparativo PPTO vs Ejecutado - Vista Ampliada",
        template="mantine_light",
        barmode="group",
        height=600,
        color_discrete_map={
            "IMPORTE PRESUPUESTO": "#094782",  # Azul para presupuesto
            "IMPORTE MAYOR ANALITICO": "#0b72d7"  # Naranja para ejecutado
        },
        
    )
    
    # Personalizar el gráfico expandido
    fig.update_layout(
        margin=dict(t=80, b=60, l=80, r=40),
        xaxis_title="Categoría de Costos",
        yaxis_title="Importe ($)",
        legend_title="",
        hovermode="x unified",
        title=dict(
            text="Comparativo PPTO vs Ejecutado - Vista Ampliada",
            font=dict(size=20, color="black", weight="bold")
        ),
        font=dict(
            size=14,
            color="black"
        ),
        # Hoverlabel mejorado para vista expandida
        hoverlabel=dict(
            bgcolor="rgba(255, 255, 255, 0.95)",
            #bordercolor="#1f77b4",
            #borderwidth=2,
            font_size=14,
            font_family="Arial, sans-serif",
            font_color="black"
        )
    )
    
    # Configurar el eje Y para mostrar valores completos sin abreviación
    fig.update_yaxes(
        tickformat=",",
        tickmode="auto",
        nticks=15,
        title_font=dict(size=16, weight="bold"),
        tickfont=dict(size=12)
    )
    
    # Configurar el eje X
    fig.update_xaxes(
        title_font=dict(size=16, weight="bold"),
        tickfont=dict(size=12),
        tickangle=45
    )
    
    # Configurar leyenda
    fig.update_layout(legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="right",
        x=1,
        font=dict(size=14, weight="bold")
    ))
    
    # Agregar etiquetas de datos en las barras
    fig.update_traces(
        texttemplate='%{y:,.0f}',
        textposition='outside',
        textfont=dict(size=12, color="black"),
        hovertemplate='<b>%{fullData.name}</b><br>' +
                     'Categoría: %{x}<br>' +
                     'Importe: $%{y:,.2f}<br>' +
                     '<extra></extra>'
    )
    
    # Actualizar las etiquetas de la leyenda
    fig.data[0].name = "Presupuesto"
    fig.data[1].name = "Ejecutado"
    
    return fig
     
# Callback para actualizar la fila de totales dinámicamente 
@callback(
    Output(f"{PAGE_ID}main-ag-grid", "dashGridOptions"),
    Input(f"{PAGE_ID}main-ag-grid", "virtualRowData"),
    prevent_initial_call=False
)
def update_totals_row(data):
    if not data:
        return Patch()
    
    # Convertir los datos virtuales a DataFrame
    df_virtual = pd.DataFrame(data)
    
    # Extraer valores numéricos de las columnas formateadas
    def extract_numeric(value):
        if isinstance(value, str) and value.startswith('$'):
            return float(value.replace('$', '').replace(',', ''))
        return 0
    
    # Calcular totales
    total_presupuesto = sum(df_virtual["$ PPTO"].apply(extract_numeric))
    total_ejecutado = sum(df_virtual["$ Ejecutado"].apply(extract_numeric))
    
    # Crear fila de totales actualizada
    fila_totales_actualizada = {
        "AGRUPADOR": "TOTAL",
        "$ PPTO": f"${total_presupuesto:,.2f}",
        "$ Ejecutado": f"${total_ejecutado:,.2f}"
    }
    
    # Actualizar la fila de totales
    grid_option_patch = Patch()
    grid_option_patch["pinnedBottomRowData"] = [fila_totales_actualizada]
    
    return grid_option_patch



# Callback para preparar datos del PDF
@callback(
    Output(f"{PAGE_ID}pdf-data-store", "data"),
    Input(f"{PAGE_ID}filtered-data-store", "data"),
    State(f"{PAGE_ID}bar-comparativo", "figure"),
    prevent_initial_call=True
)
def prepare_pdf_data(filtered_data, main_chart):
    if not filtered_data:
        return {}
    
    print(f"Debug - prepare_pdf_data llamado")
    print(f"Debug - main_chart disponible: {main_chart is not None}")
    if main_chart:
        print(f"Debug - tipo de main_chart: {type(main_chart)}")
        print(f"Debug - claves en main_chart: {list(main_chart.keys()) if isinstance(main_chart, dict) else 'No es dict'}")
    
    try:
        # Preparar datos de resumen
        df = pd.DataFrame(filtered_data.get("Presupuesto Packing", []))
        df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
        
        if len(df) > 0 and len(df_ma) > 0:
            presupuesto_group = df.groupby(["Año", "Mes", "ITEM_CORREGIDO", "MES"])[["IMPORTE"]].sum().reset_index()
            presupuesto_group = presupuesto_group.rename(columns={"ITEM_CORREGIDO": "Descripción Proyecto", "IMPORTE": "IMPORTE PRESUPUESTO"})
            mayor_analitico_group = df_ma.groupby(["Año", "Mes", "Descripción Proyecto", "AGRUPADOR"])[["Dólares Cargo"]].sum().reset_index()
            mayor_analitico_group = mayor_analitico_group.rename(columns={"Dólares Cargo": "IMPORTE MAYOR ANALITICO"})
            
            comparativo_ejec_presupuesto = pd.merge(
                presupuesto_group, 
                mayor_analitico_group, 
                on=["Año", "Mes", "Descripción Proyecto"], 
                how="left"
            )
            comparativo_ejec_presupuesto_table = comparativo_ejec_presupuesto.groupby(["AGRUPADOR"])[["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"]].sum().reset_index()
            
            total_presupuesto = comparativo_ejec_presupuesto_table["IMPORTE PRESUPUESTO"].sum()
            total_ejecutado = comparativo_ejec_presupuesto_table["IMPORTE MAYOR ANALITICO"].sum()
            variacion_porcentual = ((total_ejecutado - total_presupuesto) / total_presupuesto * 100) if total_presupuesto > 0 else 0
            
            # Formatear tabla para PDF
            tabla_formateada = comparativo_ejec_presupuesto_table.copy()
            tabla_formateada["IMPORTE PRESUPUESTO"] = tabla_formateada["IMPORTE PRESUPUESTO"].apply(lambda x: f"${x:,.2f}")
            tabla_formateada["IMPORTE MAYOR ANALITICO"] = tabla_formateada["IMPORTE MAYOR ANALITICO"].apply(lambda x: f"${x:,.2f}")
            tabla_formateada = tabla_formateada.rename(columns={"IMPORTE PRESUPUESTO": "$ PPTO", "IMPORTE MAYOR ANALITICO": "$ Ejecutado"})
            

            
            # Regenerar el gráfico principal aquí para asegurar que esté disponible
            print("Debug - Regenerando gráfico principal para PDF...")
            df_grafico_pdf = comparativo_ejec_presupuesto.groupby(["AGRUPADOR"])[["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"]].sum().reset_index()
            
            # Crear gráfico para PDF
            import plotly.express as px
            fig_pdf = px.bar(
                df_grafico_pdf, 
                x="AGRUPADOR", 
                y=["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"], 
                title="Comparativo PPTO vs Ejecutado",
                template="plotly_white",  # Cambio a template más simple
                barmode="group",
                height=400,
                color_discrete_map={
                    "IMPORTE PRESUPUESTO": "#094782",
                    "IMPORTE MAYOR ANALITICO": "#0b72d7"
                }
            )
            
            # Configurar el gráfico para PDF
            fig_pdf.update_layout(
                margin=dict(t=60, b=40, l=40, r=40),
                xaxis_title="Categoría",
                yaxis_title="Importe ($)",
                legend_title="",
                title=dict(
                    text="Comparativo PPTO vs Ejecutado",
                    font=dict(size=16, color="black")
                ),
                font=dict(size=12, color="black"),
                showlegend=True
            )
            
            # Actualizar las etiquetas de la leyenda
            fig_pdf.data[0].name = "Presupuesto"
            fig_pdf.data[1].name = "Ejecutado"
            
            print("Debug - Gráfico PDF generado exitosamente")
            
            return {
                'charts': {
                    'main_chart': fig_pdf.to_dict()  # Usar el gráfico regenerado
                },
                'tables': {
                    'main_table': tabla_formateada.to_dict('records')
                },
                'summary': {
                    'total_presupuesto': total_presupuesto,
                    'total_ejecutado': total_ejecutado,
                    'variacion_porcentual': variacion_porcentual,
                    'num_categorias': len(comparativo_ejec_presupuesto_table)
                }
            }
    except Exception as e:
        print(f"Error preparando datos PDF: {e}")
        return {}
    
    return {}

# Callback para vista previa del PDF
@callback(
    Output(f"{PAGE_ID}pdf-preview-modal", "opened"),
    Output(f"{PAGE_ID}pdf-preview-content", "children"),
    Output(f"{PAGE_ID}pdf-loading-overlay", "visible"),
    Input(f"{PAGE_ID}preview-pdf-btn", "n_clicks"),
    Input(f"{PAGE_ID}close-preview-btn", "n_clicks"),
    State(f"{PAGE_ID}pdf-data-store", "data"),
    State(f"{PAGE_ID}pdf-preview-modal", "opened"),
    prevent_initial_call=True
)
def handle_pdf_preview(preview_clicks, close_clicks, pdf_data, modal_opened):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, "", False
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == f"{PAGE_ID}close-preview-btn":
        return False, "", False
    
    if trigger_id == f"{PAGE_ID}preview-pdf-btn" and preview_clicks:
        if not pdf_data:
            return True, dmc.Alert(
                "No hay datos disponibles para generar el reporte",
                title="Error",
                color="red",
                icon=DashIconify(icon="mdi:alert")
            ), False
        
        # Crear vista previa del contenido del PDF
        preview_content = create_pdf_preview_content(pdf_data)
        return True, preview_content, False
    
    return modal_opened, dash.no_update, False

# Callback para descargar PDF
@callback(
    Output(f"{PAGE_ID}pdf-download", "data"),
    Input(f"{PAGE_ID}download-pdf-btn", "n_clicks"),
    Input(f"{PAGE_ID}download-from-preview-btn", "n_clicks"),
    State(f"{PAGE_ID}pdf-data-store", "data"),
    prevent_initial_call=True
)
def download_pdf(download_clicks, preview_download_clicks, pdf_data):
    if not pdf_data or (not download_clicks and not preview_download_clicks):
        return dash.no_update
    
    try:
        # Generar PDF usando función simplificada
        from datetime import datetime
        
        filename = f"reporte_financiero_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_buffer = generate_simple_pdf_report(pdf_data)
        
        return dcc.send_bytes(pdf_buffer.getvalue(), filename)
        
    except Exception as e:
        print(f"Error generando PDF: {e}")
        import traceback
        traceback.print_exc()
        return dash.no_update

def create_pdf_preview_content(pdf_data):
    """Crear contenido de vista previa del PDF"""
    if not pdf_data:
        return dmc.Alert("No hay datos disponibles", color="red")
    
    from datetime import datetime
    summary = pdf_data.get('summary', {})
    
    return dmc.Stack([
        # Encabezado
        dmc.Paper([
            dmc.Group([
                DashIconify(icon="mdi:file-pdf", width=32, color="#d32f2f"),
                dmc.Stack([
                    dmc.Text("Reporte de Análisis de Costos Packing", size="xl", fw=700),
                    dmc.Text(f"Comparativo Presupuesto vs Ejecutado - {datetime.now().strftime('%d de %B de %Y')}", 
                            size="sm", c="dimmed")
                ], gap="xs")
            ], gap="md")
        ], p="md", withBorder=True, radius="md"),
        
        # Resumen ejecutivo
        dmc.Paper([
            dmc.Stack([
                dmc.Text("📋 Resumen Ejecutivo", size="lg", fw=600),
                dmc.SimpleGrid([
                    dmc.Stack([
                        dmc.Text("Total Presupuestado", size="sm", c="dimmed"),
                        dmc.Text(f"${summary.get('total_presupuesto', 0):,.2f}", size="lg", fw=700, c="blue")
                    ], gap="xs"),
                    dmc.Stack([
                        dmc.Text("Total Ejecutado", size="sm", c="dimmed"),
                        dmc.Text(f"${summary.get('total_ejecutado', 0):,.2f}", size="lg", fw=700, c="green")
                    ], gap="xs"),
                    dmc.Stack([
                        dmc.Text("Variación", size="sm", c="dimmed"),
                        dmc.Text(f"{summary.get('variacion_porcentual', 0):.1f}%", 
                                size="lg", fw=700, 
                                c="red" if summary.get('variacion_porcentual', 0) > 0 else "green")
                    ], gap="xs"),
                    dmc.Stack([
                        dmc.Text("Categorías", size="sm", c="dimmed"),
                        dmc.Text(f"{summary.get('num_categorias', 0)}", size="lg", fw=700)
                    ], gap="xs"),
                ], cols=4, spacing="md")
            ], gap="md")
        ], p="md", withBorder=True, radius="md"),
        
        # Contenido incluido
        dmc.Paper([
            dmc.Stack([
                dmc.Text("📄 Contenido del Reporte", size="lg", fw=600),
                dmc.List([
                    dmc.ListItem("Gráfico comparativo principal con análisis detallado"),
                    dmc.ListItem("Tabla de datos por categorías con formateo profesional"),
                    dmc.ListItem("Conclusiones y recomendaciones automáticas"),
                    dmc.ListItem("Formato profesional en PDF A4 optimizado para impresión")
                ], icon=DashIconify(icon="mdi:check", color="green"))
            ], gap="md")
        ], p="md", withBorder=True, radius="md"),
        
        # Información adicional
        dmc.Alert(
            "El reporte se generará en formato PDF con diseño profesional, incluyendo gráficos de alta resolución y análisis detallado de cada sección.",
            title="Información",
            color="blue",
            icon=DashIconify(icon="mdi:information")
        )
    ], gap="md")

def generate_simple_pdf_report(pdf_data):
    """Función simplificada para generar PDF sin ambigüedades de DataFrame"""
    import io
    from datetime import datetime
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import plotly.graph_objects as go
    import plotly.io as pio
    from reportlab.platypus import Image
    
    try:
        # Crear buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        # Estilos
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#094782')
        ))
        
        styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#0b72d7')
        ))
        
        story = []
        
        # Título
        title = Paragraph("📊 Reporte de Análisis Financiero", styles['CustomTitle'])
        story.append(title)
        
        # Fecha
        current_date = datetime.now().strftime("%d de %B de %Y")
        subtitle = Paragraph(f"Comparativo Presupuesto vs Ejecutado - {current_date}", styles['CustomSubtitle'])
        story.append(subtitle)
        story.append(Spacer(1, 20))
        
        # Resumen ejecutivo
        summary = pdf_data.get('summary', {})
        if summary:
            story.append(Paragraph("📋 Resumen Ejecutivo", styles['CustomSubtitle']))
            
            summary_text = f"""
            <b>Datos del período analizado:</b><br/>
            • Total Presupuestado: ${summary.get('total_presupuesto', 0):,.2f}<br/>
            • Total Ejecutado: ${summary.get('total_ejecutado', 0):,.2f}<br/>
            • Variación: {summary.get('variacion_porcentual', 0):.1f}%<br/>
            • Número de categorías: {summary.get('num_categorias', 0)}
            """
            
            story.append(Paragraph(summary_text, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Gráfico principal
        charts = pdf_data.get('charts', {})
        main_chart_data = charts.get('main_chart')
        
        print(f"Debug - main_chart_data disponible: {main_chart_data is not None}")
        if main_chart_data:
            print(f"Debug - tipo de main_chart_data: {type(main_chart_data)}")
            
        story.append(Paragraph("📊 Gráfico Comparativo Principal", styles['CustomSubtitle']))
        
        if main_chart_data:
            try:
                print("Debug - Intentando convertir gráfico principal...")
                
                # Asegurarse de que es un dict válido
                if isinstance(main_chart_data, dict):
                    # Convertir a figura de Plotly
                    fig = go.Figure(main_chart_data)
                    print("Debug - Figura de Plotly creada exitosamente")
                    
                    # Configurar la figura para mejor renderizado
                    fig.update_layout(
                        width=600,
                        height=400,
                        font=dict(size=12),
                        showlegend=True
                    )
                    
                    print("Debug - Convirtiendo figura a imagen...")
                    # Convertir a imagen con kaleido
                    img_bytes = pio.to_image(
                        fig, 
                        format="png", 
                        width=600, 
                        height=400, 
                        scale=2,
                        engine="kaleido"
                    )
                    print(f"Debug - Imagen generada, tamaño: {len(img_bytes)} bytes")
                    
                    if len(img_bytes) > 0:
                        img = Image(io.BytesIO(img_bytes), width=6*inch, height=4*inch)
                        story.append(img)
                        print("Debug - Imagen agregada al PDF exitosamente")
                    else:
                        raise Exception("Imagen generada está vacía")
                else:
                    raise Exception(f"main_chart_data no es un dict válido: {type(main_chart_data)}")
                
                # Explicación
                explanation = """Este gráfico muestra la comparación directa entre el presupuesto planificado 
                y los gastos ejecutados por categoría. Las barras azules representan el presupuesto asignado, 
                mientras que las barras azul claro muestran los gastos reales."""
                
                story.append(Paragraph("<b>Análisis:</b>", styles['Normal']))
                story.append(Paragraph(explanation, styles['Normal']))
                story.append(Spacer(1, 20))
                
            except Exception as e:
                print(f"Error procesando gráfico principal: {e}")
                import traceback
                traceback.print_exc()
                
                error_msg = f"Error: No se pudo generar el gráfico principal. Detalle: {str(e)}"
                story.append(Paragraph(error_msg, styles['Normal']))
                story.append(Spacer(1, 20))
        else:
            print("Debug - No hay datos de gráfico principal disponibles")
            story.append(Paragraph("No hay datos de gráfico disponibles para este período.", styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Tabla de datos
        table_data = pdf_data.get('tables', {}).get('main_table', [])
        if table_data and len(table_data) > 0:
            try:
                story.append(Paragraph("📋 Detalle por Categorías", styles['CustomSubtitle']))
                
                # Preparar datos para tabla
                if len(table_data) > 0:
                    # Headers
                    first_row = table_data[0]
                    headers = list(first_row.keys())
                    
                    # Datos
                    table_rows = [headers]
                    for row in table_data:
                        table_rows.append([str(row.get(header, '')) for header in headers])
                    
                    # Crear tabla
                    table = Table(table_rows, repeatRows=1)
                    table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#094782')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, 0), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                        ('FONTSIZE', (0, 1), (-1, -1), 9),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    
                    story.append(table)
                    story.append(Spacer(1, 20))
                    
            except Exception as e:
                print(f"Error procesando tabla: {e}")
                story.append(Paragraph("Error: No se pudo generar la tabla de datos.", styles['Normal']))
                story.append(Spacer(1, 20))
        

        
        # Conclusiones
        story.append(Paragraph("📝 Conclusiones", styles['CustomSubtitle']))
        
        if summary:
            variacion = summary.get('variacion_porcentual', 0)
            if variacion > 10:
                conclusion = "Se observa una sobreejecución significativa del presupuesto."
            elif variacion > 5:
                conclusion = "Se observa una ligera sobreejecución del presupuesto."
            elif variacion < -10:
                conclusion = "Se observa una subejecución significativa del presupuesto."
            elif variacion < -5:
                conclusion = "Se observa una ligera subejecución del presupuesto."
            else:
                conclusion = "La ejecución se mantiene dentro de parámetros normales."
        else:
            conclusion = "No hay datos suficientes para generar conclusiones."
        
        story.append(Paragraph(conclusion, styles['Normal']))
        story.append(Spacer(1, 30))
        
        # Footer
        footer_text = f"Reporte generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}."
        story.append(Paragraph(footer_text, styles['Normal']))
        
        # Construir PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
        
    except Exception as e:
        print(f"Error en generate_simple_pdf_report: {e}")
        import traceback
        traceback.print_exc()
        
        # Crear PDF de error básico
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("Error al generar reporte", styles['Title']),
            Paragraph(f"Se produjo un error: {str(e)}", styles['Normal'])
        ]
        doc.build(story)
        buffer.seek(0)
        return buffer

# Callbacks para el modal del gráfico expandido
@callback(
    Output(f"{PAGE_ID}chart-modal", "opened"),
    Output(f"{PAGE_ID}chart-loading-overlay", "visible"),
    Input(f"{PAGE_ID}expand-chart-btn", "n_clicks"),
    Input(f"{PAGE_ID}close-chart-modal-btn", "n_clicks"),
    State(f"{PAGE_ID}chart-modal", "opened"),
    prevent_initial_call=True
)
def toggle_chart_modal(expand_clicks, close_clicks, modal_opened):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, False
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    if trigger_id == f"{PAGE_ID}expand-chart-btn" and expand_clicks:
        return True, True  # Abrir modal y mostrar loading
    elif trigger_id == f"{PAGE_ID}close-chart-modal-btn" and close_clicks:
        return False, False  # Cerrar modal
    
    return modal_opened, False

# Callback para actualizar el contenido del gráfico expandido
@callback(
    Output(f"{PAGE_ID}expanded-chart", "figure"),
    Output(f"{PAGE_ID}total-presupuesto", "children"),
    Output(f"{PAGE_ID}total-ejecutado", "children"),
    Output(f"{PAGE_ID}variacion", "children"),
    Output(f"{PAGE_ID}num-categorias", "children"),
    Output(f"{PAGE_ID}chart-loading-overlay", "visible", allow_duplicate=True),
    Input(f"{PAGE_ID}chart-modal", "opened"),
    State(f"{PAGE_ID}filtered-data-store", "data"),
    State(f"{PAGE_ID}segmented-bar-comparativo", "value"),
    prevent_initial_call=True
)
def update_expanded_chart_content(modal_opened, filtered_data, segmented_bar_comparativo):
    if not modal_opened or not filtered_data:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, False
    
    try:
        # Obtener datos
        df = pd.DataFrame(filtered_data.get("Presupuesto Packing", []))
        df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
        
        if len(df) == 0 or len(df_ma) == 0:
            return {}, "$0.00", "$0.00", "0.0%", "0", False
        
        # Procesar datos igual que en el callback principal
        presupuesto_group = df.groupby(["Año", "Mes", "ITEM_CORREGIDO", "MES"])[["IMPORTE"]].sum().reset_index()
        presupuesto_group = presupuesto_group.rename(columns={"ITEM_CORREGIDO": "Descripción Proyecto", "IMPORTE": "IMPORTE PRESUPUESTO"})
        mayor_analitico_group = df_ma.groupby(["Año", "Mes", "Descripción Proyecto", "AGRUPADOR"])[["Dólares Cargo"]].sum().reset_index()
        mayor_analitico_group = mayor_analitico_group.rename(columns={"Dólares Cargo": "IMPORTE MAYOR ANALITICO"})
        
        comparativo_ejec_presupuesto = pd.merge(
            presupuesto_group, 
            mayor_analitico_group, 
            on=["Año", "Mes", "Descripción Proyecto"], 
            how="left"
        )
        
        # Crear datos para gráfico expandido
        df_grafico = comparativo_ejec_presupuesto.groupby([segmented_bar_comparativo])[["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"]].sum().reset_index()
        
        if segmented_bar_comparativo == "Mes":
            df_grafico = df_grafico[df_grafico["IMPORTE MAYOR ANALITICO"] > 0]
        
        # Calcular estadísticas
        total_presupuesto = df_grafico["IMPORTE PRESUPUESTO"].sum()
        total_ejecutado = df_grafico["IMPORTE MAYOR ANALITICO"].sum()
        variacion_porcentual = ((total_ejecutado - total_presupuesto) / total_presupuesto * 100) if total_presupuesto > 0 else 0
        num_categorias = len(df_grafico)
        
        # Crear gráfico expandido con mejor diseño
        fig = px.bar(
            df_grafico, 
            x=segmented_bar_comparativo, 
            y=["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"], 
            title=f"Comparativo PPTO vs Ejecutado - Vista Detallada por {segmented_bar_comparativo}",
            template="plotly_white",
            barmode="group",
            height=600,
            color_discrete_map={
                "IMPORTE PRESUPUESTO": "#094782",
                "IMPORTE MAYOR ANALITICO": "#0b72d7"
            }
        )
        
        # Personalizar gráfico expandido
        fig.update_layout(
            margin=dict(t=80, b=60, l=80, r=40),
            xaxis_title=f"{segmented_bar_comparativo}",
            yaxis_title="Importe ($)",
            legend_title="",
            title=dict(
                text=f"Comparativo PPTO vs Ejecutado - Vista Detallada por {segmented_bar_comparativo}",
                font=dict(size=20, color="black", weight="bold"),
                x=0.5
            ),
            font=dict(size=14, color="black"),
            hoverlabel=dict(
                bgcolor="rgba(255, 255, 255, 0.95)",
                font_size=14,
                font_family="Arial, sans-serif",
                font_color="black"
            ),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)"
        )
        
        # Configurar ejes
        fig.update_yaxes(
            tickformat=",",
            tickmode="auto",
            nticks=15,
            title_font=dict(size=16, weight="bold"),
            tickfont=dict(size=12),
            gridcolor="rgba(128,128,128,0.2)"
        )
        
        fig.update_xaxes(
            title_font=dict(size=16, weight="bold"),
            tickfont=dict(size=12),
            tickangle=45 if len(df_grafico) > 5 else 0
        )
        
        # Configurar leyenda
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=14, weight="bold")
        ))
        
        # Agregar etiquetas de datos
        fig.update_traces(
            texttemplate='$%{y:,.0f}',
            textposition='outside',
            textfont=dict(size=11, color="black"),
            hovertemplate='<b>%{fullData.name}</b><br>' +
                         f'{segmented_bar_comparativo}: %{{x}}<br>' +
                         'Importe: $%{y:,.2f}<br>' +
                         '<extra></extra>'
        )
        
        # Actualizar nombres de la leyenda
        fig.data[0].name = "Presupuesto"
        fig.data[1].name = "Ejecutado"
        
        # Formatear estadísticas
        total_ppto_formatted = f"${total_presupuesto:,.2f}"
        total_ejec_formatted = f"${total_ejecutado:,.2f}"
        variacion_formatted = f"{variacion_porcentual:+.1f}%"
        
        return fig, total_ppto_formatted, total_ejec_formatted, variacion_formatted, str(num_categorias), False
        
    except Exception as e:
        print(f"Error en gráfico expandido: {e}")
        import traceback
        traceback.print_exc()
        return {}, "$0.00", "$0.00", "0.0%", "0", False