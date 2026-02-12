# 📊 API Gateway - Motor Integrado y Seguro

Sistema de sincronización inteligente de tablas en SQL Server con lógica de comparación y priorización.

## 🎯 Descripción

Este proyecto implementa un motor de sincronización de datos que:

1. **Detecta Cierres Automáticos**: Identifica tickets que desaparecieron del sistema automático
2. **Sincroniza Carga Automática** (B → C): Mantiene la tabla consolidada actualizada con la carga automática
3. **Aplica Prioridad de Gestión** (A → C): La gestión manual del equipo tiene prioridad
4. **Genera Volcados de Fallas**: Filtra y exporta solo fallas y mantenimientos a tabla de fallas masivas
5. **Expone API REST**: Acceso mediante endpoints HTTP

## 📁 Estructura del Proyecto

```
.
├── main.py                 # Script de ejecución batch
├── main-SERVER.py          # Servidor Flask con API REST
├── requirements.txt        # Dependencias Python
├── README.md              # Este archivo
├── config/
│   ├── __init__.py
│   └── credentials.py     # Configuración de BD y tablas
├── src/
│   ├── __init__.py
│   ├── database.py        # Gestor de conexiones SQL Server
│   ├── api_gateway.py     # Motor de sincronización
│   ├── comparison.py      # Comparación de tablas (heredado)
│   ├── injection.py       # Inyección de datos (heredado)
│   └── logger.py          # Sistema de logging
└── logs/
    └── app.log            # Archivo de logs
```

## 🚀 Instalación

### Requisitos Previos
- Python 3.8+
- SQL Server con ODBC Driver 17
- Acceso a BD con tablas configuradas

### Pasos

1. **Clonar repositorio**
```bash
git clone <repo-url>
cd unificacion-de-tablas
```

2. **Crear entorno virtual**
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# o
.venv\Scripts\activate  # Windows
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Configurar credenciales**
Edita `config/credentials.py` con tus datos:
```python
DB_CONFIG = {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": "tu_servidor",
    "port": "21408",
    "database": "tu_bd",
    "username": "tu_usuario",
    "password": "tu_contraseña"
}

TABLES_CONFIG = {
    "source_table": "schema.tabla_origen",
    "comparison_table": "schema.tabla_comparacion",
    "result_table": "schema.tabla_resultado",
    # ... más tablas
}
```

## 📝 Uso

### Opción 1: Ejecución Batch
```bash
python main.py
```
Procesa todos los nodos configurados y genera logs.

### Opción 2: Servidor API REST
```bash
python main-SERVER.py
```
Inicia servidor Flask en `http://localhost:5000`

## 🔌 Endpoints API

### 1. Procesar Nodo
```http
GET /api/gateway/process?nodo=NODO1
```
Ejecuta el flujo completo de sincronización para un nodo.

**Respuesta exitosa (200)**:
```json
{
  "success": true,
  "data": [
    {
      "Nodo": "NODO1",
      "Ticket": "INC123",
      "Tipo": "Error de conexión",
      "Estado": "OPEN",
      "Fecha": "2026-02-12 10:30:00",
      "Owner": "Técnico1"
    }
  ]
}
```

**Respuesta con error (400/500)**:
```json
{
  "success": false,
  "error": "Descripción del error"
}
```

### 2. Estado del Nodo
```http
GET /api/gateway/status?nodo=NODO1
```
Obtiene estadísticas del nodo (total, abiertos, cerrados).

**Respuesta (200)**:
```json
{
  "success": true,
  "nodo": "NODO1",
  "total": 245,
  "abiertos": 23,
  "cerrados": 222
}
```

### 3. Health Check
```http
GET /api/gateway/health
```
Verifica si el servidor está activo.

**Respuesta (200)**:
```json
{
  "success": true,
  "status": "online",
  "timestamp": "2026-02-12 12:30:45"
}
```

### 4. Listar Nodos
```http
GET /api/gateway/nodes
```
Obtiene lista de nodos disponibles.

**Respuesta (200)**:
```json
{
  "success": true,
  "nodes": ["NODO1", "NODO2", "NODO3"]
}
```

## 🔄 Flujo de Sincronización

```
┌─────────────────────────────────────────┐
│   PASO 1: Verificar Actualizaciones      │
│   (Últimos 10 minutos)                   │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   PASO 2: Detectar Cierres Automáticos   │
│   (Tickets que desaparecieron)           │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   PASO 3: Sincronizar B → C              │
│   (Carga automática → Consolidado)       │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   PASO 4: Aplicar Prioridad A → C        │
│   (Gestión manual → Consolidado)         │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   PASO 5: Volcado a Fallas Masivas       │
│   (C → Tabla de Fallas)                  │
└──────────────┬──────────────────────────┘
               ↓
┌─────────────────────────────────────────┐
│   PASO 6: Retornar Datos del Nodo        │
│   (Tickets abiertos)                     │
└─────────────────────────────────────────┘
```

## 📊 Tablas Principales

| Tabla | Descripción | Rol |
|-------|-------------|-----|
| homeb2c_consolidado (C) | Tabla maestra de consolidación | Central |
| homeb2c_tiv (B) | Carga automática del sistema | Origen secundario |
| homeb2c_tck (A) | Gestión manual del equipo | Origen principal |
| homeb2c_mtv_a | Catálogo de motivos | Clasificación |
| homecc_fal | Tabla de fallas masivas | Destino filtrado |

## 🔐 Seguridad

- ✅ Credenciales en archivo separado (no versionado)
- ✅ Parámetros preparados contra inyección SQL
- ✅ Validación de entrada en endpoints
- ✅ Logging detallado de operaciones
- ✅ Context managers para manejo seguro de conexiones
- ✅ Encriptación de conexión SQL Server (TrustServerCertificate)

## 📋 Logging

Los logs se guardan en `logs/app.log` con formato:
```
2026-02-12 12:30:45 - logger_name - INFO - Mensaje del log
```

Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL

## 🧪 Desarrollo

### Ejecutar pruebas
```bash
python -m pytest tests/
```

### Ejecutar linter
```bash
pylint src/
```

### Format de código
```bash
black src/
```

## 📌 Notas Importantes

1. **Tablas con Esquema Personalizado**: El código soporta tablas del tipo `schema.nombre_tabla`

2. **Marca de Tiempo**: Todos los registros llevan `Ultima_Actualizacion` automática

3. **Limpiar Tabla de Resultados**: 
   ```python
   gateway = APIGateway()
   gateway.clear_result_table()
   ```

4. **Reintentos**: En caso de error, el servidor retoma desde el último paso exitoso

5. **Ventana de Tiempo**: Se procesan actualizaciones de los últimos 15 minutos

## 🐛 Troubleshooting

### Error de conexión
- Verificar credenciales en `config/credentials.py`
- Confirmar ODBC Driver 17 instalado: `odbcinst -j`
- Verificar conectividad: `sqlcmd -S servidor -U usuario -P contraseña`

### No se actualizan datos
- Revisar logs en `logs/app.log`
- Verificar permisos en BD (UPDATE, INSERT, MERGE)
- Confirmar existencia de tablas

### Puerto en uso
```bash
# Cambiar puerto en main-SERVER.py línea final:
app.run(host='0.0.0.0', port=8000, debug=False)
```

## 📞 Contacto & Soporte

Para reportar problemas o sugerencias, contactar al equipo de desarrollo.

---

**Última actualización**: 12 de febrero de 2026
**Versión**: 1.0.0
