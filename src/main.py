from src.archive_parser import unzip
from src.utils.helpers import load_config
from src.utils.config_validate import validate
from src.groq import parse_output
from log import tweet_logger

logger = tweet_logger()
config = load_config()

def run():
  """ Program main entry point"""
  logger.info("="*25)
  logger.info("Starting tweets auditing")
  logger.info("="*25)

  unzip_tweet = unzip(config["archive_settings"]["archive_path"])
  validate_config = validate()

  gemini_output = parse_output()

run()