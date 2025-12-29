"""
Sistema de gestión de sesiones con Redis para aislamiento por empresa
"""
import redis
import json
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
from flask import request
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class SessionData:
    """Estructura de datos de sesión"""
    user_id: int
    username: str
    email: str
    company_id: int
    company_name: str
    role: str
    is_admin: bool
    full_name: str
    ip_address: str
    user_agent: str
    created_at: str
    last_activity: str
    expires_at: str

class RedisSessionManager:
    """Manejador de sesiones con Redis"""
    
    def __init__(self, redis_host: str = 'redis-cache', redis_port: int = 6379, 
                 redis_db: int = 0, session_timeout: int = 28800):  # 8 horas por defecto
        """
        Inicializar el manejador de sesiones
        
        Args:
            redis_host: Host de Redis
            redis_port: Puerto de Redis
            redis_db: Base de datos de Redis
            session_timeout: Timeout de sesión en segundos (8 horas por defecto)
        """
        self.redis_client = redis.Redis(
            host=redis_host, 
            port=redis_port, 
            db=redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        self.session_timeout = session_timeout
        self.session_prefix = "session:"
        self.user_sessions_prefix = "user_sessions:"
        self.company_data_prefix = "company_data:"
        
        # Verificar conexión a Redis
        try:
            self.redis_client.ping()
            logger.info("Conexión a Redis establecida correctamente")
        except redis.ConnectionError as e:
            logger.error(f"Error conectando a Redis: {e}")
            raise e
    
    def generate_session_id(self) -> str:
        """Generar un ID de sesión único y seguro"""
        return f"{uuid.uuid4().hex}_{secrets.token_hex(16)}"
    
    def create_session(self, user_data: Dict[str, Any]) -> str:
        """
        Crear una nueva sesión de usuario
        
        Args:
            user_data: Datos del usuario autenticado
            
        Returns:
            session_id: ID de la sesión creada
        """
        session_id = self.generate_session_id()
        
        # Obtener información de la request
        ip_address = request.remote_addr if request else "unknown"
        user_agent = request.headers.get('User-Agent', 'unknown') if request else "unknown"
        
        now = datetime.utcnow()
        expires_at = now + timedelta(seconds=self.session_timeout)
        
        session_data = SessionData(
            user_id=user_data['user_id'],
            username=user_data['username'],
            email=user_data['email'],
            company_id=user_data['company_id'],
            company_name=user_data.get('company_name', ''),
            role=user_data.get('role', 'invitado'),
            is_admin=user_data.get('is_admin', False),
            full_name=user_data.get('full_name', ''),
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=now.isoformat(),
            last_activity=now.isoformat(),
            expires_at=expires_at.isoformat()
        )
        
        # Guardar sesión en Redis
        session_key = f"{self.session_prefix}{session_id}"
        self.redis_client.setex(
            session_key,
            self.session_timeout,
            json.dumps(asdict(session_data))
        )
        
        # Mantener lista de sesiones del usuario
        user_sessions_key = f"{self.user_sessions_prefix}{user_data['user_id']}"
        self.redis_client.sadd(user_sessions_key, session_id)
        self.redis_client.expire(user_sessions_key, self.session_timeout)
        
        logger.info(f"Sesión creada: {session_id} para usuario {user_data['username']} de empresa {user_data['company_id']}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[SessionData]:
        """
        Obtener datos de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            SessionData o None si no existe o expiró
        """
        session_key = f"{self.session_prefix}{session_id}"
        session_json = self.redis_client.get(session_key)
        
        if not session_json:
            return None
        
        try:
            session_dict = json.loads(session_json)
            return SessionData(**session_dict)
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error deserializando sesión {session_id}: {e}")
            return None
    
    def update_session_activity(self, session_id: str) -> bool:
        """
        Actualizar la última actividad de una sesión
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            True si se actualizó correctamente
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Actualizar última actividad
        session_data.last_activity = datetime.utcnow().isoformat()
        
        # Guardar de nuevo con TTL renovado
        session_key = f"{self.session_prefix}{session_id}"
        self.redis_client.setex(
            session_key,
            self.session_timeout,
            json.dumps(asdict(session_data))
        )
        
        return True
    
    def invalidate_session(self, session_id: str) -> bool:
        """
        Invalidar una sesión específica
        
        Args:
            session_id: ID de la sesión
            
        Returns:
            True si se invalidó correctamente
        """
        session_data = self.get_session(session_id)
        if not session_data:
            return False
        
        # Eliminar sesión
        session_key = f"{self.session_prefix}{session_id}"
        self.redis_client.delete(session_key)
        
        # Eliminar de la lista de sesiones del usuario
        user_sessions_key = f"{self.user_sessions_prefix}{session_data.user_id}"
        self.redis_client.srem(user_sessions_key, session_id)
        
        logger.info(f"Sesión invalidada: {session_id}")
        return True
    
    def invalidate_user_sessions(self, user_id: int) -> int:
        """
        Invalidar todas las sesiones de un usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Número de sesiones invalidadas
        """
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        session_ids = self.redis_client.smembers(user_sessions_key)
        
        invalidated_count = 0
        for session_id in session_ids:
            if self.invalidate_session(session_id):
                invalidated_count += 1
        
        # Limpiar la lista de sesiones del usuario
        self.redis_client.delete(user_sessions_key)
        
        logger.info(f"Invalidadas {invalidated_count} sesiones del usuario {user_id}")
        return invalidated_count
    
    def get_user_sessions(self, user_id: int) -> list:
        """
        Obtener todas las sesiones activas de un usuario
        
        Args:
            user_id: ID del usuario
            
        Returns:
            Lista de SessionData
        """
        user_sessions_key = f"{self.user_sessions_prefix}{user_id}"
        session_ids = self.redis_client.smembers(user_sessions_key)
        
        sessions = []
        for session_id in session_ids:
            session_data = self.get_session(session_id)
            if session_data:
                sessions.append(session_data)
            else:
                # Limpiar sesión inválida de la lista
                self.redis_client.srem(user_sessions_key, session_id)
        
        return sessions
    
    def cache_company_data(self, company_id: int, data: Dict[str, Any], ttl: int = 3600) -> bool:
        """
        Cache de datos específicos de empresa
        
        Args:
            company_id: ID de la empresa
            data: Datos a cachear
            ttl: Tiempo de vida en segundos (1 hora por defecto)
            
        Returns:
            True si se cacheó correctamente
        """
        cache_key = f"{self.company_data_prefix}{company_id}"
        
        try:
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(data, default=str)  # default=str para manejar datetime
            )
            logger.info(f"Datos de empresa {company_id} cacheados por {ttl} segundos")
            return True
        except Exception as e:
            logger.error(f"Error cacheando datos de empresa {company_id}: {e}")
            return False
    
    def get_company_data(self, company_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtener datos cacheados de una empresa
        
        Args:
            company_id: ID de la empresa
            
        Returns:
            Datos de la empresa o None si no están cacheados
        """
        cache_key = f"{self.company_data_prefix}{company_id}"
        cached_data = self.redis_client.get(cache_key)
        
        if not cached_data:
            return None
        
        try:
            return json.loads(cached_data)
        except json.JSONDecodeError as e:
            logger.error(f"Error deserializando datos de empresa {company_id}: {e}")
            return None
    
    def invalidate_company_cache(self, company_id: int) -> bool:
        """
        Invalidar cache de datos de una empresa
        
        Args:
            company_id: ID de la empresa
            
        Returns:
            True si se invalidó correctamente
        """
        cache_key = f"{self.company_data_prefix}{company_id}"
        deleted = self.redis_client.delete(cache_key)
        
        if deleted:
            logger.info(f"Cache de empresa {company_id} invalidado")
        
        return bool(deleted)
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Obtener estadísticas de sesiones
        
        Returns:
            Diccionario con estadísticas
        """
        # Contar sesiones activas
        session_keys = self.redis_client.keys(f"{self.session_prefix}*")
        active_sessions = len(session_keys)
        
        # Contar usuarios únicos con sesiones
        user_session_keys = self.redis_client.keys(f"{self.user_sessions_prefix}*")
        unique_users = len(user_session_keys)
        
        # Contar empresas con datos cacheados
        company_cache_keys = self.redis_client.keys(f"{self.company_data_prefix}*")
        cached_companies = len(company_cache_keys)
        
        return {
            "active_sessions": active_sessions,
            "unique_users_with_sessions": unique_users,
            "cached_companies": cached_companies,
            "redis_memory_usage": self.redis_client.info()['used_memory_human'],
            "redis_connected_clients": self.redis_client.info()['connected_clients']
        }
    
    def cleanup_expired_sessions(self) -> int:
        """
        Limpiar sesiones expiradas (método de mantenimiento)
        
        Returns:
            Número de sesiones limpiadas
        """
        session_keys = self.redis_client.keys(f"{self.session_prefix}*")
        cleaned_count = 0
        
        for session_key in session_keys:
            session_json = self.redis_client.get(session_key)
            if not session_json:
                continue
            
            try:
                session_dict = json.loads(session_json)
                expires_at = datetime.fromisoformat(session_dict['expires_at'])
                
                if datetime.utcnow() > expires_at:
                    session_id = session_key.replace(self.session_prefix, '')
                    if self.invalidate_session(session_id):
                        cleaned_count += 1
                        
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"Error procesando sesión {session_key}: {e}")
                # Eliminar sesión corrupta
                self.redis_client.delete(session_key)
                cleaned_count += 1
        
        if cleaned_count > 0:
            logger.info(f"Limpiadas {cleaned_count} sesiones expiradas")
        
        return cleaned_count

# Instancia global del manejador de sesiones
session_manager = None

def get_session_manager() -> RedisSessionManager:
    """Obtener la instancia del manejador de sesiones"""
    global session_manager
    if session_manager is None:
        # Configuración por defecto - se puede sobrescribir con variables de entorno
        session_manager = RedisSessionManager()
    return session_manager

def init_session_manager(redis_host: str = 'redis-cache', redis_port: int = 6379, 
                        redis_db: int = 0, session_timeout: int = 28800):
    """Inicializar el manejador de sesiones con configuración específica"""
    global session_manager
    session_manager = RedisSessionManager(redis_host, redis_port, redis_db, session_timeout)
    return session_manager
