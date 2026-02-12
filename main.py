"""
Script principal
Orquesta el flujo de comparación e inyección de datos usando el API Gateway
"""

import sys
from src.logger import setup_logger
from src.api_gateway import APIGateway
from config.credentials import DB_CONFIG

logger = setup_logger(__name__)

def main():
    """
    Función principal que ejecuta el proceso completo
    """
    logger.info("=" * 60)
    logger.info("Iniciando API Gateway - Motor Integrado y Seguro")
    logger.info("=" * 60)

    try:
        # Validar credenciales
        if not DB_CONFIG["server"] or DB_CONFIG["server"] == "tu_servidor":
            logger.error("⚠️  Credenciales no configuradas. Edita config/credentials.py")
            sys.exit(1)

        # Crear gateway
        gateway = APIGateway()

        # Procesar nodos (ejemplo con nodos de prueba)
        # En producción, estos vendrían de una solicitud HTTP
        nodos = ["NODO1", "NODO2", "NODO3"]  # Ajusta según tus nodos reales
        
        all_success = True
        for nodo in nodos:
            logger.info(f"\nProcesando nodo: {nodo}")
            result = gateway.process_node(nodo)
            
            if result["success"]:
                logger.info(f"✅ Nodo {nodo} procesado exitosamente")
                logger.info(f"   Registros obtenidos: {len(result.get('data', []))}")
            else:
                logger.error(f"❌ Error en nodo {nodo}: {result.get('error', 'Error desconocido')}")
                all_success = False

        if all_success:
            logger.info("\n✅ Proceso completado exitosamente")
            return 0
        else:
            logger.error("\n❌ El proceso encontró errores")
            return 1

    except Exception as e:
        logger.error(f"❌ Error inesperado: {e}")
        return 1
    finally:
        logger.info("=" * 60)
        logger.info("Proceso finalizado")
        logger.info("=" * 60)


if __name__ == "__main__":
    sys.exit(main())
