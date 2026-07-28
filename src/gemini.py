"""Thin wrapper around the Gemini REST API (generateContent)."""
import json
import re
import time
import requests

from . import config

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_BACKOFF_SECONDS = 20


def _generate(model, prompt, response_mime_type=None):
    url = GEMINI_URL.format(model=model)
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    if response_mime_type:
        body["generationConfig"] = {"responseMimeType": response_mime_type}

    for attempt in range(RATE_LIMIT_RETRIES + 1):
        resp = requests.post(
            url,
            params={"key": config.GEMINI_API_KEY},
            json=body,
            timeout=120,
        )
        if resp.status_code == 429 and attempt < RATE_LIMIT_RETRIES:
            time.sleep(RATE_LIMIT_BACKOFF_SECONDS * (attempt + 1))
            continue
        resp.raise_for_status()
        break

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        raise RuntimeError(f"Gemini returned no candidates: {data}")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts)


def score_opportunity(title, notice_type, agency, description):
    prompt = config.STAGE1_PROMPT.format(
        criteria=config.SERVICE_CRITERIA,
        title=title,
        notice_type=notice_type,
        agency=agency,
        description=(description or "(no description provided)")[:4000],
    )
    raw = _generate(config.GEMINI_MODEL_STAGE1, prompt, response_mime_type="application/json")
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
    raise RuntimeError(f"Could not parse Stage 1 score from Gemini response: {raw!r}")


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
    return _generate(config.GEMINI_MODEL_STAGE2, prompt)
