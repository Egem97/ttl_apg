"""
Dashboard de Costos Diarios - Versión Simplificada  
Ejemplo de diseño diferente usando los mismos componentes
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
    create_chart_card,
    register_page_callbacks
)
from constants import PAGE_TITLE_PREFIX

# Registrar página
dash.register_page(__name__, "/costos-simple", title=PAGE_TITLE_PREFIX + "Costos Simple")

# ============================================================
# CONFIGURACIÓN DEL DASHBOARD
# ============================================================

PAGE_ID = "costos-simple"
DATA_SOURCE = "costos_diarios"  # Diferente fuente de datos

# Filtros más simples
FILTERS_CONFIG = [
    {
        'name': 'year',
        'label': 'Año',
        'type': 'select',
        'size': 3
    },
    {
        'name': 'month', 
        'label': 'Mes',
        'type': 'select',
        'clearable': True,
        'size': 3
    }
]

# Métricas enfocadas en costos
METRICS_CONFIG = [
    {
        'name': 'costo_total',
        'label': 'Costo Total',
        'type': 'sum',
        'column': 'COSTO',
        'size': 4
    },
    {
        'name': 'costo_promedio',
        'label': 'Costo Promedio',
        'type': 'avg',
        'column': 'COSTO',
        'size': 4
    },
    {
        'name': 'dias_registrados',
        'label': 'Días Registrados',
        'type': 'count',
        'size': 4
    }
]

# Gráficos más especializados
CHARTS_CONFIG = [
    {
        'name': 'costo_mensual',
        'title': 'Evolución de Costos Mensuales',
        'type': 'line',
        'x': 'FECHA',
        'y': 'COSTO',
        'height': 500
    },
    {
        'name': 'distribucion_costos',
        'title': 'Distribución por Categoría',
        'type': 'pie',
        'names': 'CATEGORIA',
        'values': 'COSTO',
        'height': 400
    }
]

# ============================================================
# LAYOUT PERSONALIZADO (diferente diseño)
# ============================================================

def create_custom_layout():
    """Layout con diseño personalizado - diferente al anterior"""
    
    return html.Div([
        # Stores invisibles
        html.Div(create_data_stores(PAGE_ID, [DATA_SOURCE])),
        
        # Header con diseño diferente
        dmc.Container([
            Row([
                Column([
                    create_page_header(
                        title="💰 ANÁLISIS DE COSTOS",
                        subtitle="Control y seguimiento de gastos operativos"
                    )
                ], size=8),
                Column([
                    dmc.Button(
                        "Exportar Datos",
                        variant="outline",
                        #leftSection=dmc.rem("🔄", 16),
                        style={"marginTop": "20px"}
                    )
                ], size=4)
            ])
        ], size="xl", mb="lg"),
        
        # Layout en columnas (diferente al anterior)
        dmc.Container([
            Row([
                # Columna izquierda: Filtros y métricas
                Column([
                    # Filtros en card compacta
                    dmc.Card([
                        dmc.Text("🔍 Filtros", size="md", fw=500, mb="sm"),
                        create_filters_row(PAGE_ID, FILTERS_CONFIG)
                    ], withBorder=True, shadow="sm", p="md", mb="md"),
                    
                    # Métricas en stack vertical
                    dmc.Stack([
                        dmc.Text("📊 Resumen Ejecutivo", size="md", fw=500),
                        create_metrics_row(PAGE_ID, METRICS_CONFIG)
                    ], gap="md")
                    
                ], size=4),
                
                # Columna derecha: Gráficos principales
                Column([
                    # Gráfico principal grande
                    create_chart_card(PAGE_ID, CHARTS_CONFIG[0]),
                    
                    # Gráfico secundario más pequeño
                    create_chart_card(PAGE_ID, CHARTS_CONFIG[1])
                    
                ], size=8)
            ])
        ], size="xl"),
        
        # Footer con información
        dmc.Container([
            dmc.Divider(mb="md"),
            dmc.Group([
                dmc.Text("Última actualización: Hoy", size="sm", c="dimmed"),
                dmc.Badge("En línea", color="green", variant="light")
            ], justify="space-between")
        ], size="xl", mt="xl")
    ])

# Crear layout
layout = create_custom_layout()

# ============================================================
# REGISTRAR CALLBACKS (mismo sistema, diferentes datos)
# ============================================================

register_page_callbacks(
    page_id=PAGE_ID,
    data_source=DATA_SOURCE,
    filters_config=FILTERS_CONFIG,
    charts_config=CHARTS_CONFIG,
    metrics_config=METRICS_CONFIG
)