import logging
import sys


def setup_logging(level: str = "INFO") -> None:
    """Configura el logging de toda la aplicación (llamar una vez al arranque)."""
    log_level = getattr(logging, level.upper(), logging.INFO)

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,  # permite reconfigurar si uvicorn ya tocó el logging
    )


def get_logger(name: str) -> logging.Logger:
    """Obtiene un logger con el nombre del módulo (ej. app.main)."""
    return logging.getLogger(name)