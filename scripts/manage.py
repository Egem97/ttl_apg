#!/usr/bin/env python3
"""
Script de gestión para APG BI Dashboard
"""
import os
import sys
import subprocess
import argparse
import yaml
from pathlib import Path

# Agregar el directorio padre al path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_directories():
    """Crear directorios necesarios para el proyecto"""
    directories = [
        'logs',
        'logs/nginx',
        'data',
        'data/postgres',
        'data/redis',
        'docker/ssl',
        'backups',
        'temp'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Directorio creado: {directory}")

def check_config_file():
    """Verificar si existe el archivo de configuración"""
    config_file = Path('config.yaml')
    
    if not config_file.exists():
        print("⚠️  Archivo config.yaml no encontrado")
        create_config = input("¿Deseas crear un config.yaml de ejemplo? (y/N): ")
        
        if create_config.lower() == 'y':
            create_sample_config()
        else:
            print("❌ Se necesita un archivo config.yaml para continuar")
            return False
    
    return True

def create_sample_config():
    """Crear archivo de configuración de ejemplo"""
    sample_config = {
        'database': {
            'server': 'localhost',
            'port': 5432,
            'user': 'postgres',
            'password': 'admin123',
            'name': 'apg_bi'
        },
        'app': {
            'port': 8777,
            'debug': True,
            'logo': '/resource/logo_apg.jpeg'
        },
        'empresa': {
            'name': 'APG Empresa',
            'name_user': 'Usuario APG',
            'rubro': 'Tecnología'
        },
        'redis': {
            'host': 'localhost',
            'port': 6379,
            'session_db': 0,
            'cache_db': 1
        },
        'microsoft_graph': {
            'tenant_id': 'tu_tenant_id_aqui',
            'client_id': 'tu_client_id_aqui',
            'client_secret': 'tu_client_secret_aqui'
        },
        'microsoft_graph_packing': {
            'tenant_id': 'tu_tenant_id_packing_aqui',
            'client_id': 'tu_client_id_packing_aqui',
            'client_secret': 'tu_client_secret_packing_aqui'
        },
        'onedrive': {
            'drive_id': 'tu_drive_id_aqui',
            'folder_id': 'tu_folder_id_aqui'
        }
    }
    
    with open('config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(sample_config, f, default_flow_style=False, allow_unicode=True)
    
    print("✓ Archivo config.yaml creado")
    print("📝 Por favor, edita config.yaml con tus configuraciones específicas")

def check_docker():
    """Verificar si Docker está instalado y funcionando"""
    try:
        subprocess.run(['docker', '--version'], check=True, capture_output=True)
        subprocess.run(['docker-compose', '--version'], check=True, capture_output=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker o docker-compose no están instalados o no funcionan correctamente")
        print("📦 Instala Docker desde: https://docs.docker.com/get-docker/")
        return False

def build_containers():
    """Construir contenedores Docker"""
    print("🔨 Construyendo contenedores Docker...")
    try:
        subprocess.run(['docker-compose', 'build'], check=True)
        print("✓ Contenedores construidos exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error construyendo contenedores: {e}")
        return False

def start_services(with_monitoring=False):
    """Iniciar servicios"""
    print("🚀 Iniciando servicios...")
    
    cmd = ['docker-compose', 'up', '-d']
    if with_monitoring:
        cmd.extend(['--profile', 'monitoring'])
    
    try:
        subprocess.run(cmd, check=True)
        print("✓ Servicios iniciados exitosamente")
        
        print("\n📊 Servicios disponibles:")
        print("- Dashboard: http://localhost:8777")
        print("- PostgreSQL: localhost:5432")
        print("- Redis: localhost:6379")
        print("- Nginx: http://localhost")
        
        if with_monitoring:
            print("- pgAdmin: http://localhost:8080")
            print("- Redis Commander: http://localhost:8081")
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error iniciando servicios: {e}")
        return False

def stop_services():
    """Detener servicios"""
    print("🛑 Deteniendo servicios...")
    try:
        subprocess.run(['docker-compose', 'down'], check=True)
        print("✓ Servicios detenidos exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error deteniendo servicios: {e}")
        return False

def show_logs(service=None):
    """Mostrar logs de servicios"""
    cmd = ['docker-compose', 'logs']
    
    if service:
        cmd.append(service)
    else:
        cmd.append('--tail=100')
    
    try:
        subprocess.run(cmd)
    except subprocess.CalledProcessError as e:
        print(f"❌ Error obteniendo logs: {e}")

def show_status():
    """Mostrar estado de los servicios"""
    print("📊 Estado de los servicios:")
    try:
        subprocess.run(['docker-compose', 'ps'])
    except subprocess.CalledProcessError as e:
        print(f"❌ Error obteniendo estado: {e}")

def backup_database():
    """Crear backup de la base de datos"""
    from datetime import datetime
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/backup_apg_bi_{timestamp}.sql"
    
    print(f"💾 Creando backup de la base de datos: {backup_file}")
    
    cmd = [
        'docker-compose', 'exec', '-T', 'postgres-db',
        'pg_dump', '-U', 'postgres', '-d', 'apg_bi'
    ]
    
    try:
        with open(backup_file, 'w') as f:
            subprocess.run(cmd, stdout=f, check=True)
        
        print(f"✓ Backup creado exitosamente: {backup_file}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error creando backup: {e}")
        return False

def restore_database(backup_file):
    """Restaurar base de datos desde backup"""
    if not os.path.exists(backup_file):
        print(f"❌ Archivo de backup no encontrado: {backup_file}")
        return False
    
    print(f"🔄 Restaurando base de datos desde: {backup_file}")
    
    cmd = [
        'docker-compose', 'exec', '-T', 'postgres-db',
        'psql', '-U', 'postgres', '-d', 'apg_bi'
    ]
    
    try:
        with open(backup_file, 'r') as f:
            subprocess.run(cmd, stdin=f, check=True)
        
        print("✓ Base de datos restaurada exitosamente")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error restaurando base de datos: {e}")
        return False

def clean_system():
    """Limpiar sistema (contenedores, volúmenes, etc.)"""
    print("🧹 Limpiando sistema...")
    
    confirm = input("⚠️  Esto eliminará todos los contenedores y volúmenes. ¿Continuar? (y/N): ")
    if confirm.lower() != 'y':
        print("Operación cancelada")
        return
    
    try:
        # Detener y eliminar contenedores
        subprocess.run(['docker-compose', 'down', '-v', '--remove-orphans'], check=True)
        
        # Eliminar imágenes
        subprocess.run(['docker', 'system', 'prune', '-f'], check=True)
        
        print("✓ Sistema limpiado exitosamente")
    except subprocess.CalledProcessError as e:
        print(f"❌ Error limpiando sistema: {e}")

def setup_project():
    """Configuración inicial completa del proyecto"""
    print("🚀 Configuración inicial de APG BI Dashboard")
    print("=" * 50)
    
    # 1. Crear directorios
    print("\n1. Creando directorios necesarios...")
    create_directories()
    
    # 2. Verificar configuración
    print("\n2. Verificando configuración...")
    if not check_config_file():
        return False
    
    # 3. Verificar Docker
    print("\n3. Verificando Docker...")
    if not check_docker():
        return False
    
    # 4. Construir contenedores
    print("\n4. Construyendo contenedores...")
    if not build_containers():
        return False
    
    # 5. Iniciar servicios
    print("\n5. Iniciando servicios...")
    if not start_services():
        return False
    
    print("\n✅ Configuración inicial completada exitosamente!")
    print("\n📚 Próximos pasos:")
    print("1. Ejecuta: python scripts/init_db.py (para inicializar la base de datos)")
    print("2. Visita: http://localhost:8777 (para acceder al dashboard)")
    print("3. Usa las credenciales de prueba para hacer login")
    
    return True

def main():
    """Función principal del script"""
    parser = argparse.ArgumentParser(description='Gestión de APG BI Dashboard')
    subparsers = parser.add_subparsers(dest='command', help='Comandos disponibles')
    
    # Comando setup
    subparsers.add_parser('setup', help='Configuración inicial completa')
    
    # Comando start
    start_parser = subparsers.add_parser('start', help='Iniciar servicios')
    start_parser.add_argument('--monitoring', action='store_true', 
                             help='Incluir servicios de monitoreo')
    
    # Comando stop
    subparsers.add_parser('stop', help='Detener servicios')
    
    # Comando status
    subparsers.add_parser('status', help='Mostrar estado de servicios')
    
    # Comando logs
    logs_parser = subparsers.add_parser('logs', help='Mostrar logs')
    logs_parser.add_argument('service', nargs='?', help='Servicio específico')
    
    # Comando build
    subparsers.add_parser('build', help='Construir contenedores')
    
    # Comando backup
    subparsers.add_parser('backup', help='Crear backup de la base de datos')
    
    # Comando restore
    restore_parser = subparsers.add_parser('restore', help='Restaurar base de datos')
    restore_parser.add_argument('backup_file', help='Archivo de backup')
    
    # Comando clean
    subparsers.add_parser('clean', help='Limpiar sistema')
    
    args = parser.parse_args()
    
    if args.command == 'setup':
        setup_project()
    elif args.command == 'start':
        start_services(args.monitoring)
    elif args.command == 'stop':
        stop_services()
    elif args.command == 'status':
        show_status()
    elif args.command == 'logs':
        show_logs(args.service)
    elif args.command == 'build':
        build_containers()
    elif args.command == 'backup':
        backup_database()
    elif args.command == 'restore':
        restore_database(args.backup_file)
    elif args.command == 'clean':
        clean_system()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
