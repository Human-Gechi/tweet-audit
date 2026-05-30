# Tradeoffs

## Model/provider tradeoffs
- **Groq Usage** Groq was used here as opposed to gemini as stated in the project readme use to outrageous rate limiting
- **Model quality variance:** Different models may flag content differently, reducing consistency across runs/providers.

## Reliability vs speed
- **Retry + backoff + jitter:** Improves resilience under rate limits/transient failures but increases end-to-end runtime.
- **Sequential processing simplicity:** Easier debugging, but slower than parallel worker-based pipelines.

## Accuracy tradeoffs
- **False positives vs false negatives:** Stricter criteria catch more risky tweets but may over-flag benign content.
- **Prompt-based moderation dependence:** Prompt wording strongly affects outcomes; small prompt changes can shift results.

## Data handling tradeoffs
- **Archive parsing assumptions:** X archive format changes can break parsers and require maintenance updates.
- **CSV output simplicity:** Easy to inspect/share, but loses richer metadata compared to JSON/DB storage.