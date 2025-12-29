"""
Callback Manager - Manejador centralizado de callbacks async
Registra callbacks con IDs únicos y maneja la lógica async
"""
import asyncio
from typing import Dict, Any, List, Callable
from dash import Input, Output, State, callback, no_update
import plotly.express as px
import plotly.graph_objects as go
from data.data_manager import data_manager
from helpers.helpers import generate_list_month


class CallbackManager:
    """Manejador centralizado de callbacks con IDs únicos"""
    
    def __init__(self):
        self.registered_callbacks = {}
    
    def generate_id(self, page_id: str, component_type: str, element_name: str = "") -> str:
        """Genera un ID único para componentes y callbacks"""
        if element_name:
            return f"{page_id}-{component_type}-{element_name}"
        return f"{page_id}-{component_type}"
    
    def register_data_loader(self, page_id: str, data_sources: List[str]):
        """
        Registra callback para cargar datos al iniciar la página
        
        Args:
            page_id: ID único de la página
            data_sources: Lista de fuentes de datos a cargar
        """
        
        # IDs para los stores de datos
        data_store_ids = [self.generate_id(page_id, "data-store", source) for source in data_sources]
        url_store_id = self.generate_id(page_id, "url-store")
        
        @callback(
            [Output(store_id, "data") for store_id in data_store_ids],
            Input(url_store_id, "data"),
            prevent_initial_call=False
        )
        async def load_initial_data(url_data):
            """Carga inicial de datos de forma asíncrona"""
            try:
                print(f"🚀 Iniciando carga de datos para {page_id}")
                
                # Cargar todos los datos de forma paralela
                tasks = [data_manager.get_data(source) for source in data_sources]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Procesar resultados
                processed_results = []
                for i, (source, result) in enumerate(zip(data_sources, results)):
                    if isinstance(result, Exception):
                        print(f"❌ Error cargando {source}: {result}")
                        processed_results.append(None)
                    elif result is not None and not result.empty:
                        processed_results.append(result.to_dict('records'))
                        print(f"✅ {source}: {len(result)} registros cargados")
                    else:
                        processed_results.append(None)
                
                return processed_results
                
            except Exception as e:
                print(f"❌ Error en carga inicial: {e}")
                return [None] * len(data_sources)
    
    def register_filter_updater(self, page_id: str, data_source: str, filter_configs: List[Dict]):
        """
        Registra callback para actualizar opciones de filtros
        
        Args:
            page_id: ID único de la página
            data_source: Fuente de datos principal
            filter_configs: Configuración de filtros
        """
        
        data_store_id = self.generate_id(page_id, "data-store", data_source)
        filter_outputs = []
        
        for filter_config in filter_configs:
            filter_name = filter_config['name']
            filter_id = self.generate_id(page_id, "filter", filter_name)
            filter_outputs.append(Output(filter_id, "data"))
        
        @callback(
            filter_outputs,
            Input(data_store_id, "data"),
            prevent_initial_call=False
        )
        async def update_filter_options(data):
            """Actualiza opciones de filtros basado en los datos"""
            if not data:
                return [[] for _ in filter_configs]
            
            try:
                # Obtener opciones de fecha del data manager
                options = await data_manager.get_date_options(data_source)
                
                results = []
                for filter_config in filter_configs:
                    filter_name = filter_config['name']
                    
                    if filter_name == 'year':
                        results.append(options.get('years', []))
                    elif filter_name == 'month':
                        results.append(options.get('months', []))
                    elif filter_name == 'week':
                        results.append(options.get('weeks', []))
                    else:
                        results.append([])
                
                return results
                
            except Exception as e:
                print(f"❌ Error actualizando filtros: {e}")
                return [[] for _ in filter_configs]
    
    def register_dependent_filters(self, page_id: str, start_year: int = 2024, start_month: int = 1):
        """
        Registra callbacks para filtros dependientes usando generate_list_month
        
        Args:
            page_id: ID único de la página
            start_year: Año de inicio para generar opciones
            start_month: Mes de inicio para generar opciones
        """
        
        # IDs de los filtros
        year_filter_id = self.generate_id(page_id, "filter", "year")
        month_filter_id = self.generate_id(page_id, "filter", "month")
        week_filter_id = self.generate_id(page_id, "filter", "week")
        
        # Store para los datos de fechas generados
        dates_store_id = self.generate_id(page_id, "dates-store")
        
        # 1. Callback para cargar datos iniciales de fechas
        @callback(
            Output(dates_store_id, "data"),
            Input(year_filter_id, "id"),  # Trigger inicial
            prevent_initial_call=False
        )
        async def load_dates_data(_):
            """Carga datos de fechas usando generate_list_month"""
            try:
                print(f"🗓️ Generando opciones de fechas desde {start_year}/{start_month}")
                
                # Generar DataFrame de fechas de forma asíncrona
                df_dates = await asyncio.to_thread(generate_list_month, start_year, start_month)
                
                if df_dates is not None and not df_dates.empty:
                    return df_dates.to_dict('records')
                return []
                
            except Exception as e:
                print(f"❌ Error generando datos de fechas: {e}")
                return []
        
        # 2. Callback para actualizar opciones de año
        @callback(
            Output(year_filter_id, "data"),
            Input(dates_store_id, "data"),
            prevent_initial_call=False
        )
        async def update_year_options(dates_data):
            """Actualiza opciones de año"""
            if not dates_data:
                return []
            
            try:
                # Extraer años únicos
                years = list(set([record['YEAR'] for record in dates_data]))
                years.sort(reverse=True)  # Más recientes primero
                
                return [{'label': str(year), 'value': str(year)} for year in years]
                
            except Exception as e:
                print(f"❌ Error actualizando años: {e}")
                return []
        
        # 3. Callback para actualizar opciones de mes (dependiente del año)
        @callback(
            Output(month_filter_id, "data"),
            Input(year_filter_id, "value"),
            State(dates_store_id, "data"),
            prevent_initial_call=False
        )
        async def update_month_options(selected_year, dates_data):
            """Actualiza opciones de mes basado en el año seleccionado"""
            if not dates_data or selected_year is None:
                return []
            
            try:
                # Filtrar meses para el año seleccionado
                months_for_year = [
                    record for record in dates_data 
                    if record['YEAR'] == selected_year
                ]
                
                # Crear diccionario para evitar duplicados y mantener orden
                month_dict = {}
                for record in months_for_year:
                    month_num = record['MES']
                    month_text = record['MES_TEXT']
                    month_dict[month_num] = month_text
                
                # Ordenar por número de mes
                sorted_months = sorted(month_dict.items())
                
                return [
                    {'label': month_text, 'value': str(month_num)}
                    for month_num, month_text in sorted_months
                ]
                
            except Exception as e:
                print(f"❌ Error actualizando meses: {e}")
                return []
        
        # 4. Callback para actualizar opciones de semana (dependiente del año y mes)
        @callback(
            Output(week_filter_id, "data"),
            [Input(year_filter_id, "value"), Input(month_filter_id, "value")],
            State(dates_store_id, "data"),
            prevent_initial_call=False
        )
        async def update_week_options(selected_year, selected_month, dates_data):
            """Actualiza opciones de semana basado en año y mes seleccionados"""
            if not dates_data or selected_year is None:
                return []
            
            try:
                # Filtrar por año
                filtered_data = [
                    record for record in dates_data 
                    if record['YEAR'] == selected_year
                ]
                
                # Si hay mes seleccionado, filtrar también por mes
                if selected_month is not None:
                    filtered_data = [
                        record for record in filtered_data
                        if record['MES'] == selected_month
                    ]
                
                # Extraer semanas únicas
                weeks = list(set([record['SEMANA'] for record in filtered_data]))
                weeks.sort()
                
                return [
                    {'label': f'Semana {week}', 'value': str(week)}
                    for week in weeks
                ]
                
            except Exception as e:
                print(f"❌ Error actualizando semanas: {e}")
                return []
    
    def register_chart_updater(self, page_id: str, data_source: str, chart_configs: List[Dict], 
                             filter_configs: List[Dict], metrics_configs: List[Dict] = None):
        """
        Registra callback para actualizar gráficos y métricas
        
        Args:
            page_id: ID único de la página
            data_source: Fuente de datos principal
            chart_configs: Configuración de gráficos
            filter_configs: Configuración de filtros
            metrics_configs: Configuración de métricas (opcional)
        """
        
        # Outputs para gráficos
        chart_outputs = []
        for chart_config in chart_configs:
            chart_id = self.generate_id(page_id, "chart", chart_config['name'])
            chart_outputs.append(Output(chart_id, "figure"))
        
        # Outputs para métricas
        metrics_outputs = []
        if metrics_configs:
            for metric_config in metrics_configs:
                metric_id = self.generate_id(page_id, "metric", metric_config['name'])
                metrics_outputs.append(Output(metric_id, "children"))
        
        # Inputs de filtros
        filter_inputs = []
        for filter_config in filter_configs:
            filter_id = self.generate_id(page_id, "filter", filter_config['name'])
            filter_inputs.append(Input(filter_id, "value"))
        
        # Store de datos
        data_store_id = self.generate_id(page_id, "data-store", data_source)
        
        @callback(
            chart_outputs + metrics_outputs,
            filter_inputs,
            State(data_store_id, "data"),
            prevent_initial_call=False
        )
        async def update_charts_and_metrics(*args):
            """Actualiza gráficos y métricas basado en filtros"""
            try:
                # Separar argumentos
                filter_values = args[:-1]  # Todos menos el último (state)
                data = args[-1]  # Último argumento (data del store)
                
                if not data:
                    empty_charts = [go.Figure() for _ in chart_configs]
                    empty_metrics = ["0" for _ in (metrics_configs or [])]
                    return empty_charts + empty_metrics
                
                # Crear diccionario de filtros
                filters = {}
                filter_column_map = {
                    'year': 'AÑO',
                    'month': 'MES', 
                    'week': 'SEMANA'
                }
                
                for filter_config, value in zip(filter_configs, filter_values):
                    if value is not None and value != []:
                        column_name = filter_column_map.get(filter_config['name'])
                        if column_name:
                            # Convertir valores string de vuelta a números para filtrar
                            if filter_config['name'] in ['year', 'month']:
                                try:
                                    filters[column_name] = int(value)
                                except (ValueError, TypeError):
                                    filters[column_name] = value
                            elif filter_config['name'] == 'week':
                                try:
                                    # Para semanas múltiples, convertir cada una
                                    if isinstance(value, list):
                                        filters[column_name] = [int(v) for v in value]
                                    else:
                                        filters[column_name] = int(value)
                                except (ValueError, TypeError):
                                    filters[column_name] = value
                            else:
                                filters[column_name] = value
                
                # Obtener datos filtrados
                df = await data_manager.get_filtered_data(data_source, filters)
                
                if df is None or df.empty:
                    empty_charts = [go.Figure() for _ in chart_configs]
                    empty_metrics = ["0" for _ in (metrics_configs or [])]
                    return empty_charts + empty_metrics
                
                # Generar gráficos
                charts = []
                for chart_config in chart_configs:
                    chart = await self._create_chart(df, chart_config)
                    charts.append(chart)
                
                # Calcular métricas
                metrics = []
                if metrics_configs:
                    for metric_config in metrics_configs:
                        metric_value = await self._calculate_metric(df, metric_config)
                        metrics.append(str(metric_value))
                
                return charts + metrics
                
            except Exception as e:
                print(f"❌ Error actualizando gráficos: {e}")
                empty_charts = [go.Figure() for _ in chart_configs]
                empty_metrics = ["0" for _ in (metrics_configs or [])]
                return empty_charts + empty_metrics
    
    async def _create_chart(self, df, chart_config: Dict) -> go.Figure:
        """Crea un gráfico basado en la configuración"""
        try:
            chart_type = chart_config.get('type', 'bar')
            
            if chart_type == 'bar':
                fig = px.bar(
                    df, 
                    x=chart_config.get('x'),
                    y=chart_config.get('y'),
                    title=chart_config.get('title', ''),
                    color=chart_config.get('color')
                )
            elif chart_type == 'line':
                fig = px.line(
                    df,
                    x=chart_config.get('x'),
                    y=chart_config.get('y'), 
                    title=chart_config.get('title', ''),
                    color=chart_config.get('color')
                )
            elif chart_type == 'pie':
                fig = px.pie(
                    df,
                    names=chart_config.get('names'),
                    values=chart_config.get('values'),
                    title=chart_config.get('title', '')
                )
            else:
                fig = go.Figure()
            
            # Aplicar estilo
            fig.update_layout(
                template="plotly_white",
                height=chart_config.get('height', 400)
            )
            
            return fig
            
        except Exception as e:
            print(f"❌ Error creando gráfico: {e}")
            return go.Figure()
    
    async def _calculate_metric(self, df, metric_config: Dict) -> Any:
        """Calcula una métrica basada en la configuración"""
        try:
            metric_type = metric_config.get('type', 'count')
            
            if metric_type == 'count':
                return len(df)
            elif metric_type == 'sum':
                column = metric_config.get('column')
                if column and column in df.columns:
                    return df[column].sum()
            elif metric_type == 'avg':
                column = metric_config.get('column')
                if column and column in df.columns:
                    return round(df[column].mean(), 2)
            elif metric_type == 'max':
                column = metric_config.get('column')
                if column and column in df.columns:
                    return df[column].max()
            
            return 0
            
        except Exception as e:
            print(f"❌ Error calculando métrica: {e}")
            return 0


# Instancia global del manejador de callbacks
callback_manager = CallbackManager()