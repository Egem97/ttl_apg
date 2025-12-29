#!/bin/bash

# =================================================================
# SCRIPT DE DESPLIEGUE AUTOMATIZADO
# =================================================================

set -e  # Salir si hay algún error

echo "🚀 Iniciando despliegue de APG BI Dashboard..."

# Colores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para logging
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
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

# Verificar que Docker esté instalado
if ! command -v docker &> /dev/null; then
    error "Docker no está instalado. Instala Docker primero."
fi

if ! command -v docker-compose &> /dev/null; then
    error "Docker Compose no está instalado. Instala Docker Compose primero."
fi

# Verificar que existe el archivo config.yaml
if [ ! -f config.yaml ]; then
    warning "Archivo config.yaml no encontrado."
    if [ -f config.docker.yaml ]; then
        log "Copiando configuración para Docker..."
        cp config.docker.yaml config.yaml
        warning "⚠️  IMPORTANTE: Edita config.yaml con tus configuraciones Microsoft Graph API."
        echo "Presiona Enter cuando hayas configurado config.yaml..."
        read -r
    else
        error "No se encontró config.docker.yaml como plantilla."
    fi
fi

# Crear directorios necesarios
log "Creando directorios necesarios..."
mkdir -p logs
mkdir -p docker/ssl

# Construir y levantar los servicios
log "Construyendo imágenes Docker..."
docker-compose build --no-cache

log "Levantando servicios..."
docker-compose up -d

# Esperar a que los servicios estén listos
log "Esperando a que los servicios estén listos..."
sleep 10

# Verificar el estado de los servicios
log "Verificando estado de los servicios..."
docker-compose ps

# Verificar conectividad de la aplicación
log "Verificando conectividad de la aplicación..."
if curl -f http://localhost:8777 > /dev/null 2>&1; then
    success "✅ Aplicación desplegada exitosamente!"
    success "🌐 Dashboard disponible en: http://localhost:8777"
else
    warning "⚠️  La aplicación puede estar iniciando aún. Verifica los logs:"
    echo "docker-compose logs dashboard-app"
fi

# Mostrar información útil
echo ""
echo "📋 INFORMACIÓN DEL DESPLIEGUE:"
echo "════════════════════════════════════════════════"
echo "🌐 Dashboard URL: http://localhost:8777"
echo "🗄️  PostgreSQL: localhost:5432"
echo "🔄 Redis: localhost:6379"
echo "🌐 Nginx: localhost:80"
echo ""
echo "📝 COMANDOS ÚTILES:"
echo "════════════════════════════════════════════════"
echo "Ver logs:           docker-compose logs -f"
echo "Parar servicios:    docker-compose down"
echo "Reiniciar:          docker-compose restart"
echo "Entrar al contenedor: docker-compose exec dashboard-app bash"
echo ""

success "🎉 Despliegue completado!"