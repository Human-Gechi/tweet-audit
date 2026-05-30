from enum import StrEnum
import json
import csv
import os
from log import tweet_logger
from src.utils.config_validate import load_config
from datetime import datetime

logger = tweet_logger()
config = load_config()


class TweetStatus(StrEnum):
    RETWEET = "RETWEET"
    POST = "POST"
    REPLY = "REPLY"


def _load_json():
    "Load json object containing tweets data"
    with open("tweet_data/data/tweets.js", "r", encoding="utf-8") as data:
        content = data.read()

    json_string = content[content.find("[") : content.rfind("]") + 1]

    try:
        tweets = json.loads(json_string)
        return tweets
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse cleaned JSON string: {e}")
        return []


def _get_tweet_status(tweet_data: dict) -> TweetStatus:
    "Get tweet status using StrEnum"
    full_text = tweet_data.get("full_text", "")
    retweeted = tweet_data.get("retweeted", False)
    in_reply_to = tweet_data.get("in_reply_to_user_id_str", "")

    if retweeted or full_text.startswith("RT @"):
        return TweetStatus.RETWEET
    if in_reply_to:
        return TweetStatus.REPLY
    return TweetStatus.POST


def _build_url(id_str: str) -> str:
    "Function to build URLS in a tweet status"
    username = config["account_context"]["username"]
    return f"https://x.com/{username}/status/{id_str}"


def _is_too_short(tweets: str):
    "Checks if a tweet is too short"
    min_length = config["filter_settings"]["min_length"]
    for tweet in tweets:
        tweet_data = tweet.get("tweet", {})
        full_text = tweet_data.get("full_text", "")
        if len(full_text) < min_length:
            return True
        return False


def _parse_created_at(tweets: str):
    "Convert date/time to python datetime"
    date_format = "%a %b %d %H:%M:%S %z %Y"
    for tweet in tweets:
        tweets_data = tweet.get("tweet", {})
        created_at = tweets_data.get("created_at", "")
        py_date = datetime.strptime(created_at, date_format)
        return py_date


def process_tweets() -> list[dict]:
    """Funtion to return needed key:vale pairs to process dicts"""
    tweets_list = _load_json()
    processed = []

    for item in tweets_list:
        if not _is_too_short(tweets_list):
            tweet_data = item.get("tweet", {})
            id_str = tweet_data.get("id_str")
            full_text = tweet_data.get("full_text", "")

            if not id_str or not full_text:
                logger.warning("Skipping tweet with missing id_str or full_text")
                continue

            status = _get_tweet_status(tweet_data)
            url = _build_url(id_str)
            created_at = _parse_created_at(tweets_list)

            processed.append(
                {
                    "url": url,
                    "full_text": full_text,
                    "status": status,
                    "created_at": created_at,
                }
            )

    logger.info(f"Processed {len(processed)} tweets")
    return processed


def output_csv(flagged_tweets: list[dict]) -> None:
    """CSV file output parser"""
    output_settings = config["output_settings"]
    output_dir = output_settings["output_dir"]
    filename = output_settings["filename"]

    base_fields = ["url", "status", "created_at", "deleted"]
    extra_fields = []

    for item in flagged_tweets:
        for key in item.keys():
            if (
                key not in {"url", "full_text", "status", "created_at"}
                and key not in extra_fields
            ):
                extra_fields.append(key)

    fieldnames = base_fields + extra_fields

    rows = []
    for tweet in flagged_tweets:
        row = {
            "url": tweet.get("url", ""),
            "status": tweet.get("status", ""),
            "created_at": tweet.get("created_at", ""),
            "deleted": "false",
        }

        for key in extra_fields:
            value = tweet.get(key, "")
            if isinstance(value, list):
                value = "|".join(value)
            row[key] = value

        rows.append(row)

    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info(f"CSV written to {output_path} with {len(rows)} flagged tweets")
