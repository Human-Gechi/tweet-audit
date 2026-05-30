import zipfile
from pathlib import Path
from log import tweet_logger
from src.utils.config_validate import load_config

logger = tweet_logger()
config = load_config()


def unzip(zip_path: str, extract_to: str = "tweet_data"):
    """
    Unzip X data archive .zip file
    """
    if Path(extract_to).exists():
        logger.info("File exists skipping Unzipping")
    else:
        if not zipfile.is_zipfile(zip_path):
            raise ValueError(f"{zip_path} is not a valid zip file")

        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_to)
        logger.info("X Data Unzipped Successfully")
