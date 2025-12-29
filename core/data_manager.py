"""
DataManager - Capa centralizada para gestión de datos
Maneja todas las fuentes de datos y caché de forma centralizada
"""
import asyncio
import pandas as pd
from typing import Dict, Optional, Any, List
from dash import dcc
from helpers.get_token import get_access_token
from helpers.get_api import listar_archivos_en_carpeta_compartida
from helpers.helpers import get_download_url_by_name, generate_list_month, dataframe_filtro
from constants import DRIVE_ID_CARPETA_STORAGE, FOLDER_ID_CARPETA_STORAGE


class DataSource:
    """Representa una fuente de datos específica"""
    
    def __init__(self, name: str, file_name: str, cache_key: str, processor=None):
        self.name = name
        self.file_name = file_name
        self.cache_key = cache_key
        self.processor = processor or self._default_processor
    
    def _default_processor(self, df: pd.DataFrame) -> pd.DataFrame:
        """Procesamiento por defecto para DataFrames"""
        if 'FECHA' in df.columns:
            df["YEAR"] = df["FECHA"].dt.year
            df["MES"] = df["FECHA"].dt.month
            df["SEMANA"] = df["FECHA"].dt.isocalendar().week
        return df


class DataManager:
    """
    Gestor centralizado de datos que maneja múltiples fuentes
    y proporciona caché compartido entre dashboards
    """
    
    def __init__(self):
        self.data_sources = {}
        self.cache_stores = {}
        self._register_default_sources()
    
    def _register_default_sources(self):
        """Registra las fuentes de datos por defecto"""
        self.register_source(
            "ocupacion_transporte", 
            "OCUPACION TRANSPORTE.parquet", 
            "ocupacion-data-store"
        )
        
        self.register_source(
            "mayor_analitico_packing", 
            "MAYOR ANALITICO PACKING.parquet", 
            "packing-data-store"
        )
        
        self.register_source(
            "date_options",
            None,  # No es un archivo, se genera
            "date-options-store",
            self._generate_date_options
        )
    
    def register_source(self, name: str, file_name: str, cache_key: str, processor=None):
        """Registra una nueva fuente de datos"""
        self.data_sources[name] = DataSource(name, file_name, cache_key, processor)
        
    def get_cache_stores(self, dashboard_id: str) -> List[dcc.Store]:
        """Genera los stores de caché necesarios para un dashboard"""
        stores = []
        for source_name, source in self.data_sources.items():
            store_id = f"{dashboard_id}-{source.cache_key}"
            stores.append(dcc.Store(id=store_id, storage_type='session'))
            self.cache_stores[store_id] = source_name
        return stores
    
    async def load_data_source(self, source_name: str) -> Dict[str, Any]:
        """Carga una fuente de datos específica"""
        if source_name not in self.data_sources:
            raise ValueError(f"Fuente de datos '{source_name}' no encontrada")
        
        source = self.data_sources[source_name]
        
        try:
            print(f"🔄 Cargando fuente: {source.name}")
            
            if source.file_name is None:
                # Fuente de datos generada (como opciones de fecha)
                data = await asyncio.to_thread(source.processor)
            else:
                # Fuente de datos desde archivo
                access_token = await asyncio.to_thread(get_access_token)
                files_data = await asyncio.to_thread(
                    listar_archivos_en_carpeta_compartida,
                    access_token=access_token,
                    drive_id=DRIVE_ID_CARPETA_STORAGE,
                    item_id=FOLDER_ID_CARPETA_STORAGE
                )
                
                url = get_download_url_by_name(files_data, source.file_name)
                if not url:
                    raise Exception(f"No se encontró el archivo: {source.file_name}")
                
                df = await asyncio.to_thread(pd.read_parquet, url)
                df = source.processor(df)
                data = df.to_dict('records')
            
            print(f"✅ Fuente '{source.name}' cargada exitosamente")
            return {"success": True, "data": data, "error": None}
            
        except Exception as e:
            print(f"❌ Error cargando fuente '{source.name}': {e}")
            return {"success": False, "data": [], "error": str(e)}
    
    def _generate_date_options(self) -> Dict[str, Any]:
        """Genera opciones de fecha para filtros"""
        df = generate_list_month(2024, 8)
        
        # Generar opciones para selectores
        years = sorted(df['YEAR'].unique())
        year_options = [{'value': str(year), 'label': str(year)} for year in years]
        
        months_data = df[['MES', 'MES_TEXT']].drop_duplicates().sort_values('MES')
        month_options = [
            {'value': str(row['MES']), 'label': row['MES_TEXT']} 
            for _, row in months_data.iterrows()
        ]
        
        weeks = sorted(df['SEMANA'].unique())
        week_options = [{'value': str(week), 'label': f'Semana {week}'} for week in weeks]
        
        return {
            'years': year_options,
            'months': month_options, 
            'weeks': week_options,
            'default_year': str(years[-1]) if years else None
        }
    
    def apply_filters(self, data: List[Dict], filters: Dict[str, Any]) -> pd.DataFrame:
        """Aplica filtros a los datos"""
        if not data:
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        
        # Preparar valores para filtro
        filter_values = []
        filter_columns = []
        
        for filter_name, filter_value in filters.items():
            if filter_value and filter_value != "":
                if filter_name == 'year':
                    filter_values.append(int(filter_value))
                    filter_columns.append('YEAR')
                elif filter_name == 'month':
                    filter_values.append(int(filter_value))
                    filter_columns.append('MES')
                elif filter_name == 'week':
                    if isinstance(filter_value, list):
                        week_values = [int(w) for w in filter_value if w]
                    else:
                        week_values = [int(filter_value)]
                    if week_values:
                        filter_values.append(week_values)
                        filter_columns.append('SEMANA')
        
        # Aplicar filtros
        query = dataframe_filtro(values=filter_values, columns_df=filter_columns)
        if query:
            df = df.query(query)
        
        return df


# Instancia global del DataManager
data_manager = DataManager()