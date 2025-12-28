import logging
import sys

def setup_logging(level: int = logging.INFO) -> None:
    """
    Configures the project-wide logging.
    """
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Silence noisy libraries
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy").setLevel(logging.WARNING)
    logging.getLogger("uvicorn").setLevel(logging.INFO)

def get_logger(name: str) -> logging.Logger:
    """
    Returns a configured logger instance.
    """
    return logging.getLogger(name)
