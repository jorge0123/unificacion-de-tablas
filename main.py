"""
Script principal
Orquesta el flujo de comparación e inyección de datos
"""

import sys
from src.logger import setup_logger
from src.injection import DataInjector
from config.credentials import DB_CONFIG

logger = setup_logger(__name__)

def main():
    """
    Función principal que ejecuta el proceso completo
    """
    logger.info("=" * 60)
    logger.info("Iniciando proceso de comparación e inyección de tablas")
    logger.info("=" * 60)

    try:
        # Validar credenciales
        if not DB_CONFIG["server"] or DB_CONFIG["server"] == "tu_servidor":
            logger.error("⚠️  Credenciales no configuradas. Edita config/credentials.py")
            sys.exit(1)

        # Crear inyector
        injector = DataInjector()

        # Opción 1: Limpiar tabla anterior y re-inyectar
        # Descomenta si quieres limpiar:
        # injector.clear_result_table()

        # Ejecutar inyección
        success = injector.inject_data()

        if success:
            logger.info("✅ Proceso completado exitosamente")
            return 0
        else:
            logger.error("❌ El proceso encontró errores")
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
