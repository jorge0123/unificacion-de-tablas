"""
Módulo de conexión a SQL Server
Maneja la conexión, consultas y cierre de conexiones de forma eficiente
"""

import pyodbc
import logging
from contextlib import contextmanager
from config.credentials import DB_CONFIG, PROCESSING_CONFIG

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestor de conexiones a SQL Server con context manager"""

    def __init__(self):
        self.config = DB_CONFIG
        self.connection_string = self._build_connection_string()

    def _build_connection_string(self) -> str:
        """Construye la cadena de conexión correcta para SQL Server"""
        return (
            f"DRIVER={{{self.config['driver']}}};"
            f"SERVER={self.config['server']},{self.config['port']};"
            f"DATABASE={self.config['database']};"
            f"UID={self.config['username']};"
            f"PWD={self.config['password']};"
            "Encrypt=yes;"
            "TrustServerCertificate=yes;"
        )

    @contextmanager
    def get_connection(self):
        """Context manager para conexión segura"""
        conn = None
        try:
            conn = pyodbc.connect(self.connection_string, timeout=10)
            yield conn
        except pyodbc.Error as e:
            logger.error(f"Error de conexión: {e}")
            raise
        finally:
            if conn:
                conn.close()

    @contextmanager
    def get_cursor(self):
        """Context manager para cursor con conexión automática"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            finally:
                cursor.close()

    def execute_query(self, query: str, params=None):
        """Ejecuta una consulta SELECT y retorna resultados"""
        try:
            with self.get_cursor() as cursor:
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                return cursor.fetchall()
        except pyodbc.Error as e:
            logger.error(f"Error ejecutando query: {e}")
            raise

    def execute_insert(self, query: str, data, batch_size=None):
        """Inserta datos en lotes para mayor eficiencia"""
        batch_size = batch_size or PROCESSING_CONFIG["batch_size"]
        inserted_count = 0

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                for i in range(0, len(data), batch_size):
                    batch = data[i : i + batch_size]
                    cursor.executemany(query, batch)
                    conn.commit()
                    inserted_count += len(batch)
                    logger.info(f"Insertados {inserted_count} registros")

                logger.info(f"Total insertados: {inserted_count}")
                return inserted_count

        except pyodbc.Error as e:
            logger.error(f"Error en inserción: {e}")
            raise

    def table_exists(self, table_name: str) -> bool:
        """Verifica si una tabla existe"""
        # Separar esquema y nombre de tabla
        if '.' in table_name:
            schema, table = table_name.split('.')
        else:
            schema, table = 'dbo', table_name
            
        query = (
            "SELECT 1 FROM information_schema.TABLES "
            "WHERE TABLE_NAME = ? AND TABLE_SCHEMA = ?"
        )
        try:
            result = self.execute_query(query, (table, schema))
            return len(result) > 0
        except Exception as e:
            logger.error(f"Error verificando tabla: {e}")
            return False
