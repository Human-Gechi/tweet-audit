from src.utils.config_validate import load_config

config = load_config()


def build_prompt(full_text: str) -> str:
    "Function to build Groq prompt with system configurations and prompt detailing how the llm API should behave"
    criteria = config["alignment_criteria"]
    account = config["account_context"]
    prompt_settings = config["prompt_settings"]

    forbidden_words = ", ".join(criteria["forbidden_words"])
    forbidden_phrases = ", ".join(f'"{p}"' for p in criteria["forbidden_phrases"])
    disallowed_topics = ", ".join(criteria["disallowed_topics"])

    require_reasoning = prompt_settings["require_reasoning"]
    reasoning_detail = prompt_settings["reasoning_detail"]
    flag_threshold = prompt_settings["flag_threshold"]

    reasoning_instruction = ""
    if require_reasoning:
        if reasoning_detail == "concise":
            reasoning_instruction = (
                "one sentence explaining why it was flagged, or null if not flagged"
            )
        else:
            reasoning_instruction = (
                "a detailed explanation of why it was flagged, or null if not flagged"
            )

    prompt = f"""
ACCOUNT CONTEXT:
This account belongs to {account["account_purpose"]}.
The account tone is {account["account_tone"]}.
Casual, honest, and emotional tweets are acceptable and expected.
Judge tweets against this context — not against a generic professional standard.

RULES:
1. FLAG the tweet if it contains any of these forbidden words (case insensitive):
   {forbidden_words}

2. FLAG the tweet if it contains any of these forbidden phrases (case insensitive):
   {forbidden_phrases}

3. FLAG the tweet if it touches any of these disallowed topics:
   {disallowed_topics}

4. FLAG the tweet only if it takes explicit sides on party politics, elections, 
   or political figures. Do NOT flag tweets about tech policy, data privacy, 
   or industry regulation.

5. FLAG the tweet if the tone is disrespectful, aggressive, mocking, 
   inflammatory, or unprofessional in a way that does not fit the account context.

6. DO NOT FLAG the tweet for:
   - Being emotional or vulnerable (student highs and lows are expected)
   - Casual language that is not offensive
   - Humour that is not at anyone's expense
   - Opinions about technology, tools, or the industry
   - Celebrating achievements or expressing frustration about learning

7. CONFIDENCE RULE:
   Only flag the tweet if your confidence is {flag_threshold} or above.
   If you are unsure, return flagged as false.

8. If the tweet text is empty, less than 3 words, or contains only a URL,
   return flagged as false with confidence 0.0.

TWEET TO REVIEW:
"{full_text}"

RESPOND WITH ONLY THIS JSON AND NOTHING ELSE:
{{
  "flagged": false,
  "confidence": 0.85,
  "reason": {reasoning_instruction},
  "violated_criteria": []
}}
"""
    return prompt.strip()


def get_system_instruction() -> str:
    return config["prompt_settings"]["system_instruction"]
