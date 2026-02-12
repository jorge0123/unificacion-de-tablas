"""
Configuración de logging
Maneja logs de forma ligera y eficiente
"""

import logging
import logging.handlers
from pathlib import Path
from config.credentials import PROCESSING_CONFIG

# Crear directorio de logs si no existe
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)

LOG_FILE = LOG_DIR / "app.log"


def setup_logger(name: str) -> logging.Logger:
    """
    Configura logger con rotación de archivos
    """
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(PROCESSING_CONFIG["log_level"])

    # Handler para archivo (rotación cada 5MB)
    file_handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=5 * 1024 * 1024, backupCount=3
    )

    # Handler para consola
    console_handler = logging.StreamHandler()

    # Formato
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
