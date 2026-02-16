"""
Optimización de Sincronización - Sistema de Caché Inteligente
Evita re-procesar datos ya comparados usando checksums
"""

import hashlib
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import logging

logger = logging.getLogger(__name__)


class SyncCache:
    """
    Sistema de caché inteligente para evitar re-procesamiento
    Usa checksums para detectar cambios sin cargar datos completos
    """
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        # Apuntar a la tabla que ya creaste en dbo
        self.cache_table = "[dbo].[sync_cache]"
        self.ensure_cache_table()
    
    def ensure_cache_table(self):
        """Crea tabla de caché si no existe"""
        create_cache = f"""
            IF NOT EXISTS (
                SELECT * 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = 'sync_cache'
            )
            CREATE TABLE {self.cache_table} (
                cache_id INT PRIMARY KEY IDENTITY(1,1),
                nodo NVARCHAR(50) NOT NULL,
                tabla_origen NVARCHAR(50) NOT NULL,
                checksum_anterior NVARCHAR(64),
                checksum_actual NVARCHAR(64),
                registros_procesados INT DEFAULT 0,
                fecha_ultimo_procesamiento DATETIME DEFAULT GETDATE(),
                fecha_expiracion DATETIME,
                estado NVARCHAR(20) DEFAULT 'ACTIVO',
                CONSTRAINT uk_nodo_tabla UNIQUE(nodo, tabla_origen)
            )
        """
        try:
            self.db_manager.execute_query(create_cache)
            logger.info("Tabla de caché verificada/creada (si no existía)")
        except Exception as e:
            logger.warning(f"Error al crear/verificar tabla de caché: {e}")
    
    def calcular_checksum(self, data: List[tuple]) -> str:
        """
        Calcula checksum SHA256 de los datos
        Rápido y detecta cambios
        """
        if not data:
            return hashlib.sha256(b"empty").hexdigest()
        
        # Convertir datos a string JSON para hash consistente
        json_str = json.dumps(str(data), sort_keys=True, default=str)
        return hashlib.sha256(json_str.encode()).hexdigest()
    
    def get_cache_status(self, nodo: str, tabla: str) -> Optional[Dict]:
        """Obtiene estado del caché para un nodo/tabla"""
        query = f"""
            SELECT checksum_anterior, checksum_actual, 
                   fecha_ultimo_procesamiento, registros_procesados,
                   estado
            FROM {self.cache_table}
            WHERE nodo = ? AND tabla_origen = ?
            AND estado = 'ACTIVO'
        """
        try:
            result = self.db_manager.execute_query(query, (nodo, tabla))
            if result:
                row = result[0]
                return {
                    'checksum_anterior': row[0],
                    'checksum_actual': row[1],
                    'ultima_procesamiento': row[2],
                    'registros': row[3],
                    'estado': row[4]
                }
        except Exception as e:
            logger.warning(f"Error consultando caché: {e}")
        
        return None
    
    def actualizar_cache(self, nodo: str, tabla: str, 
                        checksum_nuevo: str, registros: int):
        """Actualiza o inserta registro en caché"""
        # Primero intenta UPDATE
        update_query = f"""
            UPDATE {self.cache_table}
            SET checksum_anterior = checksum_actual,
                checksum_actual = ?,
                registros_procesados = ?,
                fecha_ultimo_procesamiento = GETDATE(),
                fecha_expiracion = DATEADD(HOUR, 2, GETDATE())
            WHERE nodo = ? AND tabla_origen = ?
        """
        
        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute(update_query, (checksum_nuevo, registros, nodo, tabla))
                # Si no actualizó filas, insertar
                if cursor.rowcount == 0:
                    insert_query = f"""
                        INSERT INTO {self.cache_table}
                        (nodo, tabla_origen, checksum_anterior, checksum_actual, 
                         registros_procesados, fecha_expiracion, estado)
                        VALUES (?, ?, ?, ?, ?, DATEADD(HOUR, 2, GETDATE()), 'ACTIVO')
                    """
                    cursor.execute(insert_query, 
                                 (nodo, tabla, checksum_nuevo, checksum_nuevo, registros))
                # commit (seguir tu patrón actual)
                cursor.commit()
                logger.info(f"Caché actualizado: {nodo}/{tabla}")
        except Exception as e:
            logger.error(f"Error actualizando caché: {e}")
    
    def limpiar_cache_expirado(self):
        """Elimina entradas de caché expiradas"""
        delete_query = f"""
            DELETE FROM {self.cache_table}
            WHERE fecha_expiracion < GETDATE()
        """
        try:
            with self.db_manager.get_cursor() as cursor:
                cursor.execute(delete_query)
                cursor.commit()
                if cursor.rowcount > 0:
                    logger.info(f"Limpiados {cursor.rowcount} registros de caché expirados")
        except Exception as e:
            logger.warning(f"Error limpiando caché: {e}")


class ComparadorOptimizado:
    """
    Comparador de tablas OPTIMIZADO con:
    - Checksums para evitar re-procesamiento
    - Queries dinámicas por volumen
    - Batch processing inteligente
    """
    
    def __init__(self, db_manager, cache_manager):
        self.db_manager = db_manager
        self.cache = cache_manager
    
    def necesita_reprocesar(self, nodo: str, tabla_origen: str, 
                           checksum_actual: str) -> Tuple[bool, str]:
        """
        Determina si necesita reprocesar basado en checksum
        Retorna (necesita_reprocesar, razon)
        """
        cache_status = self.cache.get_cache_status(nodo, tabla_origen)
        
        if not cache_status:
            return True, "Sin caché previo (primera ejecución)"
        
        if cache_status.get('checksum_actual') == checksum_actual:
            return False, "Datos sin cambios desde último procesamiento"
        
        return True, "Cambios detectados en datos"
    
    def obtener_checksum_tabla(self, nodo: str, tabla: str) -> str:
        """
        Calcula un checksum agregado rápido de la tabla para el nodo
        """
        query = f"""
            SELECT CHECKSUM_AGG(BINARY_CHECKSUM(*)) as tabla_checksum
            FROM [tigostar].[{tabla}]
            WHERE Nodo = ?
        """
        try:
            result = self.db_manager.execute_query(query, (nodo,))
            if result and result[0] and result[0][0] is not None:
                return str(result[0][0])
        except Exception as e:
            logger.warning(f"Error calculando checksum: {e}")
        
        return ""
    
    def comparar_optimizado(self, nodo: str, tabla_a: str, tabla_b: str) -> Dict[str, Any]:
        """
        Comparación INTELIGENTE y RÁPIDA
        1. Calcula checksums
        2. Si no cambió, retorna desde caché
        3. Si cambió, procesa sólo lo necesario
        """
        logger.info(f"Iniciando comparación optimizada: {nodo}")
        
        # Paso 1: Calcular checksums RÁPIDOS
        checksum_a = self.obtener_checksum_tabla(nodo, tabla_a)
        checksum_b = self.obtener_checksum_tabla(nodo, tabla_b)
        checksum_combinado = hashlib.sha256(
            f"{checksum_a}_{checksum_b}".encode()
        ).hexdigest()
        
        # Paso 2: Verificar si necesita reprocesar
        necesita_reprocesar, razon = self.necesita_reprocesar(
            nodo, tabla_a, checksum_combinado
        )
        
        logger.info(f"Decisión para {nodo}: {razon}")
        
        if not necesita_reprocesar:
            # Usar datos en caché
            logger.info(f"✓ Usando caché para {nodo}")
            return {
                'success': True,
                'desde_cache': True,
                'razon': razon,
                'nodo': nodo
            }
        
        # Paso 3: Si necesita reprocesar, procesar cambios (JOIN por Ticket = Incident)
        logger.info(f"⚠ Reprocesando {nodo} - Cambios detectados")
        
        query = f"""
            SELECT A.*, B.*
            FROM [tigostar].[{tabla_a}] A
            FULL OUTER JOIN [tigostar].[{tabla_b}] B
                ON A.Ticket = B.Incident
            WHERE 
                (A.Nodo = ?)
                OR 
                (B.Nodo = ?)
        """
        
        try:
            result = self.db_manager.execute_query(query, (nodo, nodo))
            
            # Actualizar caché: guardamos checksum combinado y cantidad de filas procesadas
            self.cache.actualizar_cache(nodo, tabla_a, checksum_combinado, len(result) if result else 0)
            
            return {
                'success': True,
                'desde_cache': False,
                'registros_procesados': len(result) if result else 0,
                'razon': razon,
                'nodo': nodo
            }
        except Exception as e:
            logger.error(f"Error en comparación optimizada: {e}")
            return {'success': False, 'error': str(e)}
    
    def comparar_por_lotes(self, nodo: str, tabla_a: str, tabla_b: str,
                          batch_size: int = 1000) -> List[Dict]:
        """
        Comparación por lotes para tablas MUY GRANDES
        Procesa en chunks para no saturar memoria
        """
        resultados = []
        offset = 0
        
        # Ordenamos por el id combinado para que OFFSET/FETCH funcione con resultados determinísticos
        query_plantilla = f"""
            SELECT A.*, B.* 
            FROM [tigostar].[{tabla_a}] A
            FULL OUTER JOIN [tigostar].[{tabla_b}] B 
                ON A.Ticket = B.Incident
            WHERE A.Nodo = ? OR B.Nodo = ?
            ORDER BY ISNULL(B.Incident, A.Ticket)
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY
        """
        
        while True:
            try:
                result = self.db_manager.execute_query(
                    query_plantilla, 
                    (nodo, nodo, offset, batch_size)
                )
                
                if not result:
                    break
                
                resultados.append({
                    'batch': offset // batch_size + 1,
                    'registros': len(result),
                    'datos': result
                })
                
                offset += batch_size
                logger.info(f"Procesado lote {resultados[-1]['batch']} ({len(result)} registros)")
                
            except Exception as e:
                logger.error(f"Error en lote: {e}")
                break
        
        return resultados


class MonitorOptimizacion:
    """Monitorea y reporta optimizaciones en tiempo real"""
    
    def __init__(self):
        self.stats = {
            'total_comparaciones': 0,
            'desde_cache': 0,
            'reprocesadas': 0,
            'tiempo_ahorrado': 0
        }
    
    def registrar_comparacion(self, desde_cache: bool, tiempo_procesamiento: float):
        """Registra estadísticas de comparación"""
        self.stats['total_comparaciones'] += 1
        
        if desde_cache:
            self.stats['desde_cache'] += 1
            # Asumir que sin caché hubiera tomado 10 segundos
            self.stats['tiempo_ahorrado'] += 10
        else:
            self.stats['reprocesadas'] += 1
            self.stats['tiempo_ahorrado'] += max(0, 10 - tiempo_procesamiento)
    
    def reporte(self) -> Dict:
        """Genera reporte de optimizaciones"""
        total = self.stats['total_comparaciones']
        if total == 0:
            return {}
        
        porcentaje_cache = (self.stats['desde_cache'] / total) * 100
        
        return {
            'total_comparaciones': total,
            'desde_cache': self.stats['desde_cache'],
            'reprocesadas': self.stats['reprocesadas'],
            'porcentaje_cache': f"{porcentaje_cache:.1f}%",
            'tiempo_ahorrado_segundos': self.stats['tiempo_ahorrado']
        }
