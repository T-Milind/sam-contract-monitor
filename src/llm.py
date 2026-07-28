"""Thin wrapper around the Groq REST API (OpenAI-compatible chat completions)."""
import json
import re
import time
import requests

from . import config

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF_SECONDS = 20


def _generate(model, prompt, json_mode=False):
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    for attempt in range(RATE_LIMIT_RETRIES + 1):
        resp = requests.post(
            GROQ_URL,
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json=body,
            timeout=120,
        )
        if resp.status_code == 429 and attempt < RATE_LIMIT_RETRIES:
            time.sleep(RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1))
            continue
        resp.raise_for_status()
        break

    data = resp.json()
    choices = data.get("choices", [])
    if not choices:
        raise RuntimeError(f"Groq returned no choices: {data}")
    return choices[0].get("message", {}).get("content", "")


def score_opportunity(title, notice_type, agency, description):
    prompt = config.STAGE1_PROMPT.format(
        criteria=config.SERVICE_CRITERIA,
        title=title,
        notice_type=notice_type,
        agency=agency,
        description=(description or "(no description provided)")[:4000],
    )
    raw = _generate(config.GROQ_MODEL_STAGE1, prompt, json_mode=True)
    return _parse_score(raw)


def _parse_score(raw):
    try:
        parsed = json.loads(raw)
        return float(parsed["score"]), str(parsed.get("reason", ""))
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        pass
    match = re.search(r'"score"\s*:\s*([\d.]+).*?"reason"\s*:\s*"([^"]*)"', raw, re.DOTALL)
    if match:
        return float(match.group(1)), match.group(2)
    raise RuntimeError(f"Could not parse Stage 1 score from Groq response: {raw!r}")


def capture_analysis(title, notice_type, solicitation_number, agency, publish_date, response_date, link, description):
    prompt = config.STAGE2_PROMPT.format(
        title=title,
        notice_type=notice_type,
        solicitation_number=solicitation_number or "N/A",
        agency=agency,
        publish_date=publish_date or "N/A",
        response_date=response_date or "N/A",
        link=link,
        description=description or "(no description provided in notice)",
    )
    return _generate(config.GROQ_MODEL_STAGE2, prompt)
