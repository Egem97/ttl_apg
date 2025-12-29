"""
Componentes UI simples y reutilizables
Fáciles de usar en layouts directos
"""
import dash_mantine_components as dmc
from dash import dcc, html
from components.grid import Row, Column
from callbacks.callback_manager import callback_manager


def create_page_header(title: str, subtitle: str = None) -> html.Div:
    """Crea un header simple para la página"""
    children = [dmc.Title(title, order=1, mb="xs")]
    
    if subtitle:
        children.append(dmc.Text(subtitle, size="lg", c="dimmed", mb="lg"))
    
    return html.Div(children, style={"marginBottom": "20px"})


def create_data_stores(page_id: str, data_sources: list, include_dates_store: bool = False) -> list:
    """Crea los stores necesarios para almacenar datos"""
    stores = []
    
    # Store para trigger de carga inicial
    stores.append(dcc.Store(
        id=callback_manager.generate_id(page_id, "url-store"),
        data={"trigger": True}
    ))
    
    # Stores para cada fuente de datos
    for source in data_sources:
        store_id = callback_manager.generate_id(page_id, "data-store", source)
        stores.append(dcc.Store(id=store_id))
    
    # Store para datos de fechas (si se usan filtros dependientes)
    if include_dates_store:
        dates_store_id = callback_manager.generate_id(page_id, "dates-store")
        stores.append(dcc.Store(id=dates_store_id))
    
    return stores


def create_filters_row(page_id: str, filters_config: list) -> Row:
    """
    Crea una fila de filtros simples
    
    Args:
        page_id: ID único de la página
        filters_config: Lista con configuración de filtros
        
    Example:
        filters_config = [
            {'name': 'year', 'label': 'Año', 'type': 'select', 'size': 2},
            {'name': 'month', 'label': 'Mes', 'type': 'select', 'size': 2, 'clearable': True},
            {'name': 'week', 'label': 'Semana', 'type': 'multiselect', 'size': 3, 'clearable': True}
        ]
    """
    columns = []
    
    for filter_config in filters_config:
        filter_id = callback_manager.generate_id(page_id, "filter", filter_config['name'])
        size = filter_config.get('size', 3)
        
        # Crear componente según el tipo
        if filter_config['type'] == 'select':
            component = dmc.Select(
                id=filter_id,
                label=filter_config['label'],
                placeholder=filter_config.get('placeholder', f"Seleccione {filter_config['label']}"),
                clearable=filter_config.get('clearable', False),
                data=[],  # Se llenará via callback
                mb="md"
            )
        elif filter_config['type'] == 'multiselect':
            component = dmc.MultiSelect(
                id=filter_id,
                label=filter_config['label'],
                placeholder=filter_config.get('placeholder', f"Seleccione {filter_config['label']}"),
                clearable=filter_config.get('clearable', True),
                data=[],  # Se llenará via callback
                mb="md"
            )
        else:
            # Fallback a input text
            component = dmc.TextInput(
                id=filter_id,
                label=filter_config['label'],
                placeholder=filter_config.get('placeholder', ""),
                mb="md"
            )
        
        columns.append(Column([component], size=size))
    
    return Row(columns)


def create_metrics_row(page_id: str, metrics_config: list) -> Row:
    """
    Crea una fila de métricas simples
    
    Args:
        page_id: ID único de la página
        metrics_config: Lista con configuración de métricas
        
    Example:
        metrics_config = [
            {'name': 'total_records', 'label': 'Total Registros', 'size': 3},
            {'name': 'total_amount', 'label': 'Total Monto', 'size': 3}
        ]
    """
    columns = []
    
    for metric_config in metrics_config:
        metric_id = callback_manager.generate_id(page_id, "metric", metric_config['name'])
        size = metric_config.get('size', 3)
        
        card = dmc.Card(
            children=[
                dmc.Text(metric_config['label'], size="sm", c="dimmed"),
                dmc.Title(id=metric_id, order=2, children="0"),
            ],
            withBorder=True,
            shadow="sm",
            radius="md",
            p="md",
            style={"textAlign": "center"}
        )
        
        columns.append(Column([card], size=size))
    
    return Row(columns)


def create_chart_card(page_id: str, chart_config: dict) -> dmc.Card:
    """
    Crea una tarjeta con gráfico
    
    Args:
        page_id: ID único de la página
        chart_config: Configuración del gráfico
        
    Example:
        chart_config = {
            'name': 'main_chart',
            'title': 'Gráfico Principal',
            'height': 400
        }
    """
    chart_id = callback_manager.generate_id(page_id, "chart", chart_config['name'])
    
    return dmc.Card(
        children=[
            dmc.CardSection([
                dmc.Text(chart_config.get('title', ''), fw=500, size="lg", mb="md")
            ], inheritPadding=True, py="xs"),
            dmc.CardSection([
                dcc.Graph(
                    id=chart_id,
                    figure={},
                    style={"height": f"{chart_config.get('height', 400)}px"}
                )
            ])
        ],
        withBorder=True,
        shadow="sm",
        radius="md",
        mb="lg"
    )


def create_charts_grid(page_id: str, charts_config: list) -> list:
    """
    Crea una grilla de gráficos
    
    Args:
        page_id: ID único de la página
        charts_config: Lista con configuración de gráficos
        
    Example:
        charts_config = [
            {'name': 'chart1', 'title': 'Gráfico 1', 'size': 6},
            {'name': 'chart2', 'title': 'Gráfico 2', 'size': 6}
        ]
    """
    elements = []
    current_row = []
    current_size = 0
    
    for chart_config in charts_config:
        size = chart_config.get('size', 12)
        chart_card = create_chart_card(page_id, chart_config)
        
        # Si el gráfico ocupa toda la fila o no cabe en la actual
        if size == 12 or current_size + size > 12:
            # Agregar fila actual si tiene elementos
            if current_row:
                elements.append(Row(current_row))
                current_row = []
                current_size = 0
            
            # Si ocupa toda la fila, agregarlo directamente
            if size == 12:
                elements.append(Row([Column([chart_card], size=12)]))
            else:
                current_row.append(Column([chart_card], size=size))
                current_size = size
        else:
            # Agregar a la fila actual
            current_row.append(Column([chart_card], size=size))
            current_size += size
    
    # Agregar última fila si tiene elementos
    if current_row:
        elements.append(Row(current_row))
    
    return elements


def register_page_callbacks(page_id: str, data_source: str, filters_config: list, 
                           charts_config: list, metrics_config: list = None):
    """
    Registra todos los callbacks necesarios para la página
    
    Args:
        page_id: ID único de la página
        data_source: Fuente de datos principal
        filters_config: Configuración de filtros
        charts_config: Configuración de gráficos
        metrics_config: Configuración de métricas (opcional)
    """
    
    # Registrar carga inicial de datos
    data_sources = [data_source]  # Pueden ser múltiples si es necesario
    callback_manager.register_data_loader(page_id, data_sources)
    
    # Registrar actualización de filtros
    callback_manager.register_filter_updater(page_id, data_source, filters_config)
    
    # Registrar actualización de gráficos y métricas
    callback_manager.register_chart_updater(
        page_id, data_source, charts_config, filters_config, metrics_config
    )


def register_dependent_filters_callbacks(page_id: str, data_source: str, charts_config: list, 
                                       metrics_config: list = None, start_year: int = 2024, 
                                       start_month: int = 1):
    """
    Registra callbacks para filtros dependientes usando generate_list_month
    
    Args:
        page_id: ID único de la página
        data_source: Fuente de datos principal
        charts_config: Configuración de gráficos
        metrics_config: Configuración de métricas (opcional)
        start_year: Año de inicio para generar opciones
        start_month: Mes de inicio para generar opciones
    """
    
    # Registrar carga inicial de datos (si es necesario)
    data_sources = [data_source]
    callback_manager.register_data_loader(page_id, data_sources)
    
    # Registrar filtros dependientes
    callback_manager.register_dependent_filters(page_id, start_year, start_month)
    
    
    # Registrar actualización de gráficos y métricas
    #callback_manager.register_chart_updater(
    #    page_id, data_source, charts_config, filters_config, metrics_config
    #)