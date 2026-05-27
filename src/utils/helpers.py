from enum import StrEnum
import json
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
    with open("tweets_data/data/tweets.js", "r", encoding="utf-8") as data:
        content = data.read()

    json_string = content[content.find('['):content.rfind(']') + 1]

    try:
        tweets = json.loads(json_string)
        return tweets
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse cleaned JSON string: {e}")
        return []


def _get_tweet_status(tweet_data: dict) -> TweetStatus:
    full_text = tweet_data.get("full_text", "")
    retweeted = tweet_data.get("retweeted", False)
    in_reply_to = tweet_data.get("in_reply_to_user_id_str", "")

    if retweeted or full_text.startswith("RT @"):
        return TweetStatus.RETWEET
    if in_reply_to:
        return TweetStatus.REPLY
    return TweetStatus.POST


def _build_url(id_str: str) -> str:
    username = config["account_context"]["username"]
    return f"https://x.com/{username}/status/{id_str}"


def _is_too_short(tweets: str):
    min_length = config["filter_settings"]["min_length"]
    for tweet in tweets:
        tweet_data = tweet.get("tweet", {})
        full_text = tweet_data.get("full_text", "")
        if len(full_text) < min_length:
                return True
        return False

def _parse_created_at(tweets: str):
    date_format = "%a %b %d %H:%M:%S %z %Y"
    for tweet in tweets:
        tweets_data = tweet.get("tweet", {})
        created_at = tweets_data.get("created_at", "")
        py_date = datetime.strptime(created_at, date_format)
        return py_date

def process_tweets() -> list[dict]:
    tweets_list = _load_json()
    processed = []

    for item in tweets_list:
        if not _is_too_short(tweets_list):
            tweet_data = item.get("tweet", {})
            id_str = tweet_data.get("id_str")
            full_text = tweet_data.get("full_text", "")

            if not id_str or not full_text:
                logger.warning(f"Skipping tweet with missing id_str or full_text")
                continue

            status = _get_tweet_status(tweet_data)
            url = _build_url(id_str)
            created_at = _parse_created_at(tweets_list)

            processed.append({
                "id_str": id_str,
                "full_text": full_text,
                "status": status,
                "url": url,
                "created_at": created_at
            })

    logger.info(f"Processed {len(processed)} tweets")
    return processed

#if __name__ == "__main__":
    #tweets = process_tweets()
    #for tweet in tweets[:5]:
    #    print(f"{tweet['status']} — {tweet['created_at']} — {tweet["lang"]}")
    #    print(f"  {tweet['full_text'][:80]}")