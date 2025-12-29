"""
Data Manager - Manejador centralizado de fuentes de datos
Maneja la carga async de datos y caching
"""
import asyncio
import pandas as pd
from typing import Dict, Any, Optional, List
from helpers.helpers import get_download_url_by_name
from helpers.helpers import dataframe_filtro


class DataManager:
    """Manejador centralizado de todas las fuentes de datos"""
    
    def __init__(self):
        self._cache = {}
        self._loading = {}  # Para evitar cargas duplicadas
    
    async def get_data(self, source_name: str, force_reload: bool = False) -> Optional[pd.DataFrame]:
        """
        Obtiene datos de una fuente específica
        
        Args:
            source_name: Nombre de la fuente de datos
            force_reload: Forzar recarga desde API
            
        Returns:
            DataFrame con los datos o None si hay error
        """
        cache_key = f"data_{source_name}"
        
        # Si está en cache y no forzamos reload
        if not force_reload and cache_key in self._cache:
            print(f"📊 Datos de {source_name} obtenidos desde cache")
            return self._cache[cache_key]
        
        # Si ya se está cargando, esperar
        if source_name in self._loading:
            print(f"⏳ Esperando carga de {source_name}...")
            return await self._loading[source_name]
        
        # Crear tarea de carga
        self._loading[source_name] = self._load_data_async(source_name)
        
        try:
            data = await self._loading[source_name]
            self._cache[cache_key] = data
            return data
        finally:
            # Limpiar tarea de carga
            if source_name in self._loading:
                del self._loading[source_name]
    
    async def _load_data_async(self, source_name: str) -> Optional[pd.DataFrame]:
        """Carga datos de forma asíncrona"""
        try:
            print(f"🌐 Cargando datos de {source_name}...")
            
            # Usar asyncio.to_thread para operaciones I/O
            url = await asyncio.to_thread(get_download_url_by_name, source_name)
            
            if not url:
                print(f"❌ No se pudo obtener URL para {source_name}")
                return None
            
            # Cargar DataFrame de forma asíncrona
            df = await asyncio.to_thread(pd.read_parquet, url)
            print(f"✅ Datos de {source_name} cargados: {len(df)} registros")
            return df
            
        except Exception as e:
            print(f"❌ Error cargando {source_name}: {e}")
            return None
    
    async def get_filtered_data(self, source_name: str, filters: Dict[str, Any]) -> Optional[pd.DataFrame]:
        """
        Obtiene datos filtrados de una fuente
        
        Args:
            source_name: Nombre de la fuente
            filters: Diccionario con filtros {column: value}
            
        Returns:
            DataFrame filtrado
        """
        df = await self.get_data(source_name)
        if df is None or df.empty:
            return None
        
        try:
            # Aplicar filtros usando dataframe_filtro
            filter_values = []
            filter_columns = []
            
            for column, value in filters.items():
                if value is not None and value != []:
                    filter_values.append(value)
                    filter_columns.append(column)
            
            if filter_values:
                query = dataframe_filtro(filter_values, filter_columns)
                if query:
                    df_filtered = df.query(query)
                    print(f"🔍 Filtros aplicados a {source_name}: {len(df_filtered)} registros")
                    return df_filtered
            
            return df
            
        except Exception as e:
            print(f"❌ Error aplicando filtros a {source_name}: {e}")
            return df
    
    async def get_date_options(self, source_name: str) -> Dict[str, List]:
        """Obtiene opciones de fechas de una fuente de datos"""
        df = await self.get_data(source_name)
        if df is None or df.empty:
            return {'years': [], 'months': [], 'weeks': []}
        
        try:
            options = {
                'years': [],
                'months': [],
                'weeks': []
            }
            
            if 'AÑO' in df.columns:
                options['years'] = sorted(df['AÑO'].unique().tolist())
            
            if 'MES' in df.columns:
                months = df['MES'].unique()
                options['months'] = [
                    {'label': month, 'value': month} 
                    for month in sorted(months) if pd.notna(month)
                ]
            
            if 'SEMANA' in df.columns:
                weeks = df['SEMANA'].unique()
                options['weeks'] = [
                    {'label': f'Semana {week}', 'value': str(week)}
                    for week in sorted(weeks) if pd.notna(week)
                ]
            
            return options
            
        except Exception as e:
            print(f"❌ Error obteniendo opciones de fecha: {e}")
            return {'years': [], 'months': [], 'weeks': []}
    
    def clear_cache(self, source_name: str = None):
        """Limpia el cache de datos"""
        if source_name:
            cache_key = f"data_{source_name}"
            if cache_key in self._cache:
                del self._cache[cache_key]
                print(f"🗑️ Cache de {source_name} limpiado")
        else:
            self._cache.clear()
            print("🗑️ Todo el cache limpiado")


# Instancia global del manejador de datos
data_manager = DataManager()