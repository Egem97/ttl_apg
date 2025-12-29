"""
Componentes modulares reutilizables para dashboards
"""
import plotly.express as px
import plotly.graph_objects as go
import dash_mantine_components as dmc
from dash import dcc, html, Input, Output, callback
from components.grid import Row, Column
from typing import Dict, List, Any, Optional, Callable


class FilterComponent:
    """Componente reutilizable para filtros"""
    
    def __init__(self, dashboard_id: str, filters_config: List[Dict]):
        self.dashboard_id = dashboard_id
        self.filters_config = filters_config
        self.filter_ids = {}
        
        # Generar IDs únicos para cada filtro
        for filter_config in filters_config:
            filter_name = filter_config['name']
            self.filter_ids[filter_name] = f"{dashboard_id}-{filter_name}-select"
    
    def create_layout(self) -> List[Any]:
        """Crea el layout de los filtros"""
        columns = []
        
        for filter_config in self.filters_config:
            filter_name = filter_config['name']
            filter_id = self.filter_ids[filter_name]
            
            if filter_config['type'] == 'select':
                component = dmc.Select(
                    label=filter_config['label'],
                    placeholder=filter_config.get('placeholder', 'Seleccione...'),
                    id=filter_id,
                    clearable=filter_config.get('clearable', True),
                    mb=10,
                )
            elif filter_config['type'] == 'multiselect':
                component = dmc.MultiSelect(
                    label=filter_config['label'],
                    id=filter_id,
                    clearable=filter_config.get('clearable', True),
                    mb=10,
                )
            else:
                component = html.Div()  # Fallback
            
            columns.append(
                Column([component], size=filter_config.get('size', 2))
            )
        
        return columns
    
    def get_filter_ids(self) -> Dict[str, str]:
        """Retorna los IDs de los filtros"""
        return self.filter_ids


class ChartComponent:
    """Componente reutilizable para gráficos"""
    
    def __init__(self, dashboard_id: str, chart_config: Dict):
        self.dashboard_id = dashboard_id
        self.chart_config = chart_config
        self.chart_id = f"{dashboard_id}-chart"
        self.loading_id = f"{dashboard_id}-loading"
    
    def create_layout(self) -> html.Div:
        """Crea el layout del gráfico"""
        return dcc.Loading(
            id=self.loading_id,
            type=self.chart_config.get('loading_type', 'default'),
            children=[
                dcc.Graph(
                    id=self.chart_id,
                    style=self.chart_config.get('style', {}),
                    config=self.chart_config.get('config', {})
                )
            ]
        )
    
    def create_figure(self, df, aggregation_config: Dict) -> go.Figure:
        """Crea la figura del gráfico basado en configuración"""
        if df.empty:
            return self._create_empty_figure("No hay datos disponibles")
        
        try:
            # Aplicar agregación
            if aggregation_config.get('groupby'):
                agg_dict = aggregation_config.get('agg', {})
                df_agg = df.groupby(aggregation_config['groupby']).agg(agg_dict).reset_index()
            else:
                df_agg = df
            
            # Crear gráfico basado en tipo
            chart_type = self.chart_config.get('type', 'line')
            
            if chart_type == 'line':
                fig = px.line(
                    df_agg, 
                    x=self.chart_config['x'], 
                    y=self.chart_config['y'],
                    title=self.chart_config.get('title', ''),
                    height=self.chart_config.get('height'),
                    width=self.chart_config.get('width')
                )
            elif chart_type == 'bar':
                fig = px.bar(
                    df_agg,
                    x=self.chart_config['x'],
                    y=self.chart_config['y'],
                    title=self.chart_config.get('title', ''),
                    height=self.chart_config.get('height'),
                    width=self.chart_config.get('width')
                )
            elif chart_type == 'scatter':
                fig = px.scatter(
                    df_agg,
                    x=self.chart_config['x'],
                    y=self.chart_config['y'],
                    title=self.chart_config.get('title', ''),
                    height=self.chart_config.get('height'),
                    width=self.chart_config.get('width')
                )
            else:
                fig = self._create_empty_figure(f"Tipo de gráfico '{chart_type}' no soportado")
            
            return fig
            
        except Exception as e:
            print(f"❌ Error creando gráfico: {e}")
            return self._create_empty_figure("Error generando el gráfico")
    
    def _create_empty_figure(self, message: str) -> go.Figure:
        """Crea una figura vacía con mensaje"""
        return go.Figure().add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False
        )
    
    def get_chart_id(self) -> str:
        """Retorna el ID del gráfico"""
        return self.chart_id


class HeaderComponent:
    """Componente reutilizable para encabezados"""
    
    def __init__(self, title: str, subtitle: str = None):
        self.title = title
        self.subtitle = subtitle
    
    def create_layout(self) -> html.Div:
        """Crea el layout del encabezado"""
        components = [
            Row([
                Column([dmc.Title(self.title, order= 1,fw=700)], size=5),#, mb=10
                #*filter_component.create_layout()
            ])
        ]#, mb=15
        
        if self.subtitle:
            components.append(dmc.Text(self.subtitle, size="lg", mb=10))
        
        return html.Div(components)


class MetricsComponent:
    """Componente para mostrar métricas"""
    
    def __init__(self, dashboard_id: str, metrics_config: List[Dict]):
        self.dashboard_id = dashboard_id
        self.metrics_config = metrics_config
        self.metrics_ids = {}
        
        # Generar IDs únicos para cada métrica
        for metric in metrics_config:
            metric_name = metric['name']
            self.metrics_ids[metric_name] = f"{dashboard_id}-metric-{metric_name}"
    
    def create_layout(self) -> Row:
        """Crea el layout de las métricas"""
        columns = []
        
        for metric in self.metrics_config:
            metric_id = self.metrics_ids[metric['name']]
            
            card = dmc.Card(
                children=[
                    dmc.Text(metric['label'], size="sm", c="dimmed"),
                    dmc.Title(id=metric_id, order=2, children="0"),
                ],
                withBorder=True,
                shadow="sm",
                radius="md",
                p="md",
                style={"textAlign": "center"}
            )
            
            columns.append(
                Column([card], size=metric.get('size', 3))
            )
        
        return Row(columns)
    
    def calculate_metrics(self, df, calculations: Dict[str, Callable]) -> Dict[str, Any]:
        """Calcula las métricas basado en el DataFrame"""
        metrics = {}
        
        for metric_name, calculation_func in calculations.items():
            if metric_name in self.metrics_ids:
                try:
                    metrics[metric_name] = calculation_func(df)
                except Exception as e:
                    print(f"❌ Error calculando métrica {metric_name}: {e}")
                    metrics[metric_name] = "Error"
        
        return metrics
    
    def get_metrics_ids(self) -> Dict[str, str]:
        """Retorna los IDs de las métricas"""
        return self.metrics_ids