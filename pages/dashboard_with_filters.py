"""
Dashboard con Filtros Dependientes - Ejemplo usando generate_list_month
Los filtros se actualizan automáticamente entre sí (año → mes → semana)
"""
import dash
import dash_mantine_components as dmc
from dash import html
from components.grid import Row, Column
from components.simple_components import (
    create_page_header,
    create_data_stores,
    create_filters_row,
    create_metrics_row,
    create_charts_grid,
    register_dependent_filters_callbacks
)
from constants import PAGE_TITLE_PREFIX

# Registrar página
dash.register_page(__name__, "/dashboard-filtros", title=PAGE_TITLE_PREFIX + "Dashboard con Filtros")

# ============================================================
# CONFIGURACIÓN DEL DASHBOARD
# ============================================================

PAGE_ID = "dashboard-filtros"
DATA_SOURCE = "ocupacion_transporte"

# Configuración específica para filtros dependientes
START_YEAR = 2024  # Año desde cuando generar opciones
START_MONTH = 1    # Mes desde cuando generar opciones

# Configuración de filtros (serán dependientes automáticamente)
FILTERS_CONFIG = [
    {
        'name': 'year', 
        'label': 'Año', 
        'type': 'select', 
        'placeholder': 'Seleccione Año',
        'clearable': False,
        'size': 3
    },
    {
        'name': 'month', 
        'label': 'Mes', 
        'type': 'select', 
        'placeholder': 'Seleccione Mes',
        'clearable': True,
        'size': 3
    },
    {
        'name': 'week', 
        'label': 'Semanas', 
        'type': 'multiselect', 
        'placeholder': 'Seleccione Semanas',
        'clearable': True,
        'size': 6
    }
]

# Configuración de métricas
METRICS_CONFIG = [
    {
        'name': 'total_asientos',
        'label': 'Total Asientos Ocupados',
        'type': 'sum',
        'column': 'N° ASIENTOS OCUPADOS',
        'size': 4
    },
    {
        'name': 'total_registros',
        'label': 'Total Registros',
        'type': 'count',
        'size': 4
    },
    {
        'name': 'promedio_ocupacion',
        'label': 'Promedio Ocupación',
        'type': 'avg',
        'column': 'N° ASIENTOS OCUPADOS',
        'size': 4
    }
]

# Configuración de gráficos
CHARTS_CONFIG = [
    {
        'name': 'ocupacion_temporal',
        'title': 'Ocupación por Período',
        'type': 'bar',
        'x': 'SEMANA',
        'y': 'N° ASIENTOS OCUPADOS',
        'height': 400,
        'size': 12
    },
    {
        'name': 'ocupacion_por_ruta',
        'title': 'Ocupación por Ruta',
        'type': 'bar',
        'x': 'RUTA',
        'y': 'N° ASIENTOS OCUPADOS',
        'height': 400,
        'size': 6
    },
    {
        'name': 'distribucion_rutas',
        'title': 'Distribución por Rutas',
        'type': 'pie',
        'names': 'RUTA',
        'values': 'N° ASIENTOS OCUPADOS',
        'height': 400,
        'size': 6
    }
]

# ============================================================
# LAYOUT DEL DASHBOARD
# ============================================================

def create_layout():
    """Crea el layout del dashboard con filtros dependientes"""
    
    return html.Div([
        # 🗃️ Stores para datos (incluye store para fechas)
        html.Div(create_data_stores(PAGE_ID, [DATA_SOURCE], include_dates_store=True)),
        
        # 📊 Header de la página
        create_page_header(
            title="🔗 DASHBOARD CON FILTROS DEPENDIENTES",
            subtitle="Los filtros se actualizan automáticamente usando generate_list_month"
        ),
        
        # ℹ️ Información sobre el funcionamiento
        dmc.Alert(
            children=[
                dmc.Text("🎯 Funcionamiento de los filtros:", fw=500, mb="xs"),
                html.Ul([
                    html.Li("Al seleccionar un AÑO, se actualizan automáticamente los MESES disponibles"),
                    html.Li("Al seleccionar un MES, se actualizan automáticamente las SEMANAS disponibles"),
                    html.Li("Los datos se generan usando la función generate_list_month de forma asíncrona"),
                    html.Li("Todo el proceso es async para no bloquear la interfaz")
                ])
            ],
            title="💡 Cómo Funciona",
            color="blue",
            variant="light",
            mb="lg"
        ),
        
        # 🔍 Filtros Dependientes
        dmc.Paper([
            dmc.Group([
                dmc.Text("🔗 Filtros Dependientes", size="lg", fw=500),
                dmc.Badge("Async", color="green", variant="light")
            ], justify="space-between", mb="md"),
            
            create_filters_row(PAGE_ID, FILTERS_CONFIG),
            
            # Información adicional sobre filtros
            dmc.Text(
                "💡 Los filtros se cargan de forma inteligente: primero todos los años disponibles, luego los meses del año seleccionado, y finalmente las semanas del mes seleccionado.",
                size="sm",
                c="dimmed",
                mt="sm"
            )
        ], p="md", mb="lg", withBorder=True, shadow="sm"),
        
        # 📈 Métricas
        dmc.Paper([
            dmc.Text("📊 Métricas Dinámicas", size="lg", fw=500, mb="md"),
            create_metrics_row(PAGE_ID, METRICS_CONFIG)
        ], p="md", mb="lg", withBorder=True, shadow="sm"),
        
        # 📊 Gráficos
        dmc.Paper([
            dmc.Text("📈 Análisis Visual", size="lg", fw=500, mb="md"),
            html.Div(create_charts_grid(PAGE_ID, CHARTS_CONFIG))
        ], p="md", mb="lg", withBorder=True, shadow="sm"),
        
        # 🔧 Información técnica
        dmc.Accordion([
            dmc.AccordionItem([
                dmc.AccordionControl("🔧 Detalles Técnicos"),
                dmc.AccordionPanel([
                    dmc.List([
                        dmc.ListItem([
                            dmc.Text("Data Manager: ", fw=500, span=True),
                            dmc.Text("Carga datos de Microsoft Graph API de forma asíncrona")
                        ]),
                        dmc.ListItem([
                            dmc.Text("Callback Manager: ", fw=500, span=True),
                            dmc.Text("Registra callbacks con IDs únicos para evitar conflictos")
                        ]),
                        dmc.ListItem([
                            dmc.Text("Generate List Month: ", fw=500, span=True),
                            dmc.Text(f"Genera opciones desde {START_YEAR}/{START_MONTH:02d} hasta hoy")
                        ]),
                        dmc.ListItem([
                            dmc.Text("Filtros Dependientes: ", fw=500, span=True),
                            dmc.Text("Año → Mes → Semana con actualización automática")
                        ])
                    ])
                ])
            ], value="tech")
        ], variant="separated", mb="lg")
    ])

# Crear layout
layout = create_layout()

# ============================================================
# REGISTRAR CALLBACKS CON FILTROS DEPENDIENTES
# ============================================================

# Usar la función especializada para filtros dependientes
register_dependent_filters_callbacks(
    page_id=PAGE_ID,
    data_source=DATA_SOURCE,
    charts_config=CHARTS_CONFIG,
    metrics_config=METRICS_CONFIG,
    start_year=START_YEAR,
    start_month=START_MONTH
)