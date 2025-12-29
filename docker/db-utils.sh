#!/bin/bash

# =================================================================
# UTILIDADES DE BASE DE DATOS PARA DOCKER
# =================================================================

set -e

COMPOSE_FILE="docker-compose.yml"
DB_CONTAINER="apg-bi-postgres"
DB_NAME="apg_bi"
DB_USER="postgres"

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[DB-UTILS]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Función para mostrar ayuda
show_help() {
    echo "🗄️  UTILIDADES DE BASE DE DATOS"
    echo "════════════════════════════════════════════════"
    echo "Uso: $0 [COMANDO]"
    echo ""
    echo "COMANDOS DISPONIBLES:"
    echo "  backup          Crear backup de la base de datos"
    echo "  restore FILE    Restaurar backup de la base de datos"
    echo "  shell           Conectar a shell de PostgreSQL"
    echo "  reset           Resetear base de datos (¡CUIDADO!)"
    echo "  logs            Ver logs de la base de datos"
    echo "  status          Ver estado de la base de datos"
    echo "  help            Mostrar esta ayuda"
    echo ""
    echo "EJEMPLOS:"
    echo "  $0 backup"
    echo "  $0 restore backup_2024-01-15.sql"
    echo "  $0 shell"
    echo ""
}

# Verificar que Docker Compose está corriendo
check_services() {
    if ! docker-compose ps | grep -q "$DB_CONTAINER"; then
        error "El contenedor de base de datos no está corriendo. Ejecuta: docker-compose up -d"
    fi
}

# Crear backup
create_backup() {
    check_services
    
    local backup_file="backup_$(date +%Y-%m-%d_%H-%M-%S).sql"
    local backup_path="./backups/$backup_file"
    
    log "Creando backup de la base de datos..."
    
    # Crear directorio de backups si no existe
    mkdir -p ./backups
    
    # Crear backup
    docker-compose exec -T postgres-db pg_dump -U $DB_USER -d $DB_NAME > "$backup_path"
    
    if [ $? -eq 0 ]; then
        success "✅ Backup creado exitosamente: $backup_path"
        
        # Comprimir backup
        gzip "$backup_path"
        success "✅ Backup comprimido: ${backup_path}.gz"
        
        # Limpiar backups antiguos (mantener solo los últimos 5)
        cd ./backups
        ls -t backup_*.sql.gz | tail -n +6 | xargs -r rm
        cd ..
        
        log "📁 Backups disponibles:"
        ls -la ./backups/backup_*.sql.gz 2>/dev/null || echo "No hay backups disponibles"
    else
        error "❌ Error creando backup"
    fi
}

# Restaurar backup
restore_backup() {
    if [ -z "$1" ]; then
        error "Especifica el archivo de backup. Uso: $0 restore ARCHIVO"
    fi
    
    local backup_file="$1"
    
    if [ ! -f "$backup_file" ]; then
        error "Archivo de backup no encontrado: $backup_file"
    fi
    
    check_services
    
    warning "⚠️  ADVERTENCIA: Esto sobrescribirá toda la base de datos actual."
    echo "¿Estás seguro? (escribe 'yes' para continuar)"
    read -r confirmation
    
    if [ "$confirmation" != "yes" ]; then
        log "Operación cancelada."
        exit 0
    fi
    
    log "Restaurando backup: $backup_file"
    
    # Si el archivo está comprimido, descomprimirlo temporalmente
    if [[ "$backup_file" == *.gz ]]; then
        local temp_file="/tmp/$(basename "$backup_file" .gz)"
        gunzip -c "$backup_file" > "$temp_file"
        backup_file="$temp_file"
    fi
    
    # Restaurar backup
    docker-compose exec -T postgres-db psql -U $DB_USER -d $DB_NAME < "$backup_file"
    
    if [ $? -eq 0 ]; then
        success "✅ Backup restaurado exitosamente"
    else
        error "❌ Error restaurando backup"
    fi
    
    # Limpiar archivo temporal si fue descomprimido
    if [ -f "/tmp/backup_"* ]; then
        rm -f /tmp/backup_*
    fi
}

# Conectar a shell de PostgreSQL
connect_shell() {
    check_services
    log "Conectando a shell de PostgreSQL..."
    log "Tip: Usa \\q para salir, \\l para listar bases de datos, \\dt para listar tablas"
    docker-compose exec postgres-db psql -U $DB_USER -d $DB_NAME
}

# Resetear base de datos
reset_database() {
    check_services
    
    warning "⚠️  PELIGRO: Esto eliminará TODOS los datos de la base de datos."
    echo "¿Estás completamente seguro? (escribe 'DELETE_ALL_DATA' para continuar)"
    read -r confirmation
    
    if [ "$confirmation" != "DELETE_ALL_DATA" ]; then
        log "Operación cancelada."
        exit 0
    fi
    
    log "Reseteando base de datos..."
    
    # Parar aplicación
    docker-compose stop dashboard-app
    
    # Eliminar y recrear base de datos
    docker-compose exec postgres-db psql -U $DB_USER -c "DROP DATABASE IF EXISTS $DB_NAME;"
    docker-compose exec postgres-db psql -U $DB_USER -c "CREATE DATABASE $DB_NAME;"
    
    # Reiniciar aplicación
    docker-compose start dashboard-app
    
    success "✅ Base de datos reseteada"
}

# Ver logs de la base de datos
show_logs() {
    check_services
    log "Mostrando logs de la base de datos (Ctrl+C para salir)..."
    docker-compose logs -f postgres-db
}

# Ver estado de la base de datos
show_status() {
    check_services
    
    log "Estado de la base de datos:"
    echo "════════════════════════════════════════════════"
    
    # Estado del contenedor
    docker-compose ps postgres-db
    echo ""
    
    # Información de la base de datos
    log "Información de la base de datos:"
    docker-compose exec postgres-db psql -U $DB_USER -d $DB_NAME -c "
        SELECT 
            current_database() as database,
            current_timestamp as current_time,
            version() as postgresql_version;
    "
    
    # Tamaño de la base de datos
    log "Tamaño de la base de datos:"
    docker-compose exec postgres-db psql -U $DB_USER -d $DB_NAME -c "
        SELECT 
            pg_database.datname as database_name,
            pg_size_pretty(pg_database_size(pg_database.datname)) as size
        FROM pg_database 
        WHERE datname = '$DB_NAME';
    "
    
    # Conexiones activas
    log "Conexiones activas:"
    docker-compose exec postgres-db psql -U $DB_USER -d $DB_NAME -c "
        SELECT count(*) as active_connections 
        FROM pg_stat_activity 
        WHERE datname = '$DB_NAME';
    "
}

# Comando principal
case "$1" in
    backup)
        create_backup
        ;;
    restore)
        restore_backup "$2"
        ;;  
    shell)
        connect_shell
        ;;
    reset)
        reset_database
        ;;
    logs)
        show_logs
        ;;
    status)
        show_status
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "❌ Comando desconocido: $1"
        echo ""
        show_help
        exit 1
        ;;
esac