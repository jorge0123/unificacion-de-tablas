"""
EJEMPLO DE CONFIGURACIÓN
Copia el contenido relevante a config/credentials.py

Importante: NO comitear credenciales reales a Git
Usar: git update-index --assume-unchanged config/credentials.py
"""

# ============================================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================================

DB_CONFIG = {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": "143.208.182.187",      # IP o hostname del servidor
    "port": "21408",                  # Puerto SQL Server (default 1433)
    "database": "TStest",             # Nombre de la BD
    "username": "tlopezb",            # Usuario con permisos
    "password": "LB$>nRK$vruC9g3dJ!#t*:"  # Contraseña
}

# ============================================================================
# CONFIGURACIÓN DE TABLAS
# ============================================================================
# Formato: "schema.nombre_tabla"
# Si no especificas schema, usa "dbo" por defecto

TABLES_CONFIG = {
    # Tabla A: Gestión Manual del Equipo (Máxima Prioridad)
    "tck": "tigostar.homeb2c_tck",
    
    # Tabla B: Carga Automática del Sistema
    "tiv": "tigostar.homeb2c_tiv",
    
    # Tabla C: Consolidado (Tabla Central)
    "consolidado": "tigostar.homeb2c_consolidado",
    
    # Tabla MTV: Catálogo de Motivos
    "mtv": "tigostar.homeb2c_mtv_a",
    
    # Tabla de Fallas Masivas (Destino Final)
    "fallas": "tigostar.homecc_fal",
    
    # Referencias para el Gateway
    "source_table": "tigostar.homeb2c_consolidado",      # Origen
    "comparison_table": "tigostar.homeb2c_tiv",          # Para comparación
    "result_table": "tigostar.homeb2c_resultado",        # Tabla de resultados
}

# ============================================================================
# CONFIGURACIÓN DE PROCESAMIENTO
# ============================================================================

PROCESSING_CONFIG = {
    "batch_size": 1000,           # Registros por lote de inserción
    "enable_logging": True,       # Activar logging
    "log_level": "INFO",          # DEBUG, INFO, WARNING, ERROR, CRITICAL
}

# ============================================================================
# ESTRUCTURA DE TABLAS ESPERADA
# ============================================================================

"""
TABLA A: tigostar.homeb2c_tck (Gestión de Equipo)
- Ticket (PK)
- Estado_Evento
- Tecnico
- Cierre_Evento

TABLA B: tigostar.homeb2c_tiv (Carga Automática)
- Incident (PK)
- Summary
- Reported_By
- Reported_Date
- Nodo
- Status
- Owner
- Owner_Group

TABLA C: tigostar.homeb2c_consolidado (Consolidado Central)
- Incident (PK)
- Summary
- Reported_By
- Reported_Date
- Nodo
- Status
- Owner
- Owner_Group
- Fecha_Cierre
- Gestionado_En_A
- Ultima_Actualizacion

TABLA MTV: tigostar.homeb2c_mtv_a (Catálogo)
- MOTIVO_APERTURA
- CATEGORIA (FALLA, MANTENIMIENTO, etc)

TABLA FALLAS: tigostar.homecc_fal (Destino)
- Ticket
- Motivo_Apertura
- Direccion
- Estado
- Inicio_Evento
- Cierre_Evento
- Nodo
- Fecha_Fin_Falla
- Fecha_Creado
- Crea
- Clientes_Afectados
"""

# ============================================================================
# VARIABLES DE ENTORNO (Alternativa Segura)
# ============================================================================

"""
En lugar de codificar credenciales, puedes usar variables de entorno:

import os

DB_CONFIG = {
    "driver": os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server"),
    "server": os.getenv("DB_SERVER"),
    "port": os.getenv("DB_PORT", "1433"),
    "database": os.getenv("DB_NAME"),
    "username": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

Luego ejecutar:
export DB_SERVER="143.208.182.187"
export DB_PORT="21408"
export DB_NAME="TStest"
export DB_USER="tlopezb"
export DB_PASSWORD="contraseña"
python main.py
"""

# ============================================================================
# FLUJO DE DATOS
# ============================================================================

"""
1. VERIFICACIÓN DE TIEMPO
   - Chequea si hay cambios recientes en tabla C (últimos 10 min)

2. DETECCIÓN DE CIERRES AUTOMÁTICOS
   - Identifica tickets que desaparecieron de B pero no están en A abiertos
   - Los marca como CLOSED en C

3. SINCRONIZACIÓN B → C
   - Inserta nuevos tickets de B a C
   - Actualiza estado de existentes

4. PRIORIDAD A → C (LA MÁS IMPORTANTE)
   - La gestión manual de A sobreescribe todo en C
   - Owner, Estado, Fecha_Cierre de A → C

5. VOLCADO A FALLAS
   - Filtra solo tickets con categoría FALLA o MANTENIMIENTO
   - Los inserta/actualiza en tabla de fallas

6. RETORNO DE DATOS
   - Devuelve tickets abiertos del nodo solicitado
"""

# ============================================================================
# EJEMPLO DE USO
# ============================================================================

"""
# En Python:
from src.api_gateway import APIGateway

gateway = APIGateway()
resultado = gateway.process_node("NODO1")

print(resultado)
# Output:
# {
#   'success': True,
#   'data': [
#     {
#       'Nodo': 'NODO1',
#       'Ticket': 'INC123',
#       'Tipo': 'Error de conexión',
#       'Estado': 'OPEN',
#       'Fecha': '2026-02-12 10:30:00',
#       'Owner': 'Juan Pérez'
#     },
#     ...
#   ]
# }

# Como API REST:
# GET http://localhost:5000/api/gateway/process?nodo=NODO1
"""

# ============================================================================
# NOTAS DE SEGURIDAD
# ============================================================================

"""
1. NUNCA comitear credenciales reales
   git update-index --assume-unchanged config/credentials.py

2. Usar .gitignore:
   echo "config/credentials.py" >> .gitignore

3. Para desarrollo local, usar archivos separados por entorno:
   config/credentials.dev.py
   config/credentials.prod.py

4. En producción, usar:
   - Variables de entorno
   - Azure Key Vault
   - AWS Secrets Manager
   - HashiCorp Vault
"""
