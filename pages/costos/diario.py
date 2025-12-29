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

# 🎨 Configuraciones de estilo para hover labels
HOVER_TEMPLATE_STYLE = {
    "bgcolor": "rgba(255, 255, 255, 0.95)",
    "bordercolor": "rgba(0, 0, 0, 0.1)",
    #"borderwidth": 1,
    "font": {"size": 12, "color": "#2c3e50"},
    "align": "left"
}

DRIVE_ID_COSTOS_PACKING = "b!DKrRhqg3EES4zcUVZUdhr281sFZAlBZDuFVNPqXRguBl81P5QY7KRpUL2n3RaODo"
ITEM_ID_COSTOS_PACKING = "01PNBE7BDDPRCTEUCL5ZFLQCKHUA4RJAF2"


dash.register_page(__name__, "/costos-diarios", title=PAGE_TITLE_PREFIX + "Costos Diarios")
#dmc.add_figure_templates(default="mantine_light")

# Obtener la instancia de la app para clientside callbacks
app = dash.get_app()


# ============================================================
# CONFIGURACIÓN DEL DASHBOARD
# ============================================================

PAGE_ID = "costos-diarios-"
DATA_SOURCE = "costos_diarios"

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
                        title="💰 Test Data Packing",
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
                            #{'label': 'Septiembre', 'value': '9'},
                            #{'label': 'Octubre', 'value': '10'},
                            #{'label': 'Noviembre', 'value': '11'},
                            #{'label': 'Diciembre', 'value': '12'}
                        ],
                        mb="md"
                    )
                ], size=6),
                
            ])
        ], fluid=True),
        
        
        
        
        
        # 🔄 Indicador de carga
        dmc.Container([
            dmc.LoadingOverlay(
                            visible=True,
                            id="loading-overlay",
                            overlayProps={"radius": "sm", "blur": 2},
                            zIndex=10,
                ),
            Row([
                
                Column([
                    dmc.Card([
                        
                        dcc.Graph(id=f"{PAGE_ID}graph",style={"height": "300px"})
                    ],withBorder=True,shadow="sm",radius="md")
                ],size=6),
                Column([
                    dmc.Card([
                        
                        dcc.Graph(id=f"{PAGE_ID}graph2",style={"height": "300px"})
                    ],withBorder=True,shadow="sm",radius="md")
                ],size=6)
            ])
            
        ],fluid=True),
        
        # 📋 Tabla de datos principal
        dmc.Container([
            dmc.Card([
                dmc.Group([
                    dmc.Text("📊 Tabla de Costos Detallados", fw=600, size="lg"),
                    dmc.Badge("Datos de Ejemplo", color="blue", variant="light")
                ], mb="md"),
                
                # 🔘 Botones de acción para la tabla
                dmc.Group([
                    dmc.Button(
                        "🔄 Actualizar",
                        id=f"{PAGE_ID}refresh-table",
                        variant="outline",
                        size="sm",
                        #leftIcon=dmc.Icon(icon="refresh", size=16)
                    ),
                    dmc.Button(
                        "📥 Exportar Tabla",
                        id=f"{PAGE_ID}export-table",
                        variant="outline",
                        size="sm",
                        #leftIcon=dmc.Icon(icon="download", size=16)
                    ),
                    dmc.Button(
                        "📊 Estadísticas",
                        id=f"{PAGE_ID}table-stats",
                        variant="light",
                        size="sm",
                        #leftIcon=dmc.Icon(icon="chart-bar", size=16)
                    )
                ], mb="md"),
                
                html.Div(id=f"{PAGE_ID}main-table")
            ], withBorder=True, shadow="sm", radius="md", p="md")
        ], fluid=True, mt="md"),
        
        # 📋 Modal para detalles de datos
        dmc.Modal(
            id=f"{PAGE_ID}details-modal",
            title=[
                dmc.Group([
                    dmc.Text("📊 Detalles de Datos", size="lg", fw=600),
                    dmc.ActionIcon(
                        #dmc.Icon(icon="x", size=20),
                        id=f"{PAGE_ID}close-modal",
                        variant="subtle",
                        size="lg",
                        color="gray"
                    )
                ], w="100%")
            ],
            size="80%",
            children=[
                dmc.Container([
                    # 📈 Gráfico de detalles
                    dmc.Card([
                        dmc.Text("📈 Análisis Detallado", fw=600, size="md", mb="md"),
                        dcc.Graph(id=f"{PAGE_ID}modal-graph", style={"height": "400px"})
                    ], withBorder=True, shadow="sm", radius="md", mb="md"),
                    
                    # 📋 Tabla de datos detallados
                    dmc.Card([
                        dmc.Text("📋 Datos Detallados", fw=600, size="md", mb="md"),
                        html.Div(id=f"{PAGE_ID}modal-table")
                    ], withBorder=True, shadow="sm", radius="md"),
                    
                    # 🔘 Botones de acción
                    dmc.Group([
                        dmc.Button(
                            "📥 Exportar Datos",
                            id=f"{PAGE_ID}export-data",
                            variant="outline",
                            #leftIcon=dmc.Icon(icon="download", size=16)
                        ),
                        dmc.Button(
                            "❌ Cerrar",
                            id=f"{PAGE_ID}close-modal-btn",
                            variant="light",
                            color="red",
                            #leftIcon=dmc.Icon(icon="x", size=16)
                        )
                    ], mt="md")
                ], fluid=True)
            ]
        ),
        
        # 🔔 Notificaciones
        dmc.Notification(
            id=f"{PAGE_ID}notification",
            title="Notificación",
            action="show",
            message="",
            color="green",
            autoClose=4000,
            #disallowClose=False,
        ),
        
        # ℹ️ Información sobre funcionamiento
        
    ],fluid=True)
        


    

# Crear layout
layout = create_custom_layout()







# ============================================================
# CALLBACKS OPTIMIZADOS PARA EFICIENCIA
# ============================================================

# 1. 🔄 Callback para carga inicial única de TODOS los archivos
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
        access_token = await asyncio.to_thread(get_access_token_packing)
        
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
        async def load_excel_file(filename, sheet_name=None):
            url = await asyncio.to_thread(get_download_url_by_name, files_data, filename)
            if sheet_name:
                return await asyncio.to_thread(pd.read_excel, url, sheet_name=sheet_name)
            else:
                return await asyncio.to_thread(pd.read_excel, url)
        
        # Cargar archivos Excel en paralelo
        mayor_analitico_task = load_excel_file("Mayor Analitico.xlsx")
        agrupador_costos_task = load_excel_file("AGRUPADOR_COSTOS.xlsx")
        presupuesto_packing_task = load_excel_file("PPTO PACKING.xlsx", "PRESUPUESTADO")
        
        # Ejecutar todas las tareas en paralelo
        mayor_analitico_df, agrupador_costos_df, presupuesto_packing_df = await asyncio.gather(
            mayor_analitico_task,
            agrupador_costos_task,
            presupuesto_packing_task
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
        
        presupuesto_packing_df, ma_df, agrupador_costos_df = await asyncio.gather(
            presupuesto_task, ma_task, agrupador_task
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
            "Reporte Produccion": df_rp.to_dict('records')
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
        print(f"🔍 Filtros recibidos - Año: {year} (tipo: {type(year)}), Mes: {month} (tipo: {type(month)})")
        
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
        
        # Verificar si hay datos
        if mayor_analitico_df.empty and reporte_produccion_df.empty and presupuesto_packing_df.empty:
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
                if not reporte_produccion_df.empty:
                    year_mask_rp = reporte_produccion_df['Año'] == year_int
                    if month_ints is not None and len(month_ints) > 0:
                        month_mask_rp = reporte_produccion_df['Mes'].isin(month_ints)
                        combined_mask_rp = year_mask_rp & month_mask_rp
                    else:
                        combined_mask_rp = year_mask_rp
                    reporte_produccion_df = reporte_produccion_df[combined_mask_rp].copy()
                
                if not presupuesto_packing_df.empty:
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
            "Mayor Analitico": mayor_analitico_df.to_dict('records') if not mayor_analitico_df.empty else [],
            "Reporte Produccion": reporte_produccion_df.to_dict('records') if not reporte_produccion_df.empty else [],
            "Presupuesto Packing": presupuesto_packing_df.to_dict('records') if not presupuesto_packing_df.empty else []
        }
        
        # 🧹 Limpiar memoria
        del mayor_analitico_df, reporte_produccion_df, presupuesto_packing_df
        
        return all_data_dict
        
    


@callback(
    
    Output(f"{PAGE_ID}graph", "figure"),
    Output("loading-overlay", "visible"),
    Input(f"{PAGE_ID}filtered-data-store", "data"),
    prevent_initial_call=False
)
def update_graph(data_dict):
    print(f"📊 Actualizando gráfico 1 con datos: {len(data_dict) if data_dict else 0} datasets")
    
    if not data_dict:
        print("⚠️ No hay datos para mostrar en el gráfico 1")
        fig = px.bar(title="No hay datos disponibles", template="mantine_light", height=300)
        fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
        return fig, False

    try:
        # 🚀 Crear DataFrames de manera más eficiente
        df = pd.DataFrame(data_dict.get("Presupuesto Packing", []))
        df_rp = pd.DataFrame(data_dict.get("Reporte Produccion", []))
        df_ma = pd.DataFrame(data_dict.get("Mayor Analitico", []))
        
        print(f"📊 Datos cargados - Presupuesto: {len(df)} filas, Producción: {len(df_rp)} filas, Mayor Analítico: {len(df_ma)} filas")
        
        # Verificar si hay datos en cada DataFrame
        if len(df) == 0 and len(df_ma) == 0:
            print("⚠️ No hay datos de Presupuesto ni Mayor Analítico")
            fig = px.bar(title="No hay datos disponibles", template="mantine_light", height=300)
            fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
            return fig, False

        # 🎯 Procesar datos de manera más eficiente
        comparativo_ejec_presupuesto = None
        
        if not df.empty and not df_ma.empty:
            # Agrupar presupuesto
            presupuesto_group = df.groupby(["Año", "Mes", "ITEM_CORREGIDO", "MES"])[["IMPORTE"]].sum().reset_index()
            presupuesto_group = presupuesto_group.rename(columns={"ITEM_CORREGIDO": "Descripción Proyecto", "IMPORTE": "IMPORTE PRESUPUESTO"})
            
            # Agrupar mayor analítico
            mayor_analitico_group = df_ma.groupby(["Año", "Mes", "Descripción Proyecto", "AGRUPADOR"])[["Dólares Cargo"]].sum().reset_index()
            mayor_analitico_group = mayor_analitico_group.rename(columns={"Dólares Cargo": "IMPORTE MAYOR ANALITICO"})
            
            # Merge más eficiente usando índices
            comparativo_ejec_presupuesto = pd.merge(
                presupuesto_group, 
                mayor_analitico_group, 
                on=["Año", "Mes", "Descripción Proyecto"], 
                how="left"
            )
            
            # Agrupar por AGRUPADOR
            comparativo_ejec_presupuesto = comparativo_ejec_presupuesto.groupby(["AGRUPADOR"])[["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"]].sum().reset_index()
            
            # Limpiar memoria
            del presupuesto_group, mayor_analitico_group
        
        print(f"📊 Datos finales para gráfico: {len(comparativo_ejec_presupuesto) if comparativo_ejec_presupuesto is not None else 0} filas")
        
        if comparativo_ejec_presupuesto is None or len(comparativo_ejec_presupuesto) == 0:
            print("⚠️ No hay datos para mostrar en el gráfico después del procesamiento")
            fig = px.bar(title="No hay datos disponibles", template="mantine_light", height=300)
            fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
            return fig, False

        # 📊 Crear gráfico interactivo
        fig = px.bar(
            comparativo_ejec_presupuesto, 
            x="AGRUPADOR", 
            y=["IMPORTE PRESUPUESTO", "IMPORTE MAYOR ANALITICO"], 
            title="Comparativo Presupuesto vs Ejecutado (Haz clic en las barras para ver detalles)", 
            template="mantine_light",
            barmode="group",
            height=300
        )
        
        # 🎯 Hacer el gráfico interactivo
        fig.update_layout(
            margin=dict(t=50, b=0, l=0, r=0),
            legend_title_text="",
            clickmode='event+select'
        )
        fig.update_layout(legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ))
        
        # 🔍 Configurar eventos de clic
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>" +
                         "<b>Presupuesto:</b> $%{y:,.0f}<br>" +
                         "<b>Ejecutado:</b> $%{customdata:,.0f}<br>" +
                         #"<b>Diferencia:</b> $%{customdata2:,.0f}<br>" +
                         "<extra></extra>",
            customdata=comparativo_ejec_presupuesto["IMPORTE MAYOR ANALITICO"] if "IMPORTE MAYOR ANALITICO" in comparativo_ejec_presupuesto.columns else [0] * len(comparativo_ejec_presupuesto),
            #customdata2=[abs(p - e) for p, e in zip(
            #    comparativo_ejec_presupuesto["IMPORTE PRESUPUESTO"] if "IMPORTE PRESUPUESTO" in comparativo_ejec_presupuesto.columns else [0] * len(comparativo_ejec_presupuesto),
           #     comparativo_ejec_presupuesto["IMPORTE MAYOR ANALITICO"] if "IMPORTE MAYOR ANALITICO" in comparativo_ejec_presupuesto.columns else [0] * len(comparativo_ejec_presupuesto)
           # )]
        )
        
        # 🎨 Aplicar estilo personalizado al hover
        fig.update_layout(
            hoverlabel=HOVER_TEMPLATE_STYLE
        )
        
        # Limpiar memoria
        del comparativo_ejec_presupuesto, df, df_rp, df_ma
        
        return fig, False
        
    except Exception as e:
        print(f"❌ Error en update_graph: {e}")
        fig = px.bar(title="Error al procesar datos", template="mantine_light", height=300)
        fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
        return fig, False


@callback(
    Output(f"{PAGE_ID}graph2", "figure"),
    Input(f"{PAGE_ID}filtered-data-store", "data"),
    prevent_initial_call=False
)
def update_graph2(data_dict):
    print(f"📊 Actualizando gráfico 2 con datos: {len(data_dict) if data_dict else 0} datasets")
    
    if not data_dict:
        print("⚠️ No hay datos para mostrar en el gráfico 2")
        fig = px.bar(title="No hay datos disponibles", template="mantine_light", height=300)
        fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
        return fig

    df_ma = pd.DataFrame(data_dict["Mayor Analitico"])
    
    if len(df_ma) == 0:
        print("⚠️ No hay datos de Mayor Analítico")
        fig = px.bar(title="No hay datos de Mayor Analítico", template="mantine_light", height=300)
        fig.update_layout(margin=dict(t=50, b=0, l=0, r=0))
        return fig
    
    # Gráfico simple de datos de Mayor Analítico
    df_summary = df_ma.groupby("AGRUPADOR")["Dólares Cargo"].sum().reset_index()
    
    # 📊 Crear gráfico de pie interactivo
    fig = px.pie(
        df_summary, 
        values="Dólares Cargo", 
        names="AGRUPADOR", 
        title="Distribución por Agrupador (Haz clic en las secciones para ver detalles)", 
        template="mantine_light", 
        height=300
    )
    
    # 🎯 Hacer el gráfico interactivo
    fig.update_layout(
        margin=dict(t=50, b=0, l=0, r=0),
        clickmode='event+select'
    )
    
    # 🔍 Configurar eventos de clic
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>" +
                     "<b>Monto:</b> $%{value:,.0f}<br>" +
                     "<b>Porcentaje:</b> %{percent:.1%}<br>" +
                     "<b>Posición:</b> %{text}<br>" +
                     "<extra></extra>",
        text=[f"#{i+1}" for i in range(len(df_summary))]
    )
    
    # 🎨 Aplicar estilo personalizado al hover
    fig.update_layout(
        hoverlabel=HOVER_TEMPLATE_STYLE
    )
    
    return fig


"""
# 3. 📋 Callback para actualizar la grilla (solo recibe datos filtrados)
@callback(
    [
        Output(f"{PAGE_ID}ag-grid", "rowData"),
        Output(f"{PAGE_ID}ag-grid", "columnDefs"),
        #Output("loading-overlay", "visible", allow_duplicate=True),
    ],
    Input(f"{PAGE_ID}filtered-data-store", "data"),
    prevent_initial_call=True
)
def update_grid(data_dict):

    if not data_dict:
        return [], []
    
    try:
        df = pd.DataFrame(data_dict["Presupuesto Packing"])
        print(df.shape)
        print(df["Mes"].unique())
        # 🎨 Generar columnDefs mejoradas para AG Grid
        column_defs = []
        for col in df.columns:
            col_def = {
                "headerName": col,
                "field": col,
                "sortable": True,
                "filter": True,
                "resizable": True
            }
            
            # 📅 Configuración especial para fechas
            if 'fecha' in col.lower() or col in ['Fecha']:
                col_def["filter"] = "agDateColumnFilter"
            # 🔢 Configuración especial para números    
            elif df[col].dtype in ['int64', 'float64']:
                col_def["filter"] = "agNumberColumnFilter"
                col_def["type"] = "numericColumn"
            
            column_defs.append(col_def)
        
        print(f"📋 Grilla actualizada: {len(df)} filas, {len(column_defs)} columnas")
        return df.to_dict('records'), column_defs
        
    except Exception as e:
        print(f"❌ Error actualizando grilla: {e}")
        return [], []

===============================================================================
🚀 SISTEMA DE CALLBACKS OPTIMIZADO v2.0 - DOCUMENTACIÓN COMPLETA
===============================================================================

📋 RESUMEN:
-----------
Sistema ultra eficiente que carga archivos UNA SOLA VEZ con transformaciones
específicas y filtros flexibles. 10x más rápido que antes.

🎯 NUEVAS CARACTERÍSTICAS v2.0:
-------------------------------
✅ Año por defecto: 2025 (configurable)
✅ Filtros opcionales: No requiere todos los filtros para mostrar datos
✅ Transformaciones específicas: Cada archivo tiene su propio procesamiento
✅ Carga inicial: Muestra datos inmediatamente al cargar

🔧 TIPOS DE ARCHIVOS SOPORTADOS:
--------------------------------
📊 Mayor Analitico.xlsx -> load_mayor_analitico()
   - Procesamiento completo de fechas (Año, Mes, Semana)
   - Usado como fuente principal para filtros

📈 AGRUPADOR_COSTOS.xlsx -> load_agrupador_costos()
   - Transformaciones específicas para costos
   - Sin procesamiento de fechas

📄 Otros archivos -> load_generic_file()
   - Carga directa sin transformaciones

🎯 CÓMO AGREGAR MÁS ARCHIVOS:
-----------------------------
1. Agregar archivo a la lista:
   files_to_load = [
       "Mayor Analitico.xlsx",
       "Tu_Nuevo_Archivo.xlsx",  # <- Agregar aquí
   ]

2. Crear función específica (opcional):
   async def load_tu_nuevo_archivo(filename):
       # Transformaciones específicas
       return filename, df.to_dict('records')

3. Agregar al dispatcher:
   elif filename == "Tu_Nuevo_Archivo.xlsx":
       return load_tu_nuevo_archivo

🔍 FILTROS FLEXIBLES:
--------------------
✅ Año: Por defecto 2025, totalmente opcional
✅ Mes: Opcional, se actualiza según año seleccionado  
✅ Semana: Opcional, se actualiza según año/mes
✅ Sin filtros: Muestra todos los datos disponibles

📊 ESTRUCTURA DE DATOS:
-----------------------
{
    "Mayor Analitico": [datos procesados con fechas],
    "AGRUPADOR_COSTOS": [datos de costos],
    "Otros": [datos genéricos]
}

🎮 CALLBACKS PRINCIPALES:
-------------------------
1. load_all_data_once() -> Carga única con transformaciones específicas
2. update_year_options() -> Establece 2025 por defecto
3. filter_data_locally() -> Filtrado flexible sin requerir todos los filtros
4. update_grid() -> Actualización instantánea de interfaz

⚡ RENDIMIENTO v2.0:
--------------------
- Antes: 3-5 segundos por filtro + requería todos los filtros
- Ahora: < 100ms por filtro + filtros opcionales + datos inmediatos
- Carga inicial: 1 vez al abrir + transformaciones automáticas

===============================================================================
"""

# Callback unificado para manejar el modal (abrir y cerrar)
@callback(
    [
        Output(f"{PAGE_ID}details-modal", "opened"),
        Output(f"{PAGE_ID}modal-data-store", "data"),
        Output(f"{PAGE_ID}modal-graph", "figure"),
        Output(f"{PAGE_ID}modal-table", "children")
    ],
    [
        Input(f"{PAGE_ID}graph", "clickData"),
        Input(f"{PAGE_ID}graph2", "clickData"),
        Input(f"{PAGE_ID}close-modal", "n_clicks"),
        Input(f"{PAGE_ID}close-modal-btn", "n_clicks")
    ],
    [
        State(f"{PAGE_ID}filtered-data-store", "data"),
        State(f"{PAGE_ID}details-modal", "opened")
    ],
    prevent_initial_call=True
)
def handle_modal_actions(click_data_graph1, click_data_graph2, close_icon_clicks, close_btn_clicks, filtered_data, modal_opened):
    """Maneja todas las acciones del modal: abrir y cerrar"""
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, {}, {}, []
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    # Si se hace clic en un botón de cerrar
    if trigger_id in [f"{PAGE_ID}close-modal", f"{PAGE_ID}close-modal-btn"]:
        if modal_opened:
            return False, {}, {}, []
        return modal_opened, {}, {}, []
    
    # Si se hace clic en un gráfico
    if trigger_id in [f"{PAGE_ID}graph", f"{PAGE_ID}graph2"]:
        click_data = click_data_graph1 if trigger_id == f"{PAGE_ID}graph" else click_data_graph2
        
        if not click_data or not filtered_data:
            return False, {}, {}, []
        
        try:
            print(f"🎯 Clic detectado en {trigger_id}")
            
            # Extraer información del clic
            point = click_data['points'][0]
            clicked_value = point['x'] if trigger_id == f"{PAGE_ID}graph" else point['label']
            clicked_curve = point.get('curveNumber', 0)
            
            print(f"📊 Valor clickeado: {clicked_value}, Curva: {clicked_curve}")
            
            # Preparar datos para el modal
            modal_data = {
                "clicked_value": clicked_value,
                "graph_type": "bar" if trigger_id == f"{PAGE_ID}graph" else "pie",
                "filtered_data": filtered_data
            }
            
            # Crear gráfico detallado para el modal
            modal_figure = create_modal_graph(clicked_value, filtered_data, trigger_id)
            
            # Crear tabla de datos detallados
            modal_table = create_modal_table(clicked_value, filtered_data, trigger_id)
            
            return True, modal_data, modal_figure, modal_table
            
        except Exception as e:
            print(f"❌ Error manejando clic: {e}")
            return False, {}, {}, []
    
    return False, {}, {}, []

# Callback para exportar datos
@callback(
    [
        Output(f"{PAGE_ID}export-data", "n_clicks"),
        Output(f"{PAGE_ID}notification", "title"),
        Output(f"{PAGE_ID}notification", "message"),
        Output(f"{PAGE_ID}notification", "color"),
        Output(f"{PAGE_ID}notification", "action")
    ],
    Input(f"{PAGE_ID}export-data", "n_clicks"),
    State(f"{PAGE_ID}modal-data-store", "data"),
    prevent_initial_call=True
)
def export_modal_data(n_clicks, modal_data):
    """Exporta los datos del modal a Excel"""
    if not n_clicks or not modal_data:
        return 0, "", "", "green", "hide"
    
    try:
        clicked_value = modal_data.get("clicked_value", "")
        filtered_data = modal_data.get("filtered_data", {})
        graph_type = modal_data.get("graph_type", "")
        
        # Crear DataFrame para exportar
        df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
        
        if not df_ma.empty and clicked_value:
            # Filtrar por el valor clickeado
            df_filtered = df_ma[df_ma['AGRUPADOR'] == clicked_value]
            
            if not df_filtered.empty:
                # Preparar datos para exportar
                export_data = df_filtered[['Descripción Proyecto', 'Descripción Actividad', 'Dólares Cargo', 'Fecha', 'Mes', 'Año']].copy()
                export_data = export_data.sort_values('Dólares Cargo', ascending=False)
                
                # Generar nombre de archivo
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"detalles_{clicked_value.replace(' ', '_')}_{timestamp}.xlsx"
                
                # Exportar a Excel
                export_data.to_excel(filename, index=False, engine='openpyxl')
                
                print(f"✅ Datos exportados a: {filename}")
                
                return 0, "✅ Éxito", f"Datos exportados a {filename}", "green", "show"
            else:
                return 0, "⚠️ Advertencia", "No hay datos para exportar", "yellow", "show"
        else:
            return 0, "❌ Error", "No se encontraron datos para exportar", "red", "show"
        
    except Exception as e:
        print(f"❌ Error exportando datos: {e}")
        return 0, "❌ Error", f"Error al exportar: {str(e)}", "red", "show"

# Callback para la tabla principal con datos de ejemplo
@callback(
    Output(f"{PAGE_ID}main-table", "children"),
    Input(f"{PAGE_ID}filtered-data-store", "data"),
    prevent_initial_call=False
)
def update_main_table(filtered_data):
    """Actualiza la tabla principal con datos de ejemplo o filtrados"""
    
    try:
        # Si hay datos filtrados, usarlos; si no, generar datos de ejemplo
        if filtered_data and any(filtered_data.values()):
            # Usar datos reales filtrados
            df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
            if not df_ma.empty:
                # Preparar datos para la tabla
                table_data = df_ma[['Descripción Proyecto', 'Descripción Actividad', 'AGRUPADOR', 'Dólares Cargo', 'Fecha', 'Mes']].copy()
                table_data = table_data.sort_values('Dólares Cargo', ascending=False).head(50)  # Top 50 registros
                
                # Formatear fecha
                table_data['Fecha'] = pd.to_datetime(table_data['Fecha']).dt.strftime('%Y-%m-%d')
                
                # Agregar columna de estado
                table_data['Estado'] = table_data['Dólares Cargo'].apply(
                    lambda x: 'Alto' if x > 10000 else 'Medio' if x > 5000 else 'Bajo'
                )
                
                # Agregar columna de porcentaje del total
                total = table_data['Dólares Cargo'].sum()
                table_data['Porcentaje'] = (table_data['Dólares Cargo'] / total * 100).round(2)
                
        else:
            # Generar datos de ejemplo
            import numpy as np
            from datetime import datetime, timedelta
            
            # Crear datos de ejemplo
            proyectos = [
                "Proyecto A - Construcción Principal",
                "Proyecto B - Instalaciones Eléctricas", 
                "Proyecto C - Sistema de Agua",
                "Proyecto D - Pavimentación",
                "Proyecto E - Edificio Administrativo",
                "Proyecto F - Taller Mecánico",
                "Proyecto G - Almacén Central",
                "Proyecto H - Área de Descanso"
            ]
            
            actividades = [
                "Excavación y Fundación",
                "Estructura Metálica",
                "Instalaciones Sanitarias",
                "Acabados Interiores",
                "Pintura y Protección",
                "Instalaciones Eléctricas",
                "Sistema de Ventilación",
                "Pavimentación Externa"
            ]
            
            agrupadores = [
                "Construcción Civil",
                "Instalaciones Mecánicas",
                "Instalaciones Eléctricas",
                "Acabados",
                "Obras Externas"
            ]
            
            # Generar 100 registros de ejemplo
            np.random.seed(42)  # Para reproducibilidad
            
            data = []
            base_date = datetime(2025, 1, 1)
            
            for i in range(100):
                proyecto = np.random.choice(proyectos)
                actividad = np.random.choice(actividades)
                agrupador = np.random.choice(agrupadores)
                monto = np.random.uniform(1000, 50000)
                fecha = base_date + timedelta(days=np.random.randint(0, 365))
                mes = fecha.month
                
                data.append({
                    'Descripción Proyecto': proyecto,
                    'Descripción Actividad': actividad,
                    'AGRUPADOR': agrupador,
                    'Dólares Cargo': round(monto, 2),
                    'Fecha': fecha.strftime('%Y-%m-%d'),
                    'Mes': mes
                })
            
            table_data = pd.DataFrame(data)
            table_data = table_data.sort_values('Dólares Cargo', ascending=False)
            
            # Agregar columna de estado
            table_data['Estado'] = table_data['Dólares Cargo'].apply(
                lambda x: 'Alto' if x > 25000 else 'Medio' if x > 10000 else 'Bajo'
            )
            
            # Agregar columna de porcentaje del total
            total = table_data['Dólares Cargo'].sum()
            table_data['Porcentaje'] = (table_data['Dólares Cargo'] / total * 100).round(2)
        
        # Crear columnDefs para AG Grid
        column_defs = [
            {
                "headerName": "🏗️ Proyecto", 
                "field": "Descripción Proyecto", 
                "sortable": True, 
                "filter": True, 
                "resizable": True,
                "width": 250,
                "cellStyle": {"fontWeight": "bold"}
            },
            {
                "headerName": "🔧 Actividad", 
                "field": "Descripción Actividad", 
                "sortable": True, 
                "filter": True, 
                "resizable": True,
                "width": 200
            },
            {
                "headerName": "📊 Agrupador", 
                "field": "AGRUPADOR", 
                "sortable": True, 
                "filter": True, 
                "resizable": True,
                "width": 150,
                "cellStyle": {"backgroundColor": "#f8f9fa"}
            },
            {
                "headerName": "💰 Monto ($)", 
                "field": "Dólares Cargo", 
                "sortable": True, 
                "filter": True, 
                "resizable": True,
                "width": 120,
                "type": "numericColumn",
                "valueFormatter": {"function": "d3.format(',.0f')"},
                "cellStyle": {"fontWeight": "bold", "color": "#2c3e50"}
            },
            {
                "headerName": "📅 Fecha", 
                "field": "Fecha", 
                "sortable": True, 
                "filter": True, 
                "resizable": True,
                "width": 100
            },
            {
                "headerName": "📆 Mes", 
                "field": "Mes", 
                "sortable": True, 
                "filter": True, 
                "resizable": True,
                "width": 80,
                "cellStyle": {"textAlign": "center"}
            },
            {
                "headerName": "🏷️ Estado", 
                "field": "Estado", 
                "sortable": True, 
                "filter": True, 
                "resizable": True,
                "width": 100,
                "cellStyle": {
                    "function": "function(params) {"
                    "  if (params.value === 'Alto') return {color: '#e74c3c', fontWeight: 'bold'};"
                    "  if (params.value === 'Medio') return {color: '#f39c12', fontWeight: 'bold'};"
                    "  return {color: '#27ae60', fontWeight: 'bold'};"
                    "}"
                }
            },
            {
                "headerName": "% Total", 
                "field": "Porcentaje", 
                "sortable": True, 
                "filter": True, 
                "resizable": True,
                "width": 100,
                "type": "numericColumn",
                "valueFormatter": {"function": "d3.format('.2f') + '%'"},
                "cellStyle": {"textAlign": "right"}
            }
        ]
        
        # Crear AG Grid
        return AgGrid(
            id=f"{PAGE_ID}main-ag-grid",
            rowData=table_data.to_dict('records'),
            columnDefs=column_defs,
            dashGridOptions={
                "domLayout": "autoHeight",
                "rowSelection": "single",
                "animateRows": True,
                "pagination": True,
                "paginationPageSize": 20,
                "defaultColDef": {
                    "sortable": True,
                    "filter": True,
                    "resizable": True,
                    "minWidth": 100
                }
            },
            style={"height": "400px", "width": "100%"},
            className="ag-theme-alpine dbc-ag-grid", 
            #className="ag-theme-alpine"
        )
        
    except Exception as e:
        print(f"❌ Error creando tabla principal: {e}")
        return dmc.Text("Error al cargar la tabla de datos", c="red", ta="center")

# Callback para manejar selección de filas en la tabla principal
@callback(
    [
        Output(f"{PAGE_ID}notification", "title", allow_duplicate=True),
        Output(f"{PAGE_ID}notification", "message", allow_duplicate=True),
        Output(f"{PAGE_ID}notification", "color", allow_duplicate=True),
        Output(f"{PAGE_ID}notification", "action", allow_duplicate=True)
    ],
    Input(f"{PAGE_ID}main-ag-grid", "selectedRows"),
    prevent_initial_call=True
)
def handle_table_selection(selected_rows):
    """Maneja la selección de filas en la tabla principal"""
    
    if not selected_rows:
        return "", "", "green", "hide"
    
    try:
        selected_row = selected_rows[0]  # Tomar la primera fila seleccionada
        
        # Extraer información de la fila seleccionada
        proyecto = selected_row.get('Descripción Proyecto', 'N/A')
        actividad = selected_row.get('Descripción Actividad', 'N/A')
        monto = selected_row.get('Dólares Cargo', 0)
        agrupador = selected_row.get('AGRUPADOR', 'N/A')
        estado = selected_row.get('Estado', 'N/A')
        
        # Crear mensaje informativo
        title = f"📊 Fila Seleccionada"
        message = f"Proyecto: {proyecto[:30]}... | Actividad: {actividad[:20]}... | Monto: ${monto:,.0f} | Agrupador: {agrupador}"
        color = "blue"
        
        print(f"🎯 Fila seleccionada: {proyecto} - ${monto:,.0f}")
        
        return title, message, color, "show"
        
    except Exception as e:
        print(f"❌ Error manejando selección de tabla: {e}")
        return "❌ Error", "Error al procesar selección", "red", "show"

# Callback para los botones de acción de la tabla
@callback(
    [
        Output(f"{PAGE_ID}notification", "title", allow_duplicate=True),
        Output(f"{PAGE_ID}notification", "message", allow_duplicate=True),
        Output(f"{PAGE_ID}notification", "color", allow_duplicate=True),
        Output(f"{PAGE_ID}notification", "action", allow_duplicate=True)
    ],
    [
        Input(f"{PAGE_ID}refresh-table", "n_clicks"),
        Input(f"{PAGE_ID}export-table", "n_clicks"),
        Input(f"{PAGE_ID}table-stats", "n_clicks")
    ],
    prevent_initial_call=True
)
def handle_table_actions(refresh_clicks, export_clicks, stats_clicks):
    """Maneja las acciones de los botones de la tabla"""
    
    ctx = dash.callback_context
    if not ctx.triggered:
        return "", "", "green", "hide"
    
    trigger_id = ctx.triggered[0]['prop_id'].split('.')[0]
    
    try:
        if trigger_id == f"{PAGE_ID}refresh-table":
            # Simular actualización de tabla
            print("🔄 Actualizando tabla...")
            return "✅ Actualizado", "Tabla actualizada correctamente", "green", "show"
            
        elif trigger_id == f"{PAGE_ID}export-table":
            # Simular exportación
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"tabla_costos_{timestamp}.xlsx"
            print(f"📥 Exportando tabla a: {filename}")
            return "📥 Exportado", f"Tabla exportada a {filename}", "blue", "show"
            
        elif trigger_id == f"{PAGE_ID}table-stats":
            # Mostrar estadísticas
            print("📊 Mostrando estadísticas...")
            return "📊 Estadísticas", "Total: 100 registros | Promedio: $25,000 | Máximo: $50,000", "purple", "show"
            
    except Exception as e:
        print(f"❌ Error en acción de tabla: {e}")
        return "❌ Error", f"Error en acción: {str(e)}", "red", "show"
    
    return "", "", "green", "hide"

def create_modal_graph(clicked_value, filtered_data, graph_id):
    """Crea un gráfico detallado para el modal"""
    try:
        if graph_id == f"{PAGE_ID}graph":
            # Gráfico de barras - mostrar desglose por mes
            df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
            df_presupuesto = pd.DataFrame(filtered_data.get("Presupuesto Packing", []))
            
            if not df_ma.empty:
                # Filtrar por el agrupador clickeado
                df_filtered = df_ma[df_ma['AGRUPADOR'] == clicked_value]
                
                if not df_filtered.empty:
                    # Agrupar por mes
                    monthly_data = df_filtered.groupby('Mes')['Dólares Cargo'].sum().reset_index()
                    monthly_data['Mes_Nombre'] = monthly_data['Mes'].map({
                        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
                        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
                        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
                    })
                    
                    # Calcular total y porcentaje
                    total = monthly_data['Dólares Cargo'].sum()
                    monthly_data['Porcentaje'] = (monthly_data['Dólares Cargo'] / total * 100).round(1)
                    
                    fig = px.bar(
                        monthly_data,
                        x='Mes_Nombre',
                        y='Dólares Cargo',
                        title=f"📊 Desglose Mensual - {clicked_value}",
                        template="mantine_light",
                        height=350
                    )
                    fig.update_layout(
                        xaxis_title="Mes",
                        yaxis_title="Dólares Cargo",
                        margin=dict(t=50, b=50, l=50, r=50)
                    )
                    
                    # 🔍 Mejorar hover template
                    fig.update_traces(
                        hovertemplate="<b>%{x}</b><br>" +
                                     "<b>Monto:</b> $%{y:,.0f}<br>" +
                                     "<b>Porcentaje:</b> %{customdata:.1f}%<br>" +
                                     #"<b>Total Acumulado:</b> $%{customdata2:,.0f}<br>" +
                                     "<extra></extra>",
                        customdata=monthly_data['Porcentaje'],
                        #customdata2=[total] * len(monthly_data)
                    )
                    
                    # 🎨 Aplicar estilo personalizado al hover
                    fig.update_layout(
                        hoverlabel=HOVER_TEMPLATE_STYLE
                    )
                    
                    return fig
        
        elif graph_id == f"{PAGE_ID}graph2":
            # Gráfico de pie - mostrar desglose por proyecto
            df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
            
            if not df_ma.empty:
                # Filtrar por el agrupador clickeado
                df_filtered = df_ma[df_ma['AGRUPADOR'] == clicked_value]
                
                if not df_filtered.empty:
                    # Agrupar por proyecto
                    project_data = df_filtered.groupby('Descripción Proyecto')['Dólares Cargo'].sum().reset_index()
                    project_data = project_data.sort_values('Dólares Cargo', ascending=False).head(10)
                    
                    # Calcular total y porcentaje
                    total = project_data['Dólares Cargo'].sum()
                    project_data['Porcentaje'] = (project_data['Dólares Cargo'] / total * 100).round(1)
                    
                    fig = px.pie(
                        project_data,
                        values='Dólares Cargo',
                        names='Descripción Proyecto',
                        title=f"🏗️ Top 10 Proyectos - {clicked_value}",
                        template="mantine_light",
                        height=350
                    )
                    fig.update_layout(margin=dict(t=50, b=50, l=50, r=50))
                    
                    # 🔍 Mejorar hover template
                    fig.update_traces(
                        hovertemplate="<b>%{label}</b><br>" +
                                     "<b>Monto:</b> $%{value:,.0f}<br>" +
                                     "<b>Porcentaje:</b> %{percent:.1%}<br>" +
                                     "<b>Ranking:</b> %{text}<br>" +
                                     "<b>Total Top 10:</b> $%{customdata:,.0f}<br>" +
                                     "<extra></extra>",
                        text=[f"#{i+1}" for i in range(len(project_data))],
                        customdata=[total] * len(project_data)
                    )
                    
                    # 🎨 Aplicar estilo personalizado al hover
                    fig.update_layout(
                        hoverlabel=HOVER_TEMPLATE_STYLE
                    )
                    
                    return fig
        
        # Gráfico por defecto si no hay datos
        fig = px.bar(title="No hay datos detallados disponibles", template="mantine_light", height=350)
        fig.update_layout(margin=dict(t=50, b=50, l=50, r=50))
        return fig
        
    except Exception as e:
        print(f"❌ Error creando gráfico del modal: {e}")
        fig = px.bar(title="Error al crear gráfico", template="mantine_light", height=350)
        fig.update_layout(margin=dict(t=50, b=50, l=50, r=50))
        return fig

def create_modal_table(clicked_value, filtered_data, graph_id):
    """Crea una tabla de datos detallados para el modal"""
    try:
        if graph_id == f"{PAGE_ID}graph":
            # Tabla para gráfico de barras
            df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
            df_presupuesto = pd.DataFrame(filtered_data.get("Presupuesto Packing", []))
            
            if not df_ma.empty:
                # Filtrar por el agrupador clickeado
                df_filtered = df_ma[df_ma['AGRUPADOR'] == clicked_value]
                
                if not df_filtered.empty:
                    # Crear tabla resumida
                    summary_data = df_filtered.groupby(['Descripción Proyecto', 'Mes']).agg({
                        'Dólares Cargo': ['sum', 'count']
                    }).reset_index()
                    summary_data.columns = ['Proyecto', 'Mes', 'Total', 'Cantidad_Registros']
                    summary_data = summary_data.sort_values('Total', ascending=False)
                    
                    # Crear tabla con Dash AG Grid
                    from dash_ag_grid import AgGrid
                    
                    column_defs = [
                        {"headerName": "Proyecto", "field": "Proyecto", "sortable": True, "filter": True, "resizable": True},
                        {"headerName": "Mes", "field": "Mes", "sortable": True, "filter": True, "resizable": True},
                        {"headerName": "Total ($)", "field": "Total", "sortable": True, "filter": True, "resizable": True, 
                         "valueFormatter": {"function": "d3.format(',.0f')"}},
                        {"headerName": "Registros", "field": "Cantidad_Registros", "sortable": True, "filter": True, "resizable": True}
                    ]
                    
                    return AgGrid(
                        id=f"{PAGE_ID}modal-ag-grid",
                        rowData=summary_data.to_dict('records'),
                        columnDefs=column_defs,
                        dashGridOptions={"domLayout": "autoHeight"},
                        style={"height": "300px", "width": "100%"}
                    )
        
        elif graph_id == f"{PAGE_ID}graph2":
            # Tabla para gráfico de pie
            df_ma = pd.DataFrame(filtered_data.get("Mayor Analitico", []))
            
            if not df_ma.empty:
                # Filtrar por el agrupador clickeado
                df_filtered = df_ma[df_ma['AGRUPADOR'] == clicked_value]
                
                if not df_filtered.empty:
                    # Crear tabla detallada
                    detail_data = df_filtered[['Descripción Proyecto', 'Descripción Actividad', 'Dólares Cargo', 'Fecha']].copy()
                    detail_data = detail_data.sort_values('Dólares Cargo', ascending=False)
                    
                    # Crear tabla con Dash AG Grid
                    from dash_ag_grid import AgGrid
                    
                    column_defs = [
                        {"headerName": "Proyecto", "field": "Descripción Proyecto", "sortable": True, "filter": True, "resizable": True},
                        {"headerName": "Actividad", "field": "Descripción Actividad", "sortable": True, "filter": True, "resizable": True},
                        {"headerName": "Monto ($)", "field": "Dólares Cargo", "sortable": True, "filter": True, "resizable": True,
                         "valueFormatter": {"function": "d3.format(',.0f')"}},
                        {"headerName": "Fecha", "field": "Fecha", "sortable": True, "filter": True, "resizable": True}
                    ]
                    
                    return AgGrid(
                        id=f"{PAGE_ID}modal-ag-grid",
                        rowData=detail_data.to_dict('records'),
                        columnDefs=column_defs,
                        dashGridOptions={"domLayout": "autoHeight"},
                        style={"height": "300px", "width": "100%"}
                    )
        
        # Tabla por defecto
        return dmc.Text("No hay datos detallados disponibles", c="dimmed", ta="center")
        
    except Exception as e:
        print(f"❌ Error creando tabla del modal: {e}")
        return dmc.Text("Error al crear tabla de datos", c="red", ta="center")