"""
Middleware de autenticación y autorización con gestión de sesiones por empresa
"""
import asyncio
from functools import wraps
from flask import request, jsonify, g
from typing import Optional, Dict, Any, List
import logging

from models import (
    DatabaseManager, get_user_session as get_db_user_session,
    check_user_permission, UserRole
)
from core.session_manager import get_session_manager, SessionData

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AuthMiddleware:
    """Middleware de autenticación y autorización"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session_manager = get_session_manager()
    
    def extract_session_id(self) -> Optional[str]:
        """Extraer session_id del header Authorization o cookie"""
        # Intentar obtener del header Authorization
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        
        # Intentar obtener de cookies
        session_id = request.cookies.get('session_id')
        if session_id:
            return session_id
        
        return None
    
    def get_current_session(self) -> Optional[SessionData]:
        """Obtener la sesión actual del usuario"""
        session_id = self.extract_session_id()
        if not session_id:
            return None
        
        # Obtener sesión de Redis
        session_data = self.session_manager.get_session(session_id)
        if session_data:
            # Actualizar última actividad
            self.session_manager.update_session_activity(session_id)
            
            # Guardar en contexto de Flask para uso en la aplicación
            g.current_session = session_data
            g.current_user_id = session_data.user_id
            g.current_company_id = session_data.company_id
            g.current_user_role = session_data.role
            g.is_admin = session_data.is_admin
            
            return session_data
        
        return None
    
    def require_auth(self, f):
        """Decorator que requiere autenticación"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_data = self.get_current_session()
            
            if not session_data:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Sesión no válida o expirada'
                }), 401
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    def require_role(self, required_roles: List[str]):
        """Decorator que requiere roles específicos"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                session_data = self.get_current_session()
                
                if not session_data:
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'Sesión no válida o expirada'
                    }), 401
                
                # Verificar rol
                if session_data.role not in required_roles and not session_data.is_admin:
                    return jsonify({
                        'error': 'Insufficient permissions',
                        'message': f'Rol requerido: {", ".join(required_roles)}',
                        'current_role': session_data.role
                    }), 403
                
                return f(*args, **kwargs)
            
            return decorated_function
        return decorator
    
    def require_permission(self, module: str, action: str):
        """Decorator que requiere permisos específicos"""
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                session_data = self.get_current_session()
                
                if not session_data:
                    return jsonify({
                        'error': 'Authentication required',
                        'message': 'Sesión no válida o expirada'
                    }), 401
                
                # Los administradores tienen todos los permisos
                if session_data.is_admin:
                    return f(*args, **kwargs)
                
                # Verificar permiso específico
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    async def check_permission():
                        async with self.db_manager.get_session() as db_session:
                            return await check_user_permission(
                                db_session, 
                                session_data.user_id, 
                                session_data.company_id,
                                module, 
                                action
                            )
                    
                    has_permission = loop.run_until_complete(check_permission())
                    loop.close()
                    
                    if not has_permission:
                        return jsonify({
                            'error': 'Insufficient permissions',
                            'message': f'Permiso requerido: {module}.{action}',
                            'current_role': session_data.role
                        }), 403
                    
                    return f(*args, **kwargs)
                    
                except Exception as e:
                    logger.error(f"Error verificando permisos: {e}")
                    return jsonify({
                        'error': 'Permission check failed',
                        'message': 'Error interno verificando permisos'
                    }), 500
            
            return decorated_function
        return decorator
    
    def require_company_access(self, f):
        """Decorator que verifica acceso a la empresa actual"""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            session_data = self.get_current_session()
            
            if not session_data:
                return jsonify({
                    'error': 'Authentication required',
                    'message': 'Sesión no válida o expirada'
                }), 401
            
            # Verificar que el usuario tenga acceso a la empresa
            # (esto se puede extender para usuarios con acceso a múltiples empresas)
            company_id_param = request.args.get('company_id') or request.json.get('company_id') if request.json else None
            
            if company_id_param and int(company_id_param) != session_data.company_id and not session_data.is_admin:
                return jsonify({
                    'error': 'Company access denied',
                    'message': 'No tienes acceso a esta empresa',
                    'current_company': session_data.company_id,
                    'requested_company': company_id_param
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function

# Funciones helper para usar en callbacks de Dash

def get_current_user() -> Optional[Dict[str, Any]]:
    """Obtener información del usuario actual"""
    if hasattr(g, 'current_session'):
        session_data = g.current_session
        return {
            'user_id': session_data.user_id,
            'username': session_data.username,
            'email': session_data.email,
            'company_id': session_data.company_id,
            'company_name': session_data.company_name,
            'role': session_data.role,
            'is_admin': session_data.is_admin,
            'full_name': session_data.full_name
        }
    return None

def get_current_company_id() -> Optional[int]:
    """Obtener ID de la empresa actual"""
    return getattr(g, 'current_company_id', None)

def get_current_user_role() -> Optional[str]:
    """Obtener rol del usuario actual"""
    return getattr(g, 'current_user_role', None)

def is_current_user_admin() -> bool:
    """Verificar si el usuario actual es administrador"""
    return getattr(g, 'is_admin', False)

def check_current_user_permission(module: str, action: str) -> bool:
    """Verificar si el usuario actual tiene un permiso específico"""
    if not hasattr(g, 'current_session'):
        return False
    
    session_data = g.current_session
    
    # Los administradores tienen todos los permisos
    if session_data.is_admin:
        return True
    
    try:
        # Esto requiere acceso al DatabaseManager - se puede mejorar cacheando permisos
        from auth import db_manager
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def check():
            async with db_manager.get_session() as db_session:
                return await check_user_permission(
                    db_session, 
                    session_data.user_id, 
                    session_data.company_id,
                    module, 
                    action
                )
        
        result = loop.run_until_complete(check())
        loop.close()
        return result
        
    except Exception as e:
        logger.error(f"Error verificando permisos del usuario actual: {e}")
        return False

def require_session_for_callback(callback_func):
    """Decorator para callbacks de Dash que requieren sesión"""
    @wraps(callback_func)
    def wrapper(*args, **kwargs):
        # En Dash, necesitamos manejar esto de manera diferente
        # ya que no tenemos acceso directo a Flask request context
        
        # Por ahora, retornamos el callback original
        # En una implementación más avanzada, podríamos usar
        # dash.callback_context para obtener información de la sesión
        return callback_func(*args, **kwargs)
    
    return wrapper

# Instancia global del middleware
auth_middleware = None

def get_auth_middleware() -> AuthMiddleware:
    """Obtener la instancia del middleware de autenticación"""
    global auth_middleware
    if auth_middleware is None:
        from auth import db_manager
        auth_middleware = AuthMiddleware(db_manager)
    return auth_middleware

def init_auth_middleware(db_manager: DatabaseManager):
    """Inicializar el middleware de autenticación"""
    global auth_middleware
    auth_middleware = AuthMiddleware(db_manager)
    return auth_middleware
