#!/usr/bin/env python3
"""
Script de inicialización de base de datos para APG BI Dashboard
"""
import asyncio
import sys
import os

# Agregar el directorio padre al path para importar módulos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import (
    DatabaseManager, get_database_url, create_company, create_user_with_profile,
    create_permission, assign_role_permission, UserRole
)
from auth import db_manager
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def create_permissions():
    """Crear permisos básicos del sistema"""
    logger.info("Creando permisos básicos...")
    
    permissions_data = [
        # Permisos para módulo de costos
        ('costos.read', 'Ver datos de costos', 'costos', 'read'),
        ('costos.write', 'Editar datos de costos', 'costos', 'write'),
        ('costos.delete', 'Eliminar datos de costos', 'costos', 'delete'),
        ('costos.admin', 'Administrar módulo de costos', 'costos', 'admin'),
        
        # Permisos para módulo de producción
        ('produccion.read', 'Ver datos de producción', 'produccion', 'read'),
        ('produccion.write', 'Editar datos de producción', 'produccion', 'write'),
        ('produccion.delete', 'Eliminar datos de producción', 'produccion', 'delete'),
        ('produccion.admin', 'Administrar módulo de producción', 'produccion', 'admin'),
        
        # Permisos para módulo de ventas
        ('ventas.read', 'Ver datos de ventas', 'ventas', 'read'),
        ('ventas.write', 'Editar datos de ventas', 'ventas', 'write'),
        ('ventas.delete', 'Eliminar datos de ventas', 'ventas', 'delete'),
        ('ventas.admin', 'Administrar módulo de ventas', 'ventas', 'admin'),
        
        # Permisos para administración del sistema
        ('sistema.read', 'Ver configuración del sistema', 'sistema', 'read'),
        ('sistema.write', 'Editar configuración del sistema', 'sistema', 'write'),
        ('sistema.admin', 'Administrar sistema completo', 'sistema', 'admin'),
        ('usuarios.read', 'Ver usuarios', 'usuarios', 'read'),
        ('usuarios.write', 'Gestionar usuarios', 'usuarios', 'write'),
        ('usuarios.admin', 'Administrar usuarios', 'usuarios', 'admin'),
    ]
    
    created_permissions = {}
    
    async with db_manager.get_session() as session:
        for name, description, module, action in permissions_data:
            try:
                permission = await create_permission(session, name, description, module, action)
                created_permissions[name] = permission.id
                logger.info(f"Permiso creado: {name}")
            except Exception as e:
                logger.warning(f"Error creando permiso {name}: {e}")
    
    return created_permissions

async def assign_permissions_to_roles(permissions):
    """Asignar permisos a los roles"""
    logger.info("Asignando permisos a roles...")
    
    # Definir permisos por rol
    role_permissions = {
        UserRole.ADMIN: list(permissions.keys()),  # Todos los permisos
        UserRole.CONTADOR: [
            'costos.read', 'costos.write', 'produccion.read', 'produccion.write',
            'ventas.read', 'ventas.write', 'usuarios.read'
        ],
        UserRole.EMPRESA: [
            'costos.read', 'costos.write', 'produccion.read', 'produccion.write',
            'ventas.read', 'ventas.write', 'sistema.read'
        ],
        UserRole.INVITADO: [
            'costos.read', 'produccion.read', 'ventas.read'
        ]
    }
    
    async with db_manager.get_session() as session:
        for role, permission_names in role_permissions.items():
            for permission_name in permission_names:
                if permission_name in permissions:
                    try:
                        await assign_role_permission(
                            session, role, permissions[permission_name]
                        )
                        logger.info(f"Permiso {permission_name} asignado a rol {role.value}")
                    except Exception as e:
                        logger.warning(f"Error asignando permiso {permission_name} a {role.value}: {e}")

async def create_demo_company():
    """Crear empresa de demostración"""
    logger.info("Creando empresa de demostración...")
    
    async with db_manager.get_session() as session:
        try:
            company = await create_company(
                session=session,
                name="APG Empresa Demo",
                description="Empresa de demostración para el sistema APG BI",
                email="admin@apg-demo.com",
                phone="+1234567890",
                address="Dirección de ejemplo",
                website="https://apg-demo.com"
            )
            logger.info(f"Empresa creada: {company.name} (ID: {company.id})")
            return company
        except Exception as e:
            logger.error(f"Error creando empresa: {e}")
            return None

async def create_demo_users(company):
    """Crear usuarios de demostración"""
    logger.info("Creando usuarios de demostración...")
    
    users_data = [
        {
            'username': 'admin',
            'email': 'admin@apg-demo.com',
            'password': 'password123',
            'first_name': 'Admin',
            'last_name': 'Sistema',
            'position': 'Administrador del Sistema',
            'department': 'TI',
            'phone': '+1234567890',
            'is_admin': True,
            'role': UserRole.ADMIN
        },
        {
            'username': 'contador',
            'email': 'contador@apg-demo.com',
            'password': 'password123',
            'first_name': 'Juan',
            'last_name': 'Pérez',
            'position': 'Contador Principal',
            'department': 'Contabilidad',
            'phone': '+1234567891',
            'is_admin': False,
            'role': UserRole.CONTADOR
        },
        {
            'username': 'empresa',
            'email': 'empresa@apg-demo.com',
            'password': 'password123',
            'first_name': 'Ana',
            'last_name': 'López',
            'position': 'Gerente General',
            'department': 'Gerencia',
            'phone': '+1234567892',
            'is_admin': False,
            'role': UserRole.EMPRESA
        },
        {
            'username': 'invitado',
            'email': 'invitado@apg-demo.com',
            'password': 'password123',
            'first_name': 'María',
            'last_name': 'García',
            'position': 'Consultor Externo',
            'department': 'Consultoría',
            'phone': '+1234567893',
            'is_admin': False,
            'role': UserRole.INVITADO
        }
    ]
    
    created_users = []
    
    async with db_manager.get_session() as session:
        for user_data in users_data:
            try:
                user = await create_user_with_profile(
                    session=session,
                    username=user_data['username'],
                    email=user_data['email'],
                    password=user_data['password'],
                    company_id=company.id,
                    first_name=user_data['first_name'],
                    last_name=user_data['last_name'],
                    position=user_data['position'],
                    department=user_data['department'],
                    phone=user_data['phone'],
                    is_admin=user_data['is_admin'],
                    role=user_data['role']
                )
                created_users.append(user)
                logger.info(f"Usuario creado: {user.username} ({user.role.value})")
            except Exception as e:
                logger.warning(f"Error creando usuario {user_data['username']}: {e}")
    
    return created_users

async def initialize_database():
    """Función principal de inicialización"""
    logger.info("=== Iniciando inicialización de base de datos ===")
    
    try:
        # Crear tablas
        logger.info("Creando tablas...")
        await db_manager.create_tables()
        logger.info("Tablas creadas correctamente")
        
        # Crear permisos
        permissions = await create_permissions()
        
        # Asignar permisos a roles
        await assign_permissions_to_roles(permissions)
        
        # Crear empresa demo
        company = await create_demo_company()
        
        if company:
            # Crear usuarios demo
            users = await create_demo_users(company)
            logger.info(f"Creados {len(users)} usuarios de demostración")
        
        logger.info("=== Inicialización completada exitosamente ===")
        logger.info("Usuarios de prueba creados:")
        logger.info("- admin / password123 (Administrador)")
        logger.info("- contador / password123 (Contador)")
        logger.info("- empresa / password123 (Empresa)")
        logger.info("- invitado / password123 (Invitado)")
        
    except Exception as e:
        logger.error(f"Error durante la inicialización: {e}")
        raise

async def reset_database():
    """Resetear la base de datos (eliminar y recrear todo)"""
    logger.warning("=== RESETEANDO BASE DE DATOS ===")
    logger.warning("Esta operación eliminará TODOS los datos existentes")
    
    try:
        # Eliminar tablas
        logger.info("Eliminando tablas existentes...")
        await db_manager.drop_tables()
        logger.info("Tablas eliminadas")
        
        # Recrear todo
        await initialize_database()
        
    except Exception as e:
        logger.error(f"Error durante el reset: {e}")
        raise

def main():
    """Función principal del script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Inicializar base de datos APG BI')
    parser.add_argument('--reset', action='store_true', 
                       help='Resetear base de datos (eliminar todos los datos)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Mostrar información detallada')
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Ejecutar inicialización
    try:
        if args.reset:
            asyncio.run(reset_database())
        else:
            asyncio.run(initialize_database())
        
        print("\n✅ Inicialización completada exitosamente")
        print("🚀 Ya puedes iniciar la aplicación con: docker-compose up")
        
    except Exception as e:
        print(f"\n❌ Error durante la inicialización: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
