"""
API Gateway - Motor Integrado y Seguro
Implementa la lógica de sincronización entre tablas de forma segura y eficiente
CON OPTIMIZACIÓN: Caché inteligente y checksums para evitar re-procesamiento
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any
from src.database import DatabaseManager
from src.optimizacion import SyncCache, ComparadorOptimizado, MonitorOptimizacion
from config.credentials import TABLES_CONFIG

logger = logging.getLogger(__name__)


class APIGateway:
    """Motor de sincronización entre tablas"""

    def __init__(self):
        self.db_manager = DatabaseManager()
        self.config = TABLES_CONFIG
        # Inicializar sistemas de optimización
        self.cache = SyncCache(self.db_manager)
        self.comparador = ComparadorOptimizado(self.db_manager, self.cache)
        self.monitor = MonitorOptimizacion()

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
            # PASO 3.1: Cerrar tickets si Status es CLOSED o RESOLVED
            logger.info("PASO 3.1: Marcando como cerrados por Status")

            close_by_status = """
                UPDATE C
                SET C.Fecha_Cierre = GETDATE(),
                    C.Ultima_Actualizacion = GETDATE()
                FROM [tigostar].[homeb2c_consolidado] C
                INNER JOIN [tigostar].[homeb2c_tiv] SRC
                    ON C.Incident = SRC.Incident
                WHERE C.Fecha_Cierre IS NULL
                AND UPPER(ISNULL(SRC.Status, C.Status)) IN ('CLOSED','RESOLVED')
            """
            try:
                self._execute_update(close_by_status)
            except Exception as e:
                logger.error(f"Error cerrando por Status: {e}")
            
            # PASO 3.2: Reabrir tickets si ya no están CLOSED ni RESOLVED
            logger.info("PASO 3.2: Reabriendo tickets si cambiaron de estado")

            reopen_by_status = """
                UPDATE C
                SET C.Fecha_Cierre = NULL,
                    C.Ultima_Actualizacion = GETDATE()
                FROM [tigostar].[homeb2c_consolidado] C
                INNER JOIN [TStest].[tigostar].[homeb2c_tiv] SRC
                    ON C.Incident = SRC.Incident
                WHERE C.Fecha_Cierre IS NOT NULL
                AND UPPER(ISNULL(SRC.Status,'')) NOT IN ('CLOSED','RESOLVED')
            """
            try:
                self._execute_update(reopen_by_status)
            except Exception as e:
                logger.error(f"Error reabriendo por Status: {e}")


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
                WHERE Nodo = ?
                AND Fecha_Cierre IS NULL
                AND UPPER(ISNULL(Status,'')) NOT IN ('CLOSED','RESOLVED')
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

    def get_all_nodes_from_database(self) -> List[str]:
        """
        Busca dinámicamente todos los nodos únicos de las tablas reales (A, B, C)
        Retorna una lista de nodos que existen en los datos
        """
        nodos_unicos = set()
        
        try:
            # Obtener nodos de Tabla A (TCK)
            logger.info("Buscando nodos en Tabla A (TCK)...")
            query_a = """
                SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_tck]
                WHERE Nodo IS NOT NULL
            """
            resultados_a = self.db_manager.execute_query(query_a)
            if resultados_a:
                for row in resultados_a:
                    if row[0]:
                        nodos_unicos.add(row[0].strip())
                logger.info(f"Encontrados {len([r for r in resultados_a])} nodos únicos en Tabla A")
            
            # Obtener nodos de Tabla B (TIV)
            logger.info("Buscando nodos en Tabla B (TIV)...")
            query_b = """
                SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_tiv]
                WHERE Nodo IS NOT NULL
            """
            resultados_b = self.db_manager.execute_query(query_b)
            if resultados_b:
                for row in resultados_b:
                    if row[0]:
                        nodos_unicos.add(row[0].strip())
                logger.info(f"Encontrados {len([r for r in resultados_b])} nodos únicos en Tabla B")
            
            # Obtener nodos de Tabla C (Consolidado)
            logger.info("Buscando nodos en Tabla C (Consolidado)...")
            query_c = """
                SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_consolidado]
                WHERE Nodo IS NOT NULL
            """
            resultados_c = self.db_manager.execute_query(query_c)
            if resultados_c:
                for row in resultados_c:
                    if row[0]:
                        nodos_unicos.add(row[0].strip())
                logger.info(f"Encontrados {len([r for r in resultados_c])} nodos únicos en Tabla C")
            
            # Retornar lista ordenada de nodos únicos
            nodos_finales = sorted(list(nodos_unicos))
            logger.info(f"TOTAL: {len(nodos_finales)} nodos únicos encontrados: {nodos_finales}")
            
            return nodos_finales
            
        except Exception as e:
            logger.error(f"Error buscando nodos: {e}")
            return []

    def get_nodes_comparison(self) -> Dict[str, Any]:
        """
        Compara qué nodos existen en cada tabla
        Retorna un diccionario mostrando la distribución de nodos
        """
        try:
            nodos_a = set()
            nodos_b = set()
            nodos_c = set()
            
            # Tabla A
            query_a = "SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_tck] WHERE Nodo IS NOT NULL"
            resultados_a = self.db_manager.execute_query(query_a)
            if resultados_a:
                nodos_a = {row[0].strip() for row in resultados_a if row[0]}
            
            # Tabla B
            query_b = "SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_tiv] WHERE Nodo IS NOT NULL"
            resultados_b = self.db_manager.execute_query(query_b)
            if resultados_b:
                nodos_b = {row[0].strip() for row in resultados_b if row[0]}
            
            # Tabla C
            query_c = "SELECT DISTINCT Nodo FROM [tigostar].[homeb2c_consolidado] WHERE Nodo IS NOT NULL"
            resultados_c = self.db_manager.execute_query(query_c)
            if resultados_c:
                nodos_c = {row[0].strip() for row in resultados_c if row[0]}
            
            return {
                "success": True,
                "tabla_a_tck": sorted(list(nodos_a)),
                "tabla_b_tiv": sorted(list(nodos_b)),
                "tabla_c_consolidado": sorted(list(nodos_c)),
                "todos_unicos": sorted(list(nodos_a | nodos_b | nodos_c)),
                "solo_en_a": sorted(list(nodos_a - nodos_b - nodos_c)),
                "solo_en_b": sorted(list(nodos_b - nodos_a - nodos_c)),
                "solo_en_c": sorted(list(nodos_c - nodos_a - nodos_b)),
                "en_a_y_b": sorted(list((nodos_a & nodos_b) - nodos_c)),
                "en_todas": sorted(list(nodos_a & nodos_b & nodos_c)),
                "total_unicos": len(nodos_a | nodos_b | nodos_c)
            }
        except Exception as e:
            logger.error(f"Error en comparación de nodos: {e}")
            return {"success": False, "error": str(e)}

    def process_node_optimizado(self, nodo: str) -> Dict[str, Any]:
        """
        Procesa un nodo usando CACHÉ INTELIGENTE
        - Si no cambió desde último procesamiento: retorna desde caché (RÁPIDO)
        - Si cambió: procesa solo cambios recientes (OPTIMIZADO)
        """
        inicio = time.time()
        response = {"success": True, "data": [], "optimizacion": {}}
        
        if not nodo or not nodo.strip():
            return {"success": False, "error": "Nodo vacio"}
        
        try:
            # PASO 0: Verificar caché inteligentemente
            logger.info(f"PASO 0 (OPTIMIZACIÓN): Verificando caché para {nodo}")
            
            resultado_comparacion = self.comparador.comparar_optimizado(
                nodo, "homeb2c_tck", "homeb2c_tiv"
            )
            
            response['optimizacion'] = {
                'desde_cache': resultado_comparacion.get('desde_cache', False),
                'razon': resultado_comparacion.get('razon', ''),
                'tiempo_ahorrado': 'sí' if resultado_comparacion.get('desde_cache') else 'no'
            }
            
            # Si está en caché y sin cambios, retornar directamente
            if resultado_comparacion.get('desde_cache'):
                tiempo_total = time.time() - inicio
                response['optimizacion']['tiempo_ms'] = int(tiempo_total * 1000)
                logger.info(f"✓ Procesamiento de {nodo} desde caché en {tiempo_total:.2f}s")
                self.monitor.registrar_comparacion(True, tiempo_total)
                return response
            
            # Si necesita reprocesar, ejecutar los 6 pasos normales
            logger.info(f"⚠ Necesario reprocesar {nodo} - ejecutando 6 pasos")
            
            # Ejecutar los 6 pasos normales pero ahora los datos ya fueron validados
            response_normal = self.process_node(nodo)
            response['data'] = response_normal.get('data', [])
            response['success'] = response_normal.get('success', False)
            
            tiempo_total = time.time() - inicio
            response['optimizacion']['tiempo_ms'] = int(tiempo_total * 1000)
            self.monitor.registrar_comparacion(False, tiempo_total)
            
            logger.info(f"Procesamiento de {nodo} completado en {tiempo_total:.2f}s")
            
        except Exception as e:
            logger.error(f"Error en procesamiento optimizado: {e}")
            response["success"] = False
            response["error"] = str(e)
        
        return response
    
    def get_optimization_stats(self) -> Dict[str, Any]:
        """Obtiene estadísticas de optimización"""
        return {
            'success': True,
            'estadisticas': self.monitor.reporte()
        }

