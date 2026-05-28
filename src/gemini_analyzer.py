from google import genai
from google.genai import types
import json
import time
import random
from google.api_core import exceptions as gexc
from typing import List

from src.custom_criteria import build_prompt, get_system_instruction
from src.utils.config_validate import VALID_GEMINI_MODELS, load_config
from src.utils.helpers import process_tweets, output_csv
from log import tweet_logger

logger = tweet_logger()

config = load_config()
gemini_settings = config["gemini_settings"]

client = genai.Client(api_key=config["gemini_api_key"])

def extract_json(text: str) -> dict:
    "Extract the text in the response json retrieved from GEMINI"
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")
    return json.loads(text[start:end])

def _generate_with_retries(prompt: str, system_instruction: str) -> object:
    """Generate Responses with exponenetial backoff and jitter, swiching in between models too"""
    max_attempts = gemini_settings.get("retry_attempts", 3)
    base_delay = gemini_settings.get("retry_delay_seconds", gemini_settings.get("retry_deay_seconds", 1))
    max_delay = gemini_settings.get("max_retry_delay", 30)
    backoff_factor = gemini_settings.get("backoff_factor", 2)
    fallback_models: List[str] = list(VALID_GEMINI_MODELS) + [gemini_settings.get("model")]

    last_exc = None
    for attempt in range(1, max_attempts + 1):
        model = fallback_models[min(attempt - 1, len(fallback_models) - 1)]
        try:
            resp = client.models.generate_content(
                model=model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=gemini_settings.get("temperature"),
                    max_output_tokens=gemini_settings.get("max_tokens"),
                    response_mime_type="application/json",
                )
            )
            return resp
        except gexc.GoogleAPICallError as e:
            last_exc = e
            code = getattr(e, "code", None)
            if code and int(code) in (400, 401, 403, 404):
                logger.error(f"Non-retryable API error: {e.message}")
                raise
            logger.warning(f"API call error (retryable) attempt {attempt}/{max_attempts}: {e.message}")

        except Exception as e:
            last_exc = e
            logger.warning(f"Unexpected error on attempt {attempt}/{max_attempts}: {e.message}")

        delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
        jitter = random.uniform(0, delay * 0.25)
        sleep_for = delay + jitter
        time.sleep(sleep_for)

    if last_exc:
        logger.error(f"All attempts exhausted, last error: {last_exc}")
        raise last_exc
    raise RuntimeError("All attempts exhausted without explicit exception")

def analyse_tweet(full_text: str) -> dict:
    "Analyze tweet from tweet_data fiel with prompts and system settings"
    system_instruction = get_system_instruction()
    prompt = build_prompt(full_text)

    try:
        resp = _generate_with_retries(prompt, system_instruction)
    except Exception as e:
        logger.error(f"Request failed after retries: {e}")
        return {
            "flagged": False,
            "confidence": 0.0,
            "reason": "request failed",
            "violated_criteria": []
        }

    try:
        result = extract_json(resp.text)
        return result
    except (json.JSONDecodeError, ValueError) as e:
        logger.error(f"Failed to parse response: {e}")
        logger.error(f"Response text: {getattr(resp,'text',None)}")
        return {
            "flagged": False,
            "confidence": 0.0,
            "reason": "Error occured during json parsing",
            "violated_criteria": []
        }

def parse_output():
    """ Save Output from Gemini in csv file"""
    tweets = process_tweets()
    flagged = []

    for tweet in tweets:
        result = analyse_tweet(tweet["full_text"])

        if not result:
            continue

        if result.get("flagged") is True:
            flagged.append({
                **tweet,
                "reason": result.get("reason", ""),
                "confidence": result.get("confidence", 0.0),
                "violated_criteria": result.get("violated_criteria", []),
            })

    if flagged:
        output_csv(flagged)

    return flagged

