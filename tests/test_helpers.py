from unittest.mock import MagicMock, patch
from src.utils.helpers import _load_json
import pytest
from src.utils.helpers import TweetStatus, _parse_created_at, process_tweets
from src.utils.helpers import _get_tweet_status, _build_url, _is_too_short
from datetime import datetime

fake_config = {"account_context": {"username": "test_username"}}
fake_min_length = {"filter_settings": {"min_length": 5}}


@pytest.fixture
def mock_data():
    return [
        {
            "tweet": {
                "id_str": "2057189562657468614",
                "full_text": "This is a sample reply tweet with some content",
                "created_at": "Wed May 20 19:59:47 +0000 2026",
                "in_reply_to_user_id_str": "1234567890",
                "retweeted": False,
            }
        },
        {
            "tweet": {
                "id_str": "2057189562657468615",
                "full_text": "RT @someuser Another tweet that contains important information",
                "created_at": "Thu May 21 10:30:00 +0000 2026",
                "retweeted": True,
            }
        },
        {
            "tweet": {
                "id_str": "2057189562657468616",
                "full_text": "A third sample tweet for testing purposes indicating actual posts",
                "created_at": "Fri May 22 15:45:30 +0000 2026",
                "retweeted": False,
            }
        },
    ]


@patch("src.utils.helpers.json.loads")
@patch("src.utils.helpers.open")
def test_json(mock_open, mock_loads, mock_data):
    mock_context_manager = MagicMock()
    mock_context_manager.__enter__.return_value = MagicMock(
        read=MagicMock(return_value='[{"tweet": {"id_str": "123"}}]')
    )
    mock_context_manager.__exit__.return_value = None

    mock_open.return_value = mock_context_manager

    mock_loads.return_value = mock_data

    result = _load_json()
    assert result == mock_data


def test_get_tweet_status_reply(mock_data):
    single_tweet = mock_data[0]["tweet"]
    single_tweet["in_reply_to_user_id_str"] is True
    result = _get_tweet_status(single_tweet)

    assert result == TweetStatus.REPLY


def test_get_tweet_status_retweeted(mock_data):
    single_tweet = mock_data[1]["tweet"]
    if single_tweet["retweeted"] is True and "RT @" in single_tweet:
        result = _get_tweet_status(single_tweet)

        assert result == TweetStatus.RETWEET


def test_get_tweet_status_post(mock_data):
    single_tweet = mock_data[2]["tweet"]

    if (
        single_tweet["retweeted"] is False
        and "in_reply_to_user_id_str" not in single_tweet
    ):
        result = _get_tweet_status(single_tweet)

        assert result == TweetStatus.POST


@patch("src.utils.helpers.config", fake_config)
def test_build_url(mock_data):
    tweet = mock_data[0]["tweet"]
    id_str = tweet["id_str"]

    output = f"https://x.com/{'test_username'}/status/{id_str}"

    result = _build_url(id_str=id_str)
    assert result == output


@patch("src.utils.helpers.config", fake_min_length)
def test_min_length(mock_data):
    result = _is_too_short(tweets=mock_data)
    assert not result


def runtime_parser(date_string, format_string):
    return datetime.strptime(date_string, format_string)


def test_created_at(mock_data):
    result = _parse_created_at(tweets=mock_data)

    assert isinstance(result, datetime)

    expected = mock_data[0]["tweet"]["created_at"]
    assert result.strftime("%a %b %d %H:%M:%S %z %Y") == expected


@patch("src.utils.helpers._parse_created_at")
@patch("src.utils.helpers._build_url")
@patch("src.utils.helpers._get_tweet_status")
@patch("src.utils.helpers._is_too_short")
@patch("src.utils.helpers._load_json")
def test_process_tweets(
    mock_load_json,
    mock_is_too_short,
    mock_get_status,
    mock_build_url,
    mock_parse_date,
    mock_data,
):

    mock_load_json.return_value = mock_data
    mock_is_too_short.return_value = False
    mock_get_status.return_value = TweetStatus.REPLY
    mock_build_url.return_value = (
        "https://x.com/test_username/status/2057189562657468614"
    )
    mock_parse_date.return_value = "Wed May 20 19:59:47 +0000 2026"

    result = process_tweets()

    processed = result[0]

    assert len(processed) == 4
    assert "url" in processed
    assert "status" in processed
    assert "created_at" in processed
    assert "full_text" in processed
    assert processed["url"] == "https://x.com/test_username/status/2057189562657468614"
    assert processed["created_at"] == "Wed May 20 19:59:47 +0000 2026"
    assert processed["status"] == TweetStatus.REPLY
