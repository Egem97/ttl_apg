"""
Sistema de caching avanzado con Redis para APG BI Dashboard
"""
import redis
import json
import pickle
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict, List, Callable
from functools import wraps
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CacheManager:
    """Manejador avanzado de cache con Redis"""
    
    def __init__(self, redis_host: str = 'redis-cache', redis_port: int = 6379, 
                 redis_db: int = 1, default_ttl: int = 3600):  # DB 1 para cache, DB 0 para sesiones
        """
        Inicializar el manejador de cache
        
        Args:
            redis_host: Host de Redis
            redis_port: Puerto de Redis
            redis_db: Base de datos de Redis para cache
            default_ttl: TTL por defecto en segundos (1 hora)
        """
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=redis_db,
            decode_responses=False,  # Para poder manejar datos binarios
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self.default_ttl = default_ttl
        
        # Prefijos para diferentes tipos de cache
        self.prefixes = {
            'data': 'data:',
            'query': 'query:',
            'user': 'user:',
            'company': 'company:',
            'dashboard': 'dashboard:',
            'report': 'report:',
            'api': 'api:'
        }
        
        # Verificar conexión
        try:
            self.redis_client.ping()
            logger.info("Conexión a Redis Cache establecida correctamente")
        except redis.ConnectionError as e:
            logger.error(f"Error conectando a Redis Cache: {e}")
            raise e
    
    def _generate_key(self, prefix: str, identifier: str, company_id: int = None) -> str:
        """Generar clave de cache con aislamiento por empresa"""
        if company_id:
            return f"{self.prefixes[prefix]}company_{company_id}:{identifier}"
        return f"{self.prefixes[prefix]}{identifier}"
    
    def _serialize_data(self, data: Any) -> bytes:
        """Serializar datos para almacenamiento"""
        try:
            # Intentar JSON primero (más rápido y legible)
            if isinstance(data, (dict, list, str, int, float, bool)) or data is None:
                return json.dumps(data, default=str).encode('utf-8')
            else:
                # Usar pickle para objetos complejos
                return pickle.dumps(data)
        except (TypeError, ValueError):
            # Fallback a pickle
            return pickle.dumps(data)
    
    def _deserialize_data(self, data: bytes) -> Any:
        """Deserializar datos del cache"""
        try:
            # Intentar JSON primero
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Usar pickle
            return pickle.loads(data)
    
    def set(self, key: str, data: Any, ttl: int = None, prefix: str = 'data', 
            company_id: int = None) -> bool:
        """
        Almacenar datos en cache
        
        Args:
            key: Clave identificadora
            data: Datos a almacenar
            ttl: Tiempo de vida en segundos
            prefix: Prefijo del tipo de cache
            company_id: ID de empresa para aislamiento
            
        Returns:
            True si se almacenó correctamente
        """
        try:
            cache_key = self._generate_key(prefix, key, company_id)
            serialized_data = self._serialize_data(data)
            ttl = ttl or self.default_ttl
            
            result = self.redis_client.setex(cache_key, ttl, serialized_data)
            
            if result:
                logger.debug(f"Datos cacheados: {cache_key} (TTL: {ttl}s)")
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error almacenando en cache {key}: {e}")
            return False
    
    def get(self, key: str, prefix: str = 'data', company_id: int = None) -> Optional[Any]:
        """
        Obtener datos del cache
        
        Args:
            key: Clave identificadora
            prefix: Prefijo del tipo de cache
            company_id: ID de empresa para aislamiento
            
        Returns:
            Datos cacheados o None si no existen
        """
        try:
            cache_key = self._generate_key(prefix, key, company_id)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data is None:
                return None
            
            return self._deserialize_data(cached_data)
            
        except Exception as e:
            logger.error(f"Error obteniendo del cache {key}: {e}")
            return None
    
    def delete(self, key: str, prefix: str = 'data', company_id: int = None) -> bool:
        """Eliminar datos del cache"""
        try:
            cache_key = self._generate_key(prefix, key, company_id)
            result = self.redis_client.delete(cache_key)
            
            if result:
                logger.debug(f"Cache eliminado: {cache_key}")
            
            return bool(result)
            
        except Exception as e:
            logger.error(f"Error eliminando cache {key}: {e}")
            return False
    
    def exists(self, key: str, prefix: str = 'data', company_id: int = None) -> bool:
        """Verificar si una clave existe en cache"""
        try:
            cache_key = self._generate_key(prefix, key, company_id)
            return bool(self.redis_client.exists(cache_key))
        except Exception as e:
            logger.error(f"Error verificando existencia de cache {key}: {e}")
            return False
    
    def get_ttl(self, key: str, prefix: str = 'data', company_id: int = None) -> int:
        """Obtener el TTL restante de una clave"""
        try:
            cache_key = self._generate_key(prefix, key, company_id)
            return self.redis_client.ttl(cache_key)
        except Exception as e:
            logger.error(f"Error obteniendo TTL de cache {key}: {e}")
            return -1
    
    def extend_ttl(self, key: str, additional_seconds: int, prefix: str = 'data', 
                   company_id: int = None) -> bool:
        """Extender el TTL de una clave"""
        try:
            cache_key = self._generate_key(prefix, key, company_id)
            current_ttl = self.redis_client.ttl(cache_key)
            
            if current_ttl > 0:
                new_ttl = current_ttl + additional_seconds
                result = self.redis_client.expire(cache_key, new_ttl)
                return bool(result)
            
            return False
            
        except Exception as e:
            logger.error(f"Error extendiendo TTL de cache {key}: {e}")
            return False
    
    def invalidate_pattern(self, pattern: str, prefix: str = 'data', 
                          company_id: int = None) -> int:
        """
        Invalidar múltiples claves que coincidan con un patrón
        
        Args:
            pattern: Patrón de búsqueda (ej: "user_*", "report_2024*")
            prefix: Prefijo del tipo de cache
            company_id: ID de empresa para aislamiento
            
        Returns:
            Número de claves eliminadas
        """
        try:
            base_pattern = self._generate_key(prefix, pattern, company_id)
            keys = self.redis_client.keys(base_pattern)
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidadas {deleted} claves con patrón: {base_pattern}")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidando patrón {pattern}: {e}")
            return 0
    
    def invalidate_company_cache(self, company_id: int) -> int:
        """Invalidar todo el cache de una empresa específica"""
        try:
            pattern = f"*company_{company_id}:*"
            keys = self.redis_client.keys(pattern)
            
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.info(f"Invalidado cache completo de empresa {company_id}: {deleted} claves")
                return deleted
            
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidando cache de empresa {company_id}: {e}")
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache"""
        try:
            info = self.redis_client.info()
            
            # Contar claves por prefijo
            prefix_counts = {}
            for prefix_name, prefix_value in self.prefixes.items():
                keys = self.redis_client.keys(f"{prefix_value}*")
                prefix_counts[prefix_name] = len(keys)
            
            return {
                'total_keys': info.get('db1', {}).get('keys', 0),
                'memory_usage': info.get('used_memory_human', '0B'),
                'hit_rate': self._calculate_hit_rate(),
                'prefix_counts': prefix_counts,
                'connected_clients': info.get('connected_clients', 0)
            }
            
        except Exception as e:
            logger.error(f"Error obteniendo estadísticas de cache: {e}")
            return {}
    
    def _calculate_hit_rate(self) -> float:
        """Calcular tasa de aciertos del cache"""
        try:
            info = self.redis_client.info()
            hits = info.get('keyspace_hits', 0)
            misses = info.get('keyspace_misses', 0)
            
            if hits + misses == 0:
                return 0.0
            
            return round((hits / (hits + misses)) * 100, 2)
            
        except Exception:
            return 0.0

# Decoradores para caching automático

def cache_result(ttl: int = 3600, prefix: str = 'data', key_generator: Callable = None):
    """
    Decorator para cachear resultados de funciones automáticamente
    
    Args:
        ttl: Tiempo de vida del cache
        prefix: Prefijo del tipo de cache
        key_generator: Función personalizada para generar la clave
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Obtener company_id del contexto si está disponible
            company_id = kwargs.get('company_id')
            
            # Generar clave de cache
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                # Generar clave basada en nombre de función y argumentos
                args_str = str(args) + str(sorted(kwargs.items()))
                cache_key = f"{func.__name__}_{hashlib.md5(args_str.encode()).hexdigest()}"
            
            # Intentar obtener del cache
            cache_manager = get_cache_manager()
            cached_result = cache_manager.get(cache_key, prefix, company_id)
            
            if cached_result is not None:
                logger.debug(f"Cache hit para {func.__name__}: {cache_key}")
                return cached_result
            
            # Ejecutar función y cachear resultado
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl, prefix, company_id)
            logger.debug(f"Resultado cacheado para {func.__name__}: {cache_key}")
            
            return result
        
        return wrapper
    return decorator

def invalidate_cache_on_change(patterns: List[str], prefix: str = 'data'):
    """
    Decorator para invalidar cache automáticamente cuando se modifica data
    
    Args:
        patterns: Lista de patrones de cache a invalidar
        prefix: Prefijo del tipo de cache
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = func(*args, **kwargs)
            
            # Invalidar cache después de la operación exitosa
            company_id = kwargs.get('company_id')
            cache_manager = get_cache_manager()
            
            for pattern in patterns:
                cache_manager.invalidate_pattern(pattern, prefix, company_id)
            
            return result
        
        return wrapper
    return decorator

# Instancia global del manejador de cache
cache_manager = None

def get_cache_manager() -> CacheManager:
    """Obtener la instancia del manejador de cache"""
    global cache_manager
    if cache_manager is None:
        cache_manager = CacheManager()
    return cache_manager

def init_cache_manager(redis_host: str = 'redis-cache', redis_port: int = 6379,
                      redis_db: int = 1, default_ttl: int = 3600):
    """Inicializar el manejador de cache con configuración específica"""
    global cache_manager
    cache_manager = CacheManager(redis_host, redis_port, redis_db, default_ttl)
    return cache_manager
