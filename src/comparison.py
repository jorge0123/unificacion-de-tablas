"""
Módulo de lógica de comparación de tablas
Compara tabla1 con tabla2 e identifica diferencias
"""

import logging
from typing import List, Dict, Tuple
from src.database import DatabaseManager
from config.credentials import TABLES_CONFIG

logger = logging.getLogger(__name__)


class TableComparator:
    """Compara dos tablas y prepara resultados para inyectar"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config = TABLES_CONFIG

    def get_table_columns(self, table_name: str) -> List[str]:
        """Obtiene las columnas de una tabla"""
        query = (
            "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
            "WHERE TABLE_NAME = ? AND TABLE_SCHEMA = 'dbo' "
            "ORDER BY ORDINAL_POSITION"
        )
        try:
            results = self.db_manager.execute_query(query, (table_name,))
            columns = [row[0] for row in results]
            logger.info(f"Columnas de {table_name}: {columns}")
            return columns
        except Exception as e:
            logger.error(f"Error obteniendo columnas: {e}")
            return []

    def get_table_data(self, table_name: str) -> List[Dict]:
        """Obtiene todos los datos de una tabla como diccionarios"""
        try:
            columns = self.get_table_columns(table_name)
            query = f"SELECT * FROM {table_name}"
            
            with self.db_manager.get_cursor() as cursor:
                cursor.execute(query)
                results = cursor.fetchall()
                
                # Convertir a diccionarios para comparación fácil
                data = []
                for row in results:
                    data.append(dict(zip(columns, row)))
                
                logger.info(f"Obtenidos {len(data)} registros de {table_name}")
                return data

        except Exception as e:
            logger.error(f"Error obteniendo datos: {e}")
            return []

    def compare_tables(self) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Compara tabla1 vs tabla2
        Retorna:
        - Registros solo en tabla1
        - Registros solo en tabla2
        - Registros coincidentes
        """
        source_data = self.get_table_data(self.config["source_table"])
        comparison_data = self.get_table_data(self.config["comparison_table"])

        logger.info(f"Comparando {len(source_data)} vs {len(comparison_data)} registros")

        # Convertir a sets para comparación rápida (usando representación en string)
        source_set = {str(item) for item in source_data}
        comparison_set = {str(item) for item in comparison_data}

        # Encontrar diferencias
        only_in_source = [
            item for item in source_data if str(item) not in comparison_set
        ]
        only_in_comparison = [
            item for item in comparison_data if str(item) not in source_set
        ]
        coincident = [item for item in source_data if str(item) in comparison_set]

        logger.info(
            f"Resultados - Solo en origen: {len(only_in_source)}, "
            f"Solo en comparación: {len(only_in_comparison)}, "
            f"Coincidentes: {len(coincident)}"
        )

        return only_in_source, only_in_comparison, coincident

    def prepare_injection_data(self) -> List[Tuple]:
        """
        Prepara datos para inyectar en tabla3
        Incluye marcas de qué tipo de comparación es
        """
        only_source, only_comp, coincident = self.compare_tables()

        injection_data = []

        # Agregar registro de origen no coincidente con marca
        for item in only_source:
            row_tuple = tuple(item.values()) + ("SOLO_ORIGEN",)
            injection_data.append(row_tuple)

        # Agregar registro de comparación no coincidente
        for item in only_comp:
            row_tuple = tuple(item.values()) + ("SOLO_COMPARACION",)
            injection_data.append(row_tuple)

        # Agregar registros coincidentes
        for item in coincident:
            row_tuple = tuple(item.values()) + ("COINCIDENTE",)
            injection_data.append(row_tuple)

        logger.info(f"Datos preparados para inyección: {len(injection_data)} registros")
        return injection_data
