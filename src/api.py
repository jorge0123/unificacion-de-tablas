# src/api.py
from fastapi import FastAPI, HTTPException, Query
from datetime import datetime
import logging
from src.database import DatabaseManager  # <-- usa tu clase existente

app = FastAPI(title="API Gateway - Motor Integrado")
logger = logging.getLogger("api_gateway")
logger.setLevel(logging.INFO)

db = DatabaseManager()  # instancia con la configuración que ya carga desde config.credentials


def _serialize_row(columns, row):
    """Convierte una fila (pyodbc.Row / tuple) a dict cuidando datetimes."""
    record = {}
    for col_name, value in zip(columns, row):
        if isinstance(value, datetime):
            record[col_name] = value.strftime("%Y-%m-%d %H:%M:%S")
        else:
            record[col_name] = value
    return record


@app.get("/tickets")
def obtener_tickets(nodo: str = Query(..., min_length=1)):
    if not nodo:
        raise HTTPException(status_code=400, detail="Nodo vacío")

    try:
        # Paso 1: revisar última actualización
        with db.get_connection() as conn:
            cursor = conn.cursor()

            check_sql = """
            SELECT TOP 1 Ultima_Actualizacion
            FROM tigostar.homeb2c_consolidado
            WHERE Ultima_Actualizacion > DATEADD(MINUTE, -10, GETDATE())
            """
            cursor.execute(check_sql)
            last = cursor.fetchone()
            if not last:
                # Si prefieres no abortar, puedes comentar la siguiente línea y continuar.
                return {"success": False, "error": "Datos no actualizados en los últimos 10 minutos"}

            # PASO 2 - Cierres automáticos (UPDATE)
            cursor.execute("""
            UPDATE C
            SET C.Fecha_Cierre = GETDATE(),
                C.Status = 'CLOSED',
                C.Ultima_Actualizacion = GETDATE()
            FROM tigostar.homeb2c_consolidado C
            WHERE C.Fecha_Cierre IS NULL
              AND NOT EXISTS (SELECT 1 FROM tigostar.homeb2c_tiv B WHERE B.Incident = C.Incident)
              AND NOT EXISTS (SELECT 1 FROM tigostar.homeb2c_tck A WHERE A.Ticket = C.Incident AND A.Cierre_Evento IS NULL)
            """)
            conn.commit()

            # PASO 3 - MERGE TIV -> CONSOLIDADO
            cursor.execute("""
            MERGE tigostar.homeb2c_consolidado AS TGT
            USING tigostar.homeb2c_tiv AS SRC
              ON TGT.Incident = SRC.Incident
            WHEN MATCHED THEN
              UPDATE SET TGT.Status = SRC.Status, TGT.Ultima_Actualizacion = GETDATE()
            WHEN NOT MATCHED THEN
              INSERT (Incident, Summary, Reported_By, Reported_Date, Nodo, Status, Owner, Owner_Group, Ultima_Actualizacion)
              VALUES (SRC.Incident, SRC.Summary, SRC.Reported_By, SRC.Reported_Date, SRC.Nodo, SRC.Status, SRC.Owner, SRC.Owner_Group, GETDATE());
            """)
            conn.commit()

            # PASO 4 - Prioridad gestión manual (A -> C)
            cursor.execute("""
            UPDATE C
            SET C.Gestionado_En_A = 1,
                C.Status = A.Estado_Evento,
                C.Owner = A.Tecnico,
                C.Fecha_Cierre = A.Cierre_Evento,
                C.Ultima_Actualizacion = GETDATE()
            FROM tigostar.homeb2c_consolidado C
            INNER JOIN tigostar.homeb2c_tck A ON C.Incident = A.Ticket
            """)
            conn.commit()

            # PASO 5 - Volcado a homecc_fal (MERGE)
            cursor.execute("""
            MERGE tigostar.homecc_fal AS FAL
            USING (
                SELECT CON.*
                FROM tigostar.homeb2c_consolidado CON
                INNER JOIN tigostar.homeb2c_mtv_a MTV ON CON.Summary = MTV.MOTIVO_APERTURA
                WHERE MTV.CATEGORIA IN (
                    'FALLA', 'MANTENIMIENTO', 'MANTENIMIENTO CON AFECTACION', 'MANTENIMIENTO PREVENTIVO'
                )
                AND CON.Ultima_Actualizacion >= DATEADD(MINUTE, -15, GETDATE())
            ) AS SOURCE
            ON FAL.Ticket = SOURCE.Incident AND FAL.Nodo = SOURCE.Nodo
            WHEN MATCHED THEN
              UPDATE SET FAL.Estado = SOURCE.Status, FAL.Cierre_Evento = SOURCE.Fecha_Cierre, FAL.Fecha_Fin_Falla = SOURCE.Fecha_Cierre
            WHEN NOT MATCHED THEN
              INSERT (Ticket, Motivo_Apertura, Direccion, Estado, Inicio_Evento, Cierre_Evento, Nodo, Fecha_Fin_Falla, Fecha_Creado, Crea, Clientes_Afectados)
              VALUES (SOURCE.Incident, SOURCE.Summary, '', SOURCE.Status, SOURCE.Reported_Date, SOURCE.Fecha_Cierre, SOURCE.Nodo, SOURCE.Fecha_Cierre, SOURCE.Reported_Date, SOURCE.Owner, '0');
            """)
            conn.commit()

            # PASO 6 - Consulta final (SELECT parametrizado)
            select_sql = """
            SELECT Nodo,
                   Incident AS Ticket,
                   Summary AS Tipo,
                   Status AS Estado,
                   Reported_Date AS Fecha,
                   Owner
            FROM tigostar.homeb2c_consolidado
            WHERE Nodo = ?
              AND Fecha_Cierre IS NULL
            """
            cursor.execute(select_sql, (nodo,))
            rows = cursor.fetchall()
            columns = [c[0] for c in cursor.description] if cursor.description else []

            data = [_serialize_row(columns, row) for row in rows]

            return {"success": True, "data": data}

    except Exception as exc:
        logger.exception("Error en /tickets")
        raise HTTPException(status_code=500, detail=str(exc))
