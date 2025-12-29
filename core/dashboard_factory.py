"""
DashboardFactory - Sistema para crear dashboards de forma declarativa
"""
import asyncio
from typing import Dict, List, Any, Optional
import dash_mantine_components as dmc
from dash import html, dcc, Input, Output, State, callback
from components.grid import Row, Column

from .data_manager import data_manager
from .components import FilterComponent, ChartComponent, HeaderComponent, MetricsComponent


class DashboardConfig:
    """Configuración declarativa para un dashboard"""
    
    def __init__(self, config: Dict):
        self.dashboard_id = config['dashboard_id']
        self.title = config['title']
        self.subtitle = config.get('subtitle')
        self.data_sources = config['data_sources']  # Lista de fuentes de datos requeridas
        self.filters = config.get('filters', [])
        self.charts = config.get('charts', [])
        self.metrics = config.get('metrics', [])
        self.layout_config = config.get('layout', {})


class DashboardFactory:
    """Factory para crear dashboards basados en configuración"""
    
    def __init__(self):
        self.created_dashboards = {}
    
    def create_dashboard(self, config: DashboardConfig) -> html.Div:
        """Crea un dashboard completo basado en la configuración"""
        
        # Registrar el dashboard
        self.created_dashboards[config.dashboard_id] = config
        
        # Crear componentes
        components = []
        
        # 1. Stores para caché de datos
        data_stores = data_manager.get_cache_stores(config.dashboard_id)
        components.extend(data_stores)
        
        # 2. Header
        if config.title:
            header = HeaderComponent(config.title, config.subtitle)
            components.append(header.create_layout())
        
        # 3. Container principal
        main_content = []
        
        # 4. Filtros
        
        
        # 5. Métricas
        if config.metrics:
            metrics_component = MetricsComponent(config.dashboard_id, config.metrics)
            main_content.append(metrics_component.create_layout())
            main_content.append(dmc.Divider(variant="solid", mb=15))
        
        # 6. Gráficos
        chart_components = []
        for chart_config in config.charts:
            chart_component = ChartComponent(
                f"{config.dashboard_id}-chart-{len(chart_components)}", 
                chart_config
            )
            chart_components.append(chart_component)
            
            # Layout del gráfico
            chart_size = chart_config.get('size', 12)
            chart_column = Column([chart_component.create_layout()], size=chart_size)
            main_content.append(Row([chart_column]))
        
        # Container final
        paper = dmc.Paper(
            withBorder=True,
            shadow="md",
            radius="md",
            p="md",
            style=config.layout_config.get('paper_style', {}),
            children=main_content
        )
        
        components.append(paper)
        
        # Registrar callbacks
        self._register_callbacks(config, None if config.filters else "", 
                                chart_components, 
                                MetricsComponent(config.dashboard_id, config.metrics) if config.metrics else None)
        
        return dmc.Container(
            fluid=True,
            children=components,
            style=config.layout_config.get('container_style', {})
        )
    
    def _register_callbacks(self, config: DashboardConfig, 
                          filter_component: Optional[FilterComponent],
                          chart_components: List[ChartComponent],
                          metrics_component: Optional[MetricsComponent]):
        """Registra todos los callbacks para el dashboard"""
        
        # 1. Callback para cargar datos
        for source_name in config.data_sources:
            store_id = f"{config.dashboard_id}-{data_manager.data_sources[source_name].cache_key}"
            
            @callback(
                Output(store_id, 'data'),
                Input(store_id, 'id'),
                prevent_initial_call=False
            )
            async def load_data(_, source=source_name):
                result = await data_manager.load_data_source(source)
                return result['data'] if result['success'] else []
        
        # 2. Callback para filtros (si existen)
        if filter_component and 'date_options' in config.data_sources:
            date_store_id = f"{config.dashboard_id}-date-options-store"
            filter_ids = filter_component.get_filter_ids()
            
            # Poblar opciones de filtros
            if 'year' in filter_ids:
                @callback(
                    [Output(filter_ids['year'], 'data'),
                     Output(filter_ids['year'], 'value')],
                    Input(date_store_id, 'data')
                )
                def populate_year_options(date_options):
                    if not date_options:
                        return [], None
                    return date_options.get('years', []), date_options.get('default_year')
            
            if 'month' in filter_ids:
                @callback(
                    [Output(filter_ids['month'], 'data'),
                     Output(filter_ids['month'], 'value')],
                    [Input(filter_ids['year'], 'value'),
                     Input(date_store_id, 'data')]
                )
                def populate_month_options(selected_year, date_options):
                    if not date_options or not selected_year:
                        return [], None
                    return date_options.get('months', []), None
            
            if 'week' in filter_ids:
                @callback(
                    [Output(filter_ids['week'], 'data'),
                     Output(filter_ids['week'], 'value')],
                    [Input(filter_ids['year'], 'value'),
                     Input(filter_ids['month'], 'value'),
                     Input(date_store_id, 'data')]
                )
                def populate_week_options(selected_year, selected_month, date_options):
                    if not date_options:
                        return [], None
                    return date_options.get('weeks', []), None
        
        # 3. Callbacks para gráficos
        for i, chart_component in enumerate(chart_components):
            chart_config = config.charts[i]
            main_data_source = chart_config.get('data_source', config.data_sources[0])
            store_id = f"{config.dashboard_id}-{data_manager.data_sources[main_data_source].cache_key}"
            
            # Inputs para el callback
            inputs = [Input(store_id, 'data')]
            
            # Agregar filtros como inputs si existen
            if filter_component:
                filter_ids = filter_component.get_filter_ids()
                for filter_name in filter_ids:
                    inputs.append(Input(filter_ids[filter_name], 'value'))
            
            @callback(
                Output(chart_component.get_chart_id(), 'figure'),
                inputs,
                prevent_initial_call=True
            )
            def update_chart(cached_data, *filter_values, 
                           chart_comp=chart_component, 
                           chart_cfg=chart_config,
                           filter_comp=filter_component):
                
                if not cached_data:
                    return chart_comp._create_empty_figure("No hay datos disponibles")
                
                # Preparar filtros
                filters = {}
                if filter_comp:
                    filter_names = list(filter_comp.get_filter_ids().keys())
                    for i, filter_value in enumerate(filter_values):
                        if i < len(filter_names):
                            filters[filter_names[i]] = filter_value
                
                # Aplicar filtros
                df = data_manager.apply_filters(cached_data, filters)
                
                # Crear gráfico
                aggregation_config = chart_cfg.get('aggregation', {})
                return chart_comp.create_figure(df, aggregation_config)
        
        # 4. Callbacks para métricas (si existen)
        if metrics_component:
            main_data_source = config.data_sources[0]  # Usar primera fuente por defecto
            store_id = f"{config.dashboard_id}-{data_manager.data_sources[main_data_source].cache_key}"
            
            inputs = [Input(store_id, 'data')]
            
            if filter_component:
                filter_ids = filter_component.get_filter_ids()
                for filter_name in filter_ids:
                    inputs.append(Input(filter_ids[filter_name], 'value'))
            
            metrics_ids = metrics_component.get_metrics_ids()
            outputs = [Output(metric_id, 'children') for metric_id in metrics_ids.values()]
            
            @callback(
                outputs,
                inputs,
                prevent_initial_call=True
            )
            def update_metrics(cached_data, *filter_values):
                if not cached_data:
                    return ["0"] * len(outputs)
                
                # Preparar filtros
                filters = {}
                if filter_component:
                    filter_names = list(filter_component.get_filter_ids().keys())
                    for i, filter_value in enumerate(filter_values):
                        if i < len(filter_names):
                            filters[filter_names[i]] = filter_value
                
                # Aplicar filtros
                df = data_manager.apply_filters(cached_data, filters)
                
                # Calcular métricas
                calculations = {}
                for metric in config.metrics:
                    metric_name = metric['name']
                    if metric['type'] == 'sum':
                        calculations[metric_name] = lambda df, col=metric['column']: f"{df[col].sum():,.0f}" if col in df.columns else "0"
                    elif metric['type'] == 'count':
                        calculations[metric_name] = lambda df: f"{len(df):,}"
                    elif metric['type'] == 'avg':
                        calculations[metric_name] = lambda df, col=metric['column']: f"{df[col].mean():.2f}" if col in df.columns else "0"
                
                metrics_values = metrics_component.calculate_metrics(df, calculations)
                
                # Retornar valores en el orden correcto
                return [metrics_values.get(metric['name'], "0") for metric in config.metrics]


# Instancia global del factory
dashboard_factory = DashboardFactory()