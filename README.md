# 🚀 API Gateway - Sistema de Sincronización Automática

Sistema profesional de sincronización de datos entre múltiples tablas SQL Server con **nodos dinámicos**, **REST API** y **procesamiento automático sin intervención manual**.

---

## 📋 Descripción

Este sistema sincroniza automáticamente datos entre **3 tablas principales**:

- **Tabla A (homeb2c_tck)** - Gestión manual del equipo (máxima prioridad)
- **Tabla B (homeb2c_tiv)** - Carga automática del sistema
- **Tabla C (homeb2c_consolidado)** - Tabla de consolidación central
- **Tabla Fallas (homecc_fal)** - Registro de fallos masivos

### Características Clave

✅ **Totalmente automático** - Sin intervención manual  
✅ **Nodos dinámicos** - Busca automáticamente qué nodos procesar  
✅ **REST API** - Endpoints JSON para integración  
✅ **Seguridad** - Parámetros preparados contra SQL injection  
✅ **Logging completo** - Auditoría de todas las operaciones  
✅ **6 pasos de sincronización** - Proceso robusto y comprobado  

---

## 🏗️ Estructura del Proyecto

```
.
├── config/
│   ├── credentials.py      # Configuración de BD y parámetros
│   └── __init__.py
├── src/
│   ├── api_gateway.py      # Motor principal (6 pasos)
│   ├── database.py         # Gestor de conexiones
│   ├── comparison.py       # Comparación de tablas
│   ├── injection.py        # Inyección de datos
│   ├── logger.py           # Sistema de logging
│   └── __init__.py
├── logs/                   # Archivos de log (rotativo)
├── main.py                 # Script batch (opcional)
├── main-SERVER.py          # Servidor Flask REST API
├── requirements.txt        # Dependencias Python
└── README.md
```

---

## ⚙️ Instalación y Configuración

### 1. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 2. Configurar credenciales

Edita `config/credentials.py`:

```python
DB_CONFIG = {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": "143.208.182.187",
    "port": "21408",
    "database": "TStest",
    "username": "tu_usuario",
    "password": "tu_password",
}

TABLES_CONFIG = {
    "tabla_a": "[tigostar].[homeb2c_tck]",
    "tabla_b": "[tigostar].[homeb2c_tiv]",
    "tabla_c": "[tigostar].[homeb2c_consolidado]",
    "tabla_fallas": "[tigostar].[homecc_fal]",
}
```

### 3. Verificar ODBC Driver

**macOS:**
```bash
brew install unixodbc
brew install msodbcsql17
odbcinst -j
```

**Windows:**
Descargar "ODBC Driver 17 for SQL Server" desde Microsoft

---

## 🚀 Ejecución

### Servidor REST API (Recomendado)

```bash
python main-SERVER.py
```

Escucha en: `http://localhost:5000`

### Script Batch (Una sola ejecución)

```bash
python main.py
```

---

## 📡 Endpoints API

### 1. Procesar todos los nodos (AUTOMÁTICO)

```bash
curl http://localhost:5000/api/gateway/process-all
```

**Respuesta:**
```json
{
  "success": true,
  "total_nodos": 5,
  "procesados": 5,
  "nodos_encontrados": ["NODO1", "NODO2", "NODO3", "NODO4", "NODO5"],
  "nodos": [
    {"nodo": "NODO1", "success": true, "registros": 45},
    {"nodo": "NODO2", "success": true, "registros": 32}
  ]
}
```

### 2. Ver nodos disponibles

```bash
curl http://localhost:5000/api/gateway/nodes
```

### 3. Análisis de distribución

```bash
curl "http://localhost:5000/api/gateway/nodes?comparison=true"
```

Muestra qué nodos están en cada tabla (A, B, C).

### 4. Procesar un nodo específico

```bash
curl "http://localhost:5000/api/gateway/process?nodo=NODO1"
```

### 5. Estado de un nodo

```bash
curl "http://localhost:5000/api/gateway/status?nodo=NODO1"
```

### 6. Health check

```bash
curl http://localhost:5000/api/gateway/health
```

---

## 🔄 Los 6 Pasos de Sincronización

Cada nodo se procesa con este flujo automático:

```
PASO 1: Revisar Tiempo (últimos 10 minutos)
PASO 2: Detectar Cierres Automáticos
PASO 3: Sincronizar B → C (carga automática)
PASO 4: Aplicar Prioridad A → C ⭐ (gestión manual)
PASO 5: Volcado a Fallas
PASO 6: Retornar Datos (tickets abiertos)
```

---

## 🔍 Monitoreo

### Ver logs en tiempo real

```bash
tail -f logs/app.log
```

### Log típico

```
INFO:root:Buscando nodos en Tabla A (TCK)...
INFO:root:Encontrados 3 nodos únicos en Tabla A
INFO:root:TOTAL: 5 nodos únicos encontrados
INFO:root:Procesando nodo: NODO1
INFO:root:Procesamiento automático completado: 5/5 exitosos
```

---

## 🛡️ Seguridad

✅ Parámetros preparados (previene SQL injection)  
✅ Context managers (cierre automático de conexiones)  
✅ Credenciales separadas  
✅ Validación de entrada  
✅ Logging de auditoría  

---

## 📊 Nodos Dinámicos

El sistema **busca automáticamente** qué nodos procesar:

```sql
SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_tck]
UNION
SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_tiv]
UNION
SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_consolidado]
```

**Ventajas:**
- No necesita mantenimiento manual
- Se adapta automáticamente a cambios
- Procesa solo nodos que tienen datos

---

## 🧪 Testing

```bash
python test_simple.py -v
python test_nodos_dinamicos.py -v
```

---

## 🚀 Automatizar Ejecución

### Linux/macOS: Cron

```bash
crontab -e

# Procesar cada hora
0 * * * * curl http://localhost:5000/api/gateway/process-all

# Cada 15 minutos
*/15 * * * * curl http://localhost:5000/api/gateway/process-all
```

### Windows: Task Scheduler

Crear tarea programada que ejecute:
```
curl http://localhost:5000/api/gateway/process-all
```

---

## 📦 Dependencias

```
pyodbc==5.1.0
Flask==3.1.2
requests==2.31.0
```

---

## ⚠️ Troubleshooting

| Error | Solución |
|-------|----------|
| Login failed (18456) | Verifica usuario/contraseña en `config/credentials.py` |
| ODBC Driver not found | `brew install msodbcsql17` (macOS) |
| No hay nodos | Verifica que las tablas tengan columna `Nodo` con datos |

---

## ❓ FAQ

**P: ¿Qué pasa si un nodo falla?**  
R: El sistema continúa con los siguientes. El error se registra en logs.

**P: ¿Cómo agrego un nuevo nodo?**  
R: Simplemente inserta datos con ese nodo. El sistema lo detecta automáticamente.

**P: ¿Cuánto tiempo toma?**  
R: Típicamente 1-5 minutos para 5 nodos (depende del volumen).

**P: ¿Dónde están los logs?**  
R: En `logs/app.log`. Usa `tail -f logs/app.log` para verlos en tiempo real.

---

## 📚 Documentación Técnica

Para detalles técnicos completos: → Ver `DOCUMENTACION_API_GATEWAY.md`

---

**Versión:** 2.0.0  
**Última actualización:** 12 de febrero de 2026
