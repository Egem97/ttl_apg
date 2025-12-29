"""
Configuraciones de dashboards declarativas
Aquí defines la estructura de cada dashboard sin código repetitivo
"""

# Dashboard de Ocupación de Transporte
OCUPACION_TRANSPORTE_CONFIG = {
    'dashboard_id': 'ocupacion-transporte',
    'title': 'OCUPACIÓN DE TRANSPORTE',
    'subtitle': 'Análisis de ocupación por período',
    'data_sources': ['ocupacion_transporte', 'date_options'],
    'filters': [
        {
            'name': 'year',
            'type': 'select',
            'label': 'Año',
            'placeholder': 'Seleccione Año',
            'size': 2
        },
        {
            'name': 'month',
            'type': 'select', 
            'label': 'Mes',
            'placeholder': 'Todos',
            'clearable': True,
            'size': 2
        },
        {
            'name': 'week',
            'type': 'multiselect',
            'label': 'Semana',
            'clearable': True,
            'size': 3
        }
    ],
    'metrics': [
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
        }
    ],
    'charts': [
        {
            'type': 'line',
            'x': 'FECHA',
            'y': 'N° ASIENTOS OCUPADOS',
            'title': 'Ocupación de Transporte por Fecha',
            'height': 400,
            'size': 12,
            'data_source': 'ocupacion_transporte',
            'aggregation': {
                'groupby': ['FECHA'],
                'agg': {'N° ASIENTOS OCUPADOS': 'sum'}
            }
        }
    ],
    'layout': {
        'container_style': {'padding': '20px'},
        'paper_style': {'minHeight': '80vh'}
    }
}

# Dashboard de Costos Diarios Packing
COSTOS_DIARIOS_CONFIG = {
    'dashboard_id': 'costos-diarios',
    'title': 'COSTOS DIARIOS PACKING',
    #'subtitle': 'Análisis de costos de empaque por período',
    'data_sources': ['mayor_analitico_packing', 'date_options'],
    'filters': [
        {
            'name': 'year',
            'type': 'select',
            'label': 'Año',
            'placeholder': 'Seleccione Año',
            'size': 2
        },
        {
            'name': 'month',
            'type': 'select',
            'label': 'Mes', 
            'placeholder': 'Todos',
            'clearable': True,
            'size': 2
        },
        {
            'name': 'week',
            'type': 'multiselect',
            'label': 'Semana',
            'clearable': True,
            'size': 3
        }
    ],
    'metrics': [
        {
            'name': 'total_costo',
            'label': 'Costo Total',
            'type': 'sum',
            'column': 'MONTO',  # Ajustar según columna real
            'size': 4
        },
        {
            'name': 'total_ordenes',
            'label': 'Total Órdenes',
            'type': 'count',
            'size': 4
        },
        {
            'name': 'costo_promedio',
            'label': 'Costo Promedio',
            'type': 'avg',
            'column': 'MONTO',
            'size': 4
        }
    ],
    'charts': [
        {
            'type': 'bar',
            'x': 'SEMANA',
            'y': 'MONTO',
            'title': 'Costos por Semana',
            'height': 350,
            'width': 600,
            'size': 6,
            'data_source': 'mayor_analitico_packing',
            'aggregation': {
                'groupby': ['SEMANA'],
                'agg': {'MONTO': 'sum'}
            }
        },
        {
            'type': 'line',
            'x': 'FECHA',
            'y': 'MONTO',
            'title': 'Tendencia de Costos',
            'height': 350,
            'size': 6,
            'data_source': 'mayor_analitico_packing',
            'aggregation': {
                'groupby': ['FECHA'],
                'agg': {'MONTO': 'sum'}
            }
        }
    ],
    'layout': {
        #'container_style': {'padding': '20px'},
        #'paper_style': {'minHeight': '80vh'}
    }
}

# Dashboard de Ventas (ejemplo de dashboard diferente)
VENTAS_CONFIG = {
    'dashboard_id': 'ventas',
    'title': 'DASHBOARD DE VENTAS',
    'subtitle': 'Análisis completo de ventas',
    'data_sources': ['mayor_analitico_packing'],  # Reutilizando fuente existente
    'filters': [
        {
            'name': 'year',
            'type': 'select',
            'label': 'Año',
            'size': 3
        }
    ],
    'metrics': [
        {
            'name': 'ventas_totales',
            'label': 'Ventas Totales',
            'type': 'sum',
            'column': 'MONTO',
            'size': 6
        },
        {
            'name': 'ticket_promedio',
            'label': 'Ticket Promedio',
            'type': 'avg',
            'column': 'MONTO',
            'size': 6
        }
    ],
    'charts': [
        {
            'type': 'scatter',
            'x': 'FECHA',
            'y': 'MONTO',
            'title': 'Distribución de Ventas',
            'height': 500,
            'size': 12,
            'data_source': 'mayor_analitico_packing'
        }
    ]
}