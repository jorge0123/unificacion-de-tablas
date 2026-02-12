# 📊 Comparador e Inyector de Tablas – SQL Server

Sistema ligero y eficiente desarrollado en Python para comparar dos tablas en SQL Server e inyectar los resultados en una tercera tabla, utilizando conexiones seguras con context managers y procesamiento por lotes.

---

## 🏗️ Estructura del Proyecto

.
├── config/
│ ├── credentials.py # Configuración de base de datos y procesamiento
│ └── init.py
├── src/
│ ├── database.py # Gestor de conexiones (context managers)
│ ├── comparison.py # Lógica de comparación
│ ├── injection.py # Inyección de datos en lotes
│ ├── logger.py # Sistema de logging rotativo
│ ├── api.py # (Opcional) API con FastAPI
│ └── init.py
├── logs/ # Archivos de logs
├── main.py # Script principal
├── requirements.txt # Dependencias
└── README.md


---

## ⚙️ Configuración Inicial

### 1️⃣ Instalar dependencias

```bash
pip install -r requirements.txt

2️⃣ Configurar credenciales

Edita el archivo:

config/credentials.py

Ejemplo:

DB_CONFIG = {
    "driver": "ODBC Driver 17 for SQL Server",
    "server": "localhost",        # IP o nombre del servidor
    "port": "1433",               # Puerto (ejemplo: 21408 si es personalizado)
    "database": "TStest",
    "username": "tu_usuario",
    "password": "tu_password",
}

TABLES_CONFIG = {
    "source_table": "tabla1",
    "comparison_table": "tabla2",
    "result_table": "tabla3",
}

PROCESSING_CONFIG = {
    "batch_size": 1000,
    "enable_logging": True,
    "log_level": "INFO",
}

⚠️ Recomendación:
No subas credenciales reales a GitHub. Usa variables de entorno en producción.
3️⃣ Verificar ODBC Driver
Windows

Asegúrate de tener instalado:

ODBC Driver 17 for SQL Server

macOS

brew install unixodbc
brew install msodbcsql17

Verificar instalación:

odbcinst -j

🚀 Ejecución
▶️ Ejecutar como Script

python main.py

🌐 Ejecutar como API (Opcional)

Si el proyecto incluye FastAPI:

uvicorn src.api:app --reload --port 8000

Abrir en navegador:

http://127.0.0.1:8000

🔄 Flujo de Trabajo

1️⃣ Conexión a SQL Server usando pyodbc
2️⃣ Lectura de tabla origen
3️⃣ Lectura de tabla comparación
4️⃣ Comparación en memoria optimizada
5️⃣ Clasificación de resultados
6️⃣ Inserción por lotes en tabla destino
7️⃣ Registro de logs
📋 Clasificación de Resultados
Estado	Descripción
SOLO_ORIGEN	Registro solo existe en tabla1
SOLO_COMPARACION	Registro solo existe en tabla2
COINCIDENTE	Registro existe en ambas tablas
⚡ Características Técnicas

    ✅ Context Managers (cierre automático de conexiones)

    ✅ Inserción por lotes configurable

    ✅ Logging rotativo automático

    ✅ Comparación eficiente con estructuras tipo set (O(1))

    ✅ Manejo estructurado de errores

    ✅ Arquitectura modular

🔧 Personalización
Cambiar tamaño de lote

En config/credentials.py:

PROCESSING_CONFIG = {
    "batch_size": 500,
}

    Lote pequeño → menor consumo de memoria

    Lote grande → mayor velocidad de inserción

Limpiar tabla de resultados antes de insertar

En main.py:

injector.clear_result_table()

📝 Logs

Ubicación:

logs/app.log

Configuración:

    Nivel por defecto: INFO

    Cambiar a DEBUG para mayor detalle

    Rotación automática (máximo 5MB por archivo)

🐛 Solución de Problemas
❌ Error: Login failed (18456)

    Verifica usuario y contraseña

    Confirma que SQL Server permita autenticación SQL

    Verifica puerto configurado

    Prueba conexión en SSMS

❌ Error: ODBC Driver not found

Instalar driver:

Windows:
Descargar desde Microsoft.

macOS:

brew install msodbcsql17

❌ Lentitud en inserciones

    Reduce batch_size

    Verifica índices en tabla destino

    Evita consultas innecesarias

📦 Dependencias

    pyodbc

    fastapi (opcional)

    uvicorn (opcional)

    logging (incluido en Python)

🛡️ Buenas Prácticas

    No subir credenciales reales

    Usar variables de entorno en producción

    Indexar columnas usadas en comparación

    Mantener logs habilitados en entorno productivo

📄 Licencia

MIT License