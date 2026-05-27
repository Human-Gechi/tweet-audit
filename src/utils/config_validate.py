import json
import os
import re
from pathlib import Path

from log import tweet_logger

config_path = Path("config.json")

VALID_GEMINI_MODELS = {
    "gemini-ultra",
    "gemini-1.5-pro",
    "gemini-1.5-flash"
}

logger = tweet_logger()

def _clean_string_list(items: list, field: str) -> list[str]:
    """
    Strip whitespace, lower-case, drop empty strings and duplicates.
    """
    seen: set[str] = set()
    cleaned: list[str] = []
    for raw in items:
        if not isinstance(raw, str):
            logger.warning("config: %s — non-string entry %r removed", field, raw)
            continue
        val = raw.strip().lower()
        if not val:
            logger.warning("config: %s — empty string entry removed", field)
            continue
        if val in seen:
            logger.warning("config: %s — duplicate %r removed", field, val)
            continue
        seen.add(val)
        cleaned.append(val)
    return cleaned


def _require_env_fallback(config: dict) -> dict:
    """
    Get value for key: gemini_api_key. If Blank, try GEMINI_API_KEY env var.
    Raises if neither source provides a real key.
    """
    key = config.get("gemini_api_key", "").strip()

    if not key:
        env_key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not env_key:
            raise ValueError(
                "gemini_api_key is missing. "
                "Set it in config.json or export/set GEMINI_API_KEY=<your-gemini-key> in terminal"
            )
        logger.info("config: using GEMINI_API_KEY from environment variable")
        config["gemini_api_key"] = env_key

    return config

def _validate_criteria(c: dict) -> dict:
    errors: list[str] = []

    c["forbidden_words"] = _clean_string_list(
        c.get("forbidden_words", []), "forbidden_words"
    )
    c["forbidden_phrases"] = _clean_string_list(
        c.get("forbidden_phrases", []), "forbidden_phrases"
    )
    c["disallowed_topics"] = _clean_string_list(
        c.get("disallowed_topics", []), "disallowed_topics"
    )

    if not isinstance(c.get("professional_check"), bool):
        errors.append("alignment_criteria.professional_check must be true or false")

    if not isinstance(c.get("exclude_politics"), bool):
        errors.append("alignment_criteria.exclude_politics must be true or false")

    if not isinstance(c.get("exclude_personal_info"), bool):
        errors.append("alignment_criteria.exclude_personal_info must be true or false")

    threshold = c.get("min_engagement_threshold", 0)
    if not isinstance(threshold, int) or threshold < 0:
        errors.append("alignment_criteria.min_engagement_threshold must be a non-negative integer")

    max_age = c.get("max_age_days")
    if max_age is not None:
        if not isinstance(max_age, int) or max_age <= 0:
            errors.append("alignment_criteria.max_age_days must be a positive integer or null")

    allowed = c.get("allowed_tones", [])
    if not isinstance(allowed, list) or not allowed:
        errors.append("alignment_criteria.allowed_tones must be a non-empty list")
    return c, errors


def _validate_gemini(g: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []

    if g.get("model") not in VALID_GEMINI_MODELS:
        errors.append(
            f"gemini_settings.model must be one of {sorted(VALID_GEMINI_MODELS)}, "
            f"got: {g.get('model')!r}"
        )

    temp = g.get("temperature", 0.3)
    if not isinstance(temp, (int, float)) or not (0.0 <= temp <= 1.0):
        errors.append("gemini_settings.temperature must be a float between 0.0 and 1.0")

    for int_field, minimum in [
        ("max_tokens", 1),
        ("retry_attempts", 0),
        ("retry_delay_seconds", 0),
        ("timeout_seconds", 1),
    ]:
        val = g.get(int_field)
        if not isinstance(val, int) or val < minimum:
            errors.append(
                f"gemini_settings.{int_field} must be an integer >= {minimum}, got {val!r}"
            )

    return g, errors


def _validate_output(o: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []

    filename = o.get("filename", "")
    if not filename.endswith(".csv"):
        errors.append(f"output_settings.filename must end with .csv, got {filename!r}")

    if not re.match(r'^[\w\-. ]+$', filename):
        errors.append(
            f"output_settings.filename contains invalid characters: {filename!r}"
        )

    batch = o.get("batch_size", 10)
    if not isinstance(batch, int) or not (1 <= batch <= 100):
        errors.append("output_settings.batch_size must be an integer between 1 and 100")

    if not isinstance(o.get("include_reasons"), bool):
        errors.append("output_settings.include_reasons must be true or false")

    return o, errors

def _validate_archive(a: dict) -> tuple[dict, list[str]]:
    errors: list[str] = []

    tweets_path = a.get("tweets_json_path", "")
    if not tweets_path.endswith(".js"):
        errors.append(
            f"archive_settings.tweets_json_path must point to a .js file, got {tweets_path!r}"
        )
    return a, errors

def load_config() -> dict:

    global config_path
    if not config_path.exists():
        raise FileNotFoundError(
            f"Config file not found: {config_path.resolve()}\n"
            "Copy config.example.json → config.json and fill in your values."
        )

    with config_path.open("r", encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(f"config.json is not valid JSON: {exc}") from exc
        return raw

def main() -> None:
    config = load_config()
    config = _require_env_fallback(config)

    all_errors: list[str] = []

    config["alignment_criteria"], errs = _validate_criteria(config["alignment_criteria"])
    all_errors.extend(errs)

    config["gemini_settings"], errs = _validate_gemini(config["gemini_settings"])
    all_errors.extend(errs)

    config["output_settings"], errs = _validate_output(config["output_settings"])
    all_errors.extend(errs)

    config["archive_settings"], errs = _validate_archive(config["archive_settings"])
    all_errors.extend(errs)

    if all_errors:
        bullet_list = "\n  • ".join(all_errors)
        raise ValueError(f"config.json has {len(all_errors)} error(s):\n  • {bullet_list}")

    logger.info("config: loaded successfully from %s", config_path.resolve())
    return config

main()
