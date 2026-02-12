"""
API Gateway - Motor Integrado y Seguro
Implementa la lógica de sincronización entre tablas de forma segura y eficiente
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from src.database import DatabaseManager
from config.credentials import TABLES_CONFIG

logger = logging.getLogger(__name__)


class APIGateway:
    """Motor de sincronización entre tablas"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config = TABLES_CONFIG

    def process_node(self, nodo: str) -> Dict[str, Any]:
        """
        Procesa un nodo específico ejecutando el flujo completo de sincronización
        """
        response = {"success": True, "data": []}

        if not nodo or not nodo.strip():
            return {"success": False, "error": "Nodo vacio"}

        try:
            # PASO 1: REVISAR TIEMPO - Verificar si hay actualizaciones recientes
            logger.info(f"PASO 1: Revisando tiempo para nodo {nodo}")
            check = """
                SELECT TOP 1 Ultima_Actualizacion 
                FROM [tigostar].[homeb2c_consolidado] 
                WHERE Ultima_Actualizacion > DATEADD(MINUTE, -10, GETDATE())
            """
            try:
                res_check = self.db_manager.execute_query(check)
                if not res_check:
                    logger.warning("No hay actualizaciones recientes")
            except Exception as e:
                logger.warning(f"Error en verificación de tiempo: {e}")

            # PASO 2: Detectar Cierres Automáticos
            # Busca tickets que desaparecieron de la carga automática (B) 
            # y no están abiertos en gestión de equipo (A)
            logger.info("PASO 2: Detectando cierres automáticos")
            update_cierres = """
                UPDATE C 
                SET C.Fecha_Cierre = GETDATE(), 
                    C.Status = 'CLOSED', 
                    C.Ultima_Actualizacion = GETDATE() 
                FROM [tigostar].[homeb2c_consolidado] C 
                WHERE C.Fecha_Cierre IS NULL 
                AND NOT EXISTS (
                    SELECT 1 FROM [tigostar].[homeb2c_tiv] B 
                    WHERE B.Incident = C.Incident
                ) 
                AND NOT EXISTS (
                    SELECT 1 FROM [tigostar].[homeb2c_tck] A 
                    WHERE A.Ticket = C.Incident AND A.Cierre_Evento IS NULL
                )
            """
            try:
                self._execute_update(update_cierres)
                logger.info("Cierres automáticos detectados y actualizados")
            except Exception as e:
                logger.error(f"Error en detección de cierres: {e}")

            # PASO 3: Sincronizar Carga Automática (B -> C)
            # Merge para mantener C igual a B
            logger.info("PASO 3: Sincronizando carga automática (B -> C)")
            merge_sync = """
                MERGE [tigostar].[homeb2c_consolidado] AS TGT 
                USING [tigostar].[homeb2c_tiv] AS SRC 
                ON (TGT.Incident = SRC.Incident) 
                WHEN MATCHED THEN 
                    UPDATE SET TGT.Status = SRC.Status, 
                               TGT.Ultima_Actualizacion = GETDATE() 
                WHEN NOT MATCHED THEN 
                    INSERT (Incident, Summary, Reported_By, Reported_Date, Nodo, Status, Owner, Owner_Group, Ultima_Actualizacion) 
                    VALUES (SRC.Incident, SRC.Summary, SRC.Reported_By, SRC.Reported_Date, SRC.Nodo, SRC.Status, SRC.Owner, SRC.Owner_Group, GETDATE());
            """
            try:
                self._execute_update(merge_sync)
                logger.info("Sincronización de carga automática completada")
            except Exception as e:
                logger.error(f"Error en sincronización B->C: {e}")

            # PASO 4: Prioridad Gestión de Equipo (A -> C)
            # La gestión manual de equipo tiene prioridad
            logger.info("PASO 4: Aplicando prioridad gestión de equipo (A -> C)")
            update_gestion = """
                UPDATE C 
                SET C.Gestionado_En_A = 1, 
                    C.Status = A.Estado_Evento, 
                    C.Owner = A.Tecnico, 
                    C.Fecha_Cierre = A.Cierre_Evento, 
                    C.Ultima_Actualizacion = GETDATE() 
                FROM [tigostar].[homeb2c_consolidado] C 
                INNER JOIN [tigostar].[homeb2c_tck] A 
                ON C.Incident = A.Ticket
            """
            try:
                self._execute_update(update_gestion)
                logger.info("Prioridad de gestión de equipo aplicada")
            except Exception as e:
                logger.error(f"Error en prioridad A->C: {e}")

            # PASO 5: Volcado a Fallas Masivas (C -> homecc_fal)
            # Solo fallas y mantenimientos
            logger.info("PASO 5: Volcando a fallas masivas (C -> homecc_fal)")
            merge_fallas = """
                MERGE [tigostar].[homecc_fal] AS FAL 
                USING (
                    SELECT CON.* 
                    FROM [tigostar].[homeb2c_consolidado] AS CON 
                    INNER JOIN [tigostar].[homeb2c_mtv_a] AS MTV 
                    ON CON.Summary = MTV.MOTIVO_APERTURA 
                    WHERE MTV.CATEGORIA IN ('FALLA', 'MANTENIMIENTO', 'MANTENIMIENTO CON AFECTACION', 'MANTENIMIENTO PREVENTIVO') 
                    AND CON.Ultima_Actualizacion >= DATEADD(MINUTE, -15, GETDATE())
                ) AS SOURCE 
                ON (FAL.Ticket = SOURCE.Incident AND FAL.Nodo = SOURCE.Nodo) 
                WHEN MATCHED THEN 
                    UPDATE SET FAL.Estado = SOURCE.Status, 
                               FAL.Cierre_Evento = SOURCE.Fecha_Cierre, 
                               FAL.Fecha_Fin_Falla = SOURCE.Fecha_Cierre 
                WHEN NOT MATCHED THEN 
                    INSERT (Ticket, Motivo_Apertura, Direccion, Estado, Inicio_Evento, Cierre_Evento, Nodo, Fecha_Fin_Falla, Fecha_Creado, Crea, Clientes_Afectados) 
                    VALUES (SOURCE.Incident, SOURCE.Summary, '', SOURCE.Status, SOURCE.Reported_Date, SOURCE.Fecha_Cierre, SOURCE.Nodo, SOURCE.Fecha_Cierre, SOURCE.Reported_Date, SOURCE.Owner, '0');
            """
            try:
                self._execute_update(merge_fallas)
                logger.info("Volcado a fallas masivas completado")
            except Exception as e:
                logger.error(f"Error en volcado a fallas: {e}")

            # PASO 6: Consulta Final - Retornar datos
            logger.info(f"PASO 6: Obteniendo datos finales para nodo {nodo}")
            sql_data = """
                SELECT Nodo, 
                       Incident AS Ticket, 
                       Summary AS Tipo, 
                       Status AS Estado, 
                       Reported_Date AS Fecha, 
                       Owner 
                FROM [tigostar].[homeb2c_consolidado] 
                WHERE Nodo = ? AND Fecha_Cierre IS NULL
            """
            try:
                results = self.db_manager.execute_query(sql_data, (nodo,))
                for row in results:
                    response["data"].append(self._format_row(row))
                logger.info(f"Obtenidos {len(response['data'])} registros")
            except Exception as e:
                logger.error(f"Error obteniendo datos finales: {e}")
                response["success"] = False
                response["error"] = str(e)

        except Exception as e:
            logger.error(f"Error en procesamiento de nodo: {e}")
            response["success"] = False
            response["error"] = str(e)

        return response

    def _execute_update(self, query: str) -> None:
        """Ejecuta una consulta de actualización (UPDATE/MERGE/INSERT)"""
        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute(query)
                cursor.commit()
        except Exception as e:
            logger.error(f"Error ejecutando update: {e}")
            raise

    def _format_row(self, row: tuple) -> Dict[str, Any]:
        """Formatea una fila de base de datos"""
        # Convertir datetime a string si es necesario
        formatted = {}
        column_names = ["Nodo", "Ticket", "Tipo", "Estado", "Fecha", "Owner"]
        
        for i, value in enumerate(row):
            if i < len(column_names):
                if isinstance(value, datetime):
                    formatted[column_names[i]] = value.strftime('%Y-%m-%d %H:%M:%S')
                else:
                    formatted[column_names[i]] = value
        
        return formatted

    def get_node_status(self, nodo: str) -> Dict[str, Any]:
        """Obtiene el estado actual de un nodo"""
        try:
            query = """
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN Fecha_Cierre IS NULL THEN 1 ELSE 0 END) as abiertos,
                       SUM(CASE WHEN Fecha_Cierre IS NOT NULL THEN 1 ELSE 0 END) as cerrados
                FROM [tigostar].[homeb2c_consolidado]
                WHERE Nodo = ?
            """
            result = self.db_manager.execute_query(query, (nodo,))
            if result:
                row = result[0]
                return {
                    "success": True,
                    "nodo": nodo,
                    "total": row[0] or 0,
                    "abiertos": row[1] or 0,
                    "cerrados": row[2] or 0
                }
        except Exception as e:
            logger.error(f"Error obteniendo estado del nodo: {e}")
        
        return {"success": False, "error": "No se pudo obtener estado del nodo"}
