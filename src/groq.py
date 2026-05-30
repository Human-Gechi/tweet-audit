from groq import Groq
import json
import time
import random

from src.prompt import build_prompt, get_system_instruction
from src.utils.config_validate import load_config, VALID_GROQ_MODELS
from src.utils.helpers import process_tweets, output_csv
from log import tweet_logger

logger = tweet_logger()

config = load_config()
groq_settings = config["groq_settings"]

client = Groq(api_key=config["groq_api_key"])


def extract_json(text: str) -> dict:
    """Extract JSON from Groq response text"""
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON object found in response")
    return json.loads(text[start:end])


def _generate_with_retries(prompt: str, system_instruction: str) -> dict:
    """Generate responses with exponential backoff and model fallback"""
    max_attempts = groq_settings.get("retry_attempts", 3)
    base_delay = groq_settings.get("retry_delay_seconds", 1)
    max_delay = groq_settings.get("max_retry_delay", 30)
    backoff_factor = groq_settings.get("backoff_factor", 2)

    primary_model = groq_settings.get("model", VALID_GROQ_MODELS[0])
    fallback_models = [primary_model] + [
        m for m in VALID_GROQ_MODELS if m != primary_model
    ]

    last_exc = None

    for attempt in range(1, max_attempts + 1):
        model = fallback_models[min(attempt - 1, len(fallback_models) - 1)]

        try:
            logger.info(f"Attempt {attempt}/{max_attempts} using model: {model}")

            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": prompt},
                ],
                temperature=groq_settings.get("temperature", 0.7),
                max_tokens=groq_settings.get("max_tokens", 1024),
                response_format={"type": "json_object"},
            )

            return resp

        except Exception as e:
            last_exc = e
            error_msg = str(e)

            if any(code in error_msg for code in ["401", "403", "invalid"]):
                logger.error(f"Non-retryable error: {error_msg}")
                raise

            logger.warning(
                f"Retryable error on attempt {attempt}/{max_attempts}: {error_msg}"
            )

        if attempt < max_attempts:
            delay = min(base_delay * (backoff_factor ** (attempt - 1)), max_delay)
            jitter = random.uniform(0, delay * 0.25)
            sleep_for = delay + jitter
            logger.info(f"Waiting {sleep_for:.2f}s before retry...")
            time.sleep(sleep_for)

    if last_exc:
        logger.error(f"All {max_attempts} attempts exhausted. Last error: {last_exc}")
        raise last_exc

    raise RuntimeError("All attempts exhausted without explicit exception")


def analyse_tweet(full_text: str) -> dict:
    """Function to analyse tweet using groq"""
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
            "violated_criteria": [],
        }

    try:
        result = extract_json(resp.choices[0].message.content)
        return result
    except (json.JSONDecodeError, ValueError, AttributeError, IndexError) as e:
        logger.error(f"Failed to parse response: {e}")
        response_text = (
            getattr(resp.choices[0].message, "content", None) if resp else None
        )
        logger.error(f"Response text: {response_text}")
        return {
            "flagged": False,
            "confidence": 0.0,
            "reason": "Error occurred during JSON parsing",
            "violated_criteria": [],
        }


def parse_output():
    """Save flagged tweets to CSV file"""
    tweets = process_tweets()
    batch_size = config["output_settings"]["batch_size"]
    flagged = []

    for batch_start in range(0, len(tweets), batch_size):
        batch_end = min(batch_start + batch_size, len(tweets))
        batch = tweets[batch_start:batch_end]

        logger.info(
            f"Processing batch {batch_start // batch_size + 1} (tweets {batch_start + 1}-{batch_end}/{len(tweets)})"
        )

        for idx, tweet in enumerate(batch, start=batch_start + 1):
            result = analyse_tweet(tweet["full_text"])

            if not result:
                continue

            if result.get("flagged") is True:
                flagged.append(
                    {
                        **tweet,
                        "reason": result.get("reason", ""),
                        "confidence": result.get("confidence", 0.0),
                        "violated_criteria": result.get("violated_criteria", []),
                    }
                )

        if flagged:
            logger.info(f"Found {len(flagged)} flagged tweets so far. Saving...")
            output_csv(flagged)

    if flagged:
        logger.info(f"Completed. Total {len(flagged)} flagged tweets saved.")
    else:
        logger.info("No flagged tweets found.")

    return flagged
