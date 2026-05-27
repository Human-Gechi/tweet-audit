import zipfile
from log import tweet_logger

logger = tweet_logger()

def _unzip(zip_path: str, extract_to: str = "tweet_data"):
    """
    Unzip X data archive .zip file
    """
    if not zipfile.is_zipfile(zip_path):
        raise ValueError(f"{zip_path} is not a valid zip file")

    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_to)
    logger.info("X Data Unzipped Successfully")

_unzip("../Downloads/twitter-2026-05-21-a092e8781c3bf51d56db9b3d45031a37a73590bce5ac048da2cd42483f3d2150.zip")