"""
Módulo de inyección de datos
Inserta los datos comparados en tabla3 de forma eficiente
"""

import logging
from src.database import DatabaseManager
from src.comparison import TableComparator
from config.credentials import TABLES_CONFIG, PROCESSING_CONFIG

logger = logging.getLogger(__name__)


class DataInjector:
    """Inyecta los datos comparados en tabla3"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.comparator = TableComparator()
        self.config = TABLES_CONFIG

    def prepare_result_table(self) -> bool:
        """
        Verifica o crea la tabla de resultados
        """
        result_table = self.config["result_table"]

        if self.db_manager.table_exists(result_table):
            logger.info(f"Tabla {result_table} ya existe")
            return True

        logger.info(f"Creando tabla {result_table}")
        
        # Obtener estructura de tabla origen
        source_columns = self.comparator.get_table_columns(
            self.config["source_table"]
        )

        if not source_columns:
            logger.error("No se pudieron obtener columnas de tabla origen")
            return False

        # Construir CREATE TABLE
        columns_def = ", ".join([f"[{col}] NVARCHAR(MAX)" for col in source_columns])
        create_query = (
            f"CREATE TABLE {result_table} ("
            f"ID INT PRIMARY KEY IDENTITY(1,1), "
            f"{columns_def}, "
            f"[TIPO_COMPARACION] NVARCHAR(50)"
            f")"
        )

        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute(create_query)
                cursor.commit()
            logger.info(f"Tabla {result_table} creada exitosamente")
            return True
        except Exception as e:
            logger.error(f"Error creando tabla: {e}")
            return False

    def inject_data(self) -> bool:
        """
        Inyecta los datos comparados en tabla3
        """
        try:
            # Preparar tabla de resultados
            if not self.prepare_result_table():
                logger.error("No se pudo preparar tabla de resultados")
                return False

            # Obtener datos preparados
            injection_data = self.comparator.prepare_injection_data()

            if not injection_data:
                logger.warning("No hay datos para inyectar")
                return True

            # Obtener columnas
            source_columns = self.comparator.get_table_columns(
                self.config["source_table"]
            )
            columns_str = ", ".join([f"[{col}]" for col in source_columns])

            # Construir INSERT query
            placeholders = ", ".join(["?" for _ in source_columns + ["TIPO_COMPARACION"]])
            insert_query = (
                f"INSERT INTO {self.config['result_table']} "
                f"({columns_str}, [TIPO_COMPARACION]) "
                f"VALUES ({placeholders})"
            )

            # Inyectar en lotes
            inserted = self.db_manager.execute_insert(
                insert_query, injection_data, PROCESSING_CONFIG["batch_size"]
            )

            logger.info(f"Inyección completada: {inserted} registros insertados")
            return True

        except Exception as e:
            logger.error(f"Error durante inyección: {e}")
            return False

    def clear_result_table(self) -> bool:
        """
        Limpia la tabla de resultados (útil para re-ejecutar)
        """
        try:
            result_table = self.config["result_table"]
            
            if not self.db_manager.table_exists(result_table):
                logger.warning(f"Tabla {result_table} no existe")
                return True

            with self.db_manager.get_cursor() as cursor:
                cursor.execute(f"TRUNCATE TABLE {result_table}")
                cursor.commit()

            logger.info(f"Tabla {result_table} limpiada")
            return True

        except Exception as e:
            logger.error(f"Error limpiando tabla: {e}")
            return False
