"""
Componente Dashboard reutilizable con IDs únicos para evitar conflictos entre páginas
"""
import dash
import plotly.graph_objects as go
import pandas as pd
import dash_mantine_components as dmc
import plotly.express as px
import asyncio
from dash import html, dcc, Input, Output, callback
from components.grid import Row, Column
from helpers.get_token import get_access_token
from helpers.get_api import listar_archivos_en_carpeta_compartida
from helpers.helpers import *
from constants import DRIVE_ID_CARPETA_STORAGE, FOLDER_ID_CARPETA_STORAGE


class DashboardComponent:
    """
    Componente Dashboard reutilizable que genera IDs únicos para cada instancia
    """
    
    def __init__(self, page_id: str, title: str = "Dashboard", chart_title: str = "Gráfico"):
        """
        Inicializa el componente con un ID único de página
        
        Args:
            page_id: Identificador único para esta instancia (ej: 'dashboard', 'costos-diarios')
            title: Título del dashboard
            chart_title: Título del gráfico
        """
        self.page_id = page_id
        self.title = title
        self.chart_title = chart_title
        
        # Generar IDs únicos basados en page_id
        self.ids = {
            'data_store': f'{page_id}-data-store',
            'parquet_data_store': f'{page_id}-parquet-data-store', 
            'date_options_store': f'{page_id}-date-options-store',
            'year_select': f'{page_id}-year-select',
            'month_select': f'{page_id}-month-select',
            'week_select': f'{page_id}-week-select',
            'loading_graph': f'{page_id}-loading-graph',
            'graph_container': f'{page_id}-graph-container'
        }
        
        # Registrar los callbacks para esta instancia
        self._register_callbacks()
    
    def create_layout(self):
        """
        Crea el layout del dashboard con IDs únicos
        """
        return dmc.Container(
            fluid=True,
            children=[
                # Stores para cachear datos
                dcc.Store(id=self.ids['data_store'], storage_type='session'),
                dcc.Store(id=self.ids['parquet_data_store'], storage_type='session'),
                dcc.Store(id=self.ids['date_options_store'], storage_type='session'),
                
                dmc.Paper(
                    withBorder=True,
                    shadow="md",
                    radius="md",
                    p="md",
                    style={"height": "80%"},
                    children=[
                        Row([
                            Column([
                                dmc.Title(self.title, order=1, mt=0, mb=15)
                            ], size=6),
                            Column([
                                dmc.Select(
                                    label="Año",
                                    placeholder="Seleccione Año", 
                                    id=self.ids['year_select'],
                                ),
                            ], size=1),
                            Column([
                                dmc.Select(
                                    label="Mes",
                                    placeholder="Todos",
                                    id=self.ids['month_select'],
                                    clearable=True,
                                    mb=10,
                                ),
                            ], size=2),
                            Column([
                                dmc.MultiSelect(
                                    label="Semana",
                                    id=self.ids['week_select'],
                                    clearable=True,
                                    mb=10,
                                ),
                            ], size=3),
                        ]),
                    ]
                ),
                
                dmc.Divider(variant="solid", mb=15),
                
                # Gráfico con indicador de carga
                dcc.Loading(
                    id=self.ids['loading_graph'],
                    type="default",
                    children=[
                        dcc.Graph(id=self.ids['graph_container'])
                    ]
                ),
            ]
        )
    
    def _register_callbacks(self):
        """
        Registra todos los callbacks para esta instancia del dashboard
        """
        
        # Callback para opciones de año
        @callback(
            [Output(self.ids['year_select'], 'data'),
             Output(self.ids['year_select'], 'value')],
            Input(self.ids['year_select'], 'id')
        )
        async def populate_year_options(_):
            """Pobla las opciones de año de forma asíncrona"""
            try:
                print(f"📅 [{self.page_id}] Generando opciones de año...")
                
                df = await asyncio.to_thread(generate_list_month, 2024, 8)
                years = sorted(df['YEAR'].unique())
                year_options = [{'value': str(year), 'label': str(year)} for year in years]
                default_year = str(years[-1]) if years else None
                
                print(f"✅ [{self.page_id}] Opciones de año generadas: {years}")
                return year_options, default_year
                
            except Exception as e:
                print(f"❌ [{self.page_id}] Error generando opciones de año: {e}")
                return [], None
        
        # Callback para opciones de mes
        @callback(
            [Output(self.ids['month_select'], 'data'),
             Output(self.ids['month_select'], 'value')],
            Input(self.ids['year_select'], 'value')
        )
        def populate_month_options(selected_year):
            """Pobla las opciones de mes basado en el año seleccionado"""
            if not selected_year:
                return [], None
            
            try:
                year = int(selected_year)
                df = generate_list_month(2024, 8)
                df_year = df[df['YEAR'] == year]
                months_data = df_year[['MES', 'MES_TEXT']].drop_duplicates().sort_values('MES')
                
                month_options = [
                    {'value': str(row['MES']), 'label': row['MES_TEXT']} 
                    for _, row in months_data.iterrows()
                ]
                
                return month_options, None
                
            except (ValueError, TypeError):
                return [], None
        
        # Callback para opciones de semana
        @callback(
            [Output(self.ids['week_select'], 'data'),
             Output(self.ids['week_select'], 'value')],
            [Input(self.ids['year_select'], 'value'),
             Input(self.ids['month_select'], 'value')]
        )
        def populate_week_options(selected_year, selected_month):
            """Pobla las opciones de semana basado en año y mes seleccionados"""
            if not selected_year:
                return [], None
            
            try:
                year = int(selected_year)
                df = generate_list_month(2024, 8)
                
                if not selected_month:
                    df_filtered = df[df['YEAR'] == year]
                else:
                    month = int(selected_month)
                    df_filtered = df[(df['YEAR'] == year) & (df['MES'] == month)]
                
                weeks = sorted(df_filtered['SEMANA'].unique())
                week_options = [
                    {'value': str(week), 'label': f'{week}'} 
                    for week in weeks
                ]
                
                return week_options, None
                
            except (ValueError, TypeError):
                return [], None
        
        # Callback para cargar datos de API
        @callback(
            Output(self.ids['parquet_data_store'], 'data'),
            Input(self.ids['year_select'], 'id'),
            prevent_initial_call=False,
            running=[(Output(self.ids['year_select'], "disabled"), True, False),
                     (Output(self.ids['month_select'], "disabled"), True, False),
                     (Output(self.ids['week_select'], "disabled"), True, False)]
        )
        async def load_api_data_once(_):
            """Carga los datos de la API de forma asíncrona una sola vez"""
            try:
                print(f"🔄 [{self.page_id}] Cargando datos de la API...")
                
                access_token = await asyncio.to_thread(get_access_token)
                print(f"✅ [{self.page_id}] Token de acceso obtenido")
                
                data = await asyncio.to_thread(
                    listar_archivos_en_carpeta_compartida,
                    access_token=access_token,
                    drive_id=DRIVE_ID_CARPETA_STORAGE,
                    item_id=FOLDER_ID_CARPETA_STORAGE
                )
                print(f"✅ [{self.page_id}] Lista de archivos obtenida")
                
                url = get_download_url_by_name(data, "MAYOR ANALITICO PACKING.parquet")
                
                if url:
                    print(f"📁 [{self.page_id}] URL del archivo: {url[:50]}...")
                    df = await asyncio.to_thread(pd.read_parquet, url)
                else:
                    print(f"❌ [{self.page_id}] No se encontró la URL del archivo")
                    raise Exception("No se pudo obtener la URL del archivo OCUPACION TRANSPORTE.parquet")
                print(f"📊 [{self.page_id}] DataFrame cargado: {len(df)} registros")
                
                df["YEAR"] = df["FECHA"].dt.year
                df["MES"] = df["FECHA"].dt.month
                df["SEMANA"] = df["FECHA"].dt.isocalendar().week
                
                print(f"✅ [{self.page_id}] Datos procesados y listos para caché")
                return df.to_dict('records')
                
            except Exception as e:
                print(f"❌ [{self.page_id}] Error cargando datos de la API: {e}")
                return []
        
        # Callback para actualizar gráfico
        """
        @callback(
            Output(self.ids['graph_container'], 'figure'),
            [Input(self.ids['year_select'], 'value'),
             Input(self.ids['month_select'], 'value'),
             Input(self.ids['week_select'], 'value'),
             Input(self.ids['parquet_data_store'], 'data')],
            prevent_initial_call=True
        )
        def update_graph(selected_year, selected_month, selected_week, cached_data):
            
            
            if not cached_data:
                return go.Figure().add_annotation(
                    text="No hay datos disponibles",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
            
            try:
                df = pd.DataFrame(cached_data)
                
                # Preparar valores para filtro - con validación robusta
                filter_values = []
                filter_columns = []
                
                if selected_year and selected_year != "":
                    try:
                        filter_values.append(int(selected_year))
                        filter_columns.append('YEAR')
                    except (ValueError, TypeError):
                        print(f"⚠️ [{self.page_id}] Valor de año inválido: {selected_year}")
                        
                if selected_month and selected_month != "":
                    try:
                        filter_values.append(int(selected_month))
                        filter_columns.append('MES')
                    except (ValueError, TypeError):
                        print(f"⚠️ [{self.page_id}] Valor de mes inválido: {selected_month}")
                        
                if selected_week and selected_week != "":
                    try:
                        if isinstance(selected_week, list):
                            week_values = [int(w) for w in selected_week if w is not None and w != ""]
                        else:
                            week_values = [int(selected_week)]
                        
                        if week_values:  # Solo agregar si hay valores válidos
                            filter_values.append(week_values)
                            filter_columns.append('SEMANA')
                    except (ValueError, TypeError):
                        print(f"⚠️ [{self.page_id}] Valores de semana inválidos: {selected_week}")
                
                # Aplicar filtros si existen
                query = dataframe_filtro(values=filter_values, columns_df=filter_columns)
                if query:
                    df_filtered = df.query(query)
                else:
                    df_filtered = df
                    
                print(f"[{self.page_id}] Filtros aplicados: {query}")
                print(f"[{self.page_id}] Datos filtrados: {len(df_filtered)} registros")
                
                # Generar gráfico
                if len(df_filtered) > 0:
                    
                    dff = df_filtered.groupby(['SEMANA']).agg({'N° ASIENTOS OCUPADOS': 'sum'}).reset_index()
                    fig = px.line(dff, x='SEMANA', y='N° ASIENTOS OCUPADOS', 
                                title=self.chart_title,height=350,width=400)
                else:
                    fig = go.Figure().add_annotation(
                        text="No hay datos para los filtros seleccionados",
                        xref="paper", yref="paper",
                        x=0.5, y=0.5, showarrow=False
                    )
                    
                return fig
                
            except Exception as e:
                print(f"[{self.page_id}] Error generando gráfico: {e}")
                return go.Figure().add_annotation(
                    text="Error generando el gráfico",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5, showarrow=False
                )
"""