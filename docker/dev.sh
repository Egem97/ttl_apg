#!/bin/bash

# =================================================================
# SCRIPT PARA ENTORNO DE DESARROLLO
# =================================================================

set -e

echo "🔧 Iniciando entorno de desarrollo APG BI Dashboard..."

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

log() {
    echo -e "${BLUE}[DEV]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Verificar Docker
if ! command -v docker &> /dev/null; then
    echo "❌ Docker no está instalado"
    exit 1
fi

# Verificar/crear archivo config.yaml para desarrollo
if [ ! -f config.yaml ]; then
    log "Configuración no encontrada, usando plantilla de desarrollo..."
    if [ -f config.dev.yaml ]; then
        cp config.dev.yaml config.yaml
        echo "⚠️  Configuración de desarrollo copiada. Revisa config.yaml si necesitas ajustes."
    else
        echo "❌ No se encontró config.dev.yaml. Usando config.yaml existente o por defecto."
    fi
fi

# Construir y levantar en modo desarrollo
log "Construyendo imagen de desarrollo..."
docker-compose -f docker-compose.dev.yml build

log "Levantando servicios de desarrollo..."
docker-compose -f docker-compose.dev.yml up -d

log "Esperando a que los servicios estén listos..."
sleep 5

# Mostrar logs
log "Mostrando logs de la aplicación..."
docker-compose -f docker-compose.dev.yml logs -f dashboard-app &

# Información útil
echo ""
echo "🔧 ENTORNO DE DESARROLLO LISTO"
echo "════════════════════════════════════════════════"
echo "🌐 Dashboard: http://localhost:8777"
echo "🗄️  PostgreSQL: localhost:5433"
echo ""
echo "📝 COMANDOS DE DESARROLLO:"
echo "════════════════════════════════════════════════"
echo "Ver logs:        docker-compose -f docker-compose.dev.yml logs -f"
echo "Parar:          docker-compose -f docker-compose.dev.yml down"
echo "Reiniciar:      docker-compose -f docker-compose.dev.yml restart"
echo "Shell:          docker-compose -f docker-compose.dev.yml exec dashboard-app bash"
echo "DB Shell:       docker-compose -f docker-compose.dev.yml exec postgres-db psql -U postgres -d apg_bi_dev"
echo ""

success "✅ Entorno de desarrollo iniciado!"
echo "Presiona Ctrl+C para parar los logs (los servicios seguirán corriendo)"

# Mantener el script corriendo para mostrar logs
wait