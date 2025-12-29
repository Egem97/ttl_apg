"""
Dashboard de Ocupación de Transporte - Versión Simplificada
Layout directo y fácil de editar + callbacks async separados
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
    register_page_callbacks
)
from constants import PAGE_TITLE_PREFIX

# Registrar página
dash.register_page(__name__, "/dashboard-simple", title=PAGE_TITLE_PREFIX + "Dashboard Simple")

# ============================================================
# CONFIGURACIÓN DEL DASHBOARD (fácil de editar)
# ============================================================

PAGE_ID = "dashboard-simple"
DATA_SOURCE = "ocupacion_transporte"

# Configuración de filtros
FILTERS_CONFIG = [
    {
        'name': 'year', 
        'label': 'Año', 
        'type': 'select', 
        'placeholder': 'Seleccione Año',
        'size': 2
    },
    {
        'name': 'month', 
        'label': 'Mes', 
        'type': 'select', 
        'placeholder': 'Todos',
        'clearable': True,
        'size': 2
    },
    {
        'name': 'week', 
        'label': 'Semana', 
        'type': 'multiselect', 
        'clearable': True,
        'size': 3
    }
]

# Configuración de métricas
METRICS_CONFIG = [
    {
        'name': 'total_asientos',
        'label': 'Total Asientos Ocupados',
        'type': 'sum',
        'column': 'N° ASIENTOS OCUPADOS',
        'size': 3
    },
    {
        'name': 'total_registros',
        'label': 'Total Registros',
        'type': 'count',
        'size': 3
    },
    {
        'name': 'promedio_ocupacion',
        'label': 'Promedio Ocupación',
        'type': 'avg',
        'column': 'N° ASIENTOS OCUPADOS',
        'size': 3
    },
    {
        'name': 'max_ocupacion',
        'label': 'Máxima Ocupación',
        'type': 'max',
        'column': 'N° ASIENTOS OCUPADOS',
        'size': 3
    }
]

# Configuración de gráficos
CHARTS_CONFIG = [
    {
        'name': 'ocupacion_por_semana',
        'title': 'Ocupación por Semana',
        'type': 'bar',
        'x': 'SEMANA',
        'y': 'N° ASIENTOS OCUPADOS',
        'height': 400,
        'size': 6
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
        'name': 'distribucion_ocupacion',
        'title': 'Distribución de Ocupación',
        'type': 'pie',
        'names': 'RUTA',
        'values': 'N° ASIENTOS OCUPADOS',
        'height': 500,
        'size': 12
    }
]

# ============================================================
# LAYOUT DEL DASHBOARD (fácil de personalizar)
# ============================================================

def create_layout():
    """Crea el layout del dashboard de forma directa"""
    
    return html.Div([
        # 🗃️ Stores para datos (invisible)
        html.Div(create_data_stores(PAGE_ID, [DATA_SOURCE])),
        
        # 📊 Header de la página
        create_page_header(
            title="OCUPACIÓN DE TRANSPORTE",
            subtitle="Análisis de ocupación por período"
        ),
        
        # 🔍 Filtros
        dmc.Paper([
            dmc.Text("Filtros", size="lg", fw=500, mb="md"),
            create_filters_row(PAGE_ID, FILTERS_CONFIG)
        ], p="md", mb="lg", withBorder=True, shadow="sm"),
        
        # 📈 Métricas
        dmc.Paper([
            dmc.Text("Resumen", size="lg", fw=500, mb="md"),
            create_metrics_row(PAGE_ID, METRICS_CONFIG)
        ], p="md", mb="lg", withBorder=True, shadow="sm"),
        
        # 📊 Gráficos
        dmc.Paper([
            dmc.Text("Análisis Visual", size="lg", fw=500, mb="md"),
            html.Div(create_charts_grid(PAGE_ID, CHARTS_CONFIG))
        ], p="md", mb="lg", withBorder=True, shadow="sm"),
        
        # ℹ️ Información adicional (personalizable)
        dmc.Alert(
            "Los datos se actualizan automáticamente según los filtros seleccionados.",
            title="Información",
            color="blue",
            variant="light"
        )
    ])

# Crear layout
layout = create_layout()

# ============================================================
# REGISTRAR CALLBACKS ASYNC (separado del layout)
# ============================================================

# Los callbacks se registran automáticamente con IDs únicos
