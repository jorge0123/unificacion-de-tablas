#!/bin/bash
# Script de instalación y configuración del proyecto
# Uso: bash setup.sh

set -e  # Salir si hay error

echo "======================================================================"
echo "API Gateway - Script de Instalación"
echo "======================================================================"

# Colores
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Función para imprimir mensajes
print_status() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Verificar Python
echo ""
echo "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 no instalado"
    exit 1
fi
PYTHON_VERSION=$(python3 --version)
print_status "Python encontrado: $PYTHON_VERSION"

# Crear entorno virtual si no existe
echo ""
echo "Configurando entorno virtual..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    print_status "Entorno virtual creado"
else
    print_status "Entorno virtual ya existe"
fi

# Activar entorno virtual
print_status "Activando entorno virtual..."
source .venv/bin/activate

# Actualizar pip
echo ""
print_status "Actualizando pip..."
pip install --upgrade pip > /dev/null 2>&1

# Instalar dependencias
echo ""
echo "Instalando dependencias..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
    print_status "Dependencias instaladas"
else
    print_error "requirements.txt no encontrado"
    exit 1
fi

# Crear estructura de directorios
echo ""
echo "Creando estructura de directorios..."
mkdir -p logs
print_status "Directorio logs/ creado"

# Verificar credenciales
echo ""
echo "Verificando configuración..."
if [ ! -f "config/credentials.py" ]; then
    print_warning "config/credentials.py NO encontrado"
    print_warning "Debes crear este archivo con tus credenciales"
    echo ""
    echo "1. Copia CONFIG_EJEMPLO.md"
    echo "2. Edita config/credentials.py con tus datos"
    echo "3. Ejecuta este script nuevamente"
else
    print_status "Configuración encontrada"
fi

# Verificar conexión a BD
echo ""
echo "Verificando conexión a base de datos..."
python3 << 'EOF'
import sys
try:
    from config.credentials import DB_CONFIG
    import pyodbc
    
    # Construir string de conexión
    conn_string = (
        f"DRIVER={{{DB_CONFIG['driver']}}};"
        f"SERVER={DB_CONFIG['server']},{DB_CONFIG['port']};"
        f"DATABASE={DB_CONFIG['database']};"
        f"UID={DB_CONFIG['username']};"
        f"PWD={DB_CONFIG['password']};"
        "Encrypt=yes;"
        "TrustServerCertificate=yes;"
    )
    
    # Intentar conectar
    conn = pyodbc.connect(conn_string, timeout=5)
    print("✓ Conexión a BD exitosa")
    conn.close()
except Exception as e:
    print(f"✗ Error conectando a BD: {e}")
    sys.exit(1)
EOF

# Resumen final
echo ""
echo "======================================================================"
echo "INSTALACIÓN COMPLETADA ✓"
echo "======================================================================"
echo ""
echo "Próximos pasos:"
echo ""
echo "1. EJECUCIÓN BATCH (procesamiento automático):"
echo "   python main.py"
echo ""
echo "2. O SERVIDOR API REST:"
echo "   python main-SERVER.py"
echo "   Luego acceder a: http://localhost:5000"
echo ""
echo "3. TESTING (con servidor corriendo en otra terminal):"
echo "   python test_api_gateway.py"
echo ""
echo "Documentación: Ver DOCUMENTACION_API_GATEWAY.md"
echo ""
echo "======================================================================"
