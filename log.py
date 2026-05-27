import logging
import sys
from pathlib import Path

LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"

# Logger build func
def _build_logger(name: str, file_path: Path) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = True

    if not logger.handlers:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.touch(exist_ok=True)

        file_handler = logging.FileHandler(file_path, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(file_handler)

        terminal_handler = logging.StreamHandler(sys.stdout)
        terminal_handler.setLevel(logging.INFO)
        terminal_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        logger.addHandler(terminal_handler)

    return logger


def tweet_logger():
    parent_dir = Path.cwd()
    tweet_log_file_path = parent_dir / "tweet_audit.log"

    tweet_log_file_path.parent.mkdir(parents=True, exist_ok=True)
    tweet_log_file_path.touch(exist_ok=True)

    return _build_logger("logger", tweet_log_file_path)

tweet_logger()