# SAM.gov IT Contract Monitor

Runs on GitHub Actions (free, no server, no credit card). Every run:

1. Pages SAM.gov's public search endpoint for anything modified since the last run.
2. Runs a cheap Groq pass (Stage 1) on each new/modified notice, scoring fit 0-10
   against the business's service list.
3. Anything scoring >= `STAGE1_THRESHOLD` (default 7.5) goes through a full 17-section
   capture-analysis prompt (Stage 2).
4. If anything cleared Stage 2, compiles a PDF and emails it via Gmail SMTP.
5. Commits the updated seen-notice list back to the repo so nothing is reprocessed.

## One-time setup

1. Create a GitHub repo and push this folder to it.
2. **Groq API key**: sign up at [console.groq.com](https://console.groq.com) (no credit
   card required) and generate an API key. Free tier is 1,000 requests/day, far above
   what this workload needs per run.
3. **Gmail app password**: enable 2-Step Verification on the sending Gmail account, then
   create an [App Password](https://myaccount.google.com/apppasswords) for it. Use the
   16-character password generated there — not the account's normal login password.
4. In the GitHub repo, go to **Settings -> Secrets and variables -> Actions** and add:
   - `GROQ_API_KEY`
   - `GMAIL_ADDRESS` — the sending Gmail address
   - `GMAIL_APP_PASSWORD` — the app password from step 3
   - `RECIPIENT_EMAILS` — comma-separated list, e.g. `a@x.com,b@y.com`.
5. The workflow (`.github/workflows/sam-monitor.yml`) is already scheduled for
   13:00 / 16:00 / 19:00 / 22:00 UTC daily. Trigger a manual run anytime from the
   **Actions** tab -> SAM.gov IT Contract Monitor -> **Run workflow**, to test before
   waiting for the schedule.

## First run behavior

The very first run **bootstraps**: it records the ~75 most-recently-modified existing
notices as "seen" without scoring or emailing anything. This avoids Stage 1/2 burning
through the entire IT-related backlog and sending a huge first email. From the second
run onward, only genuinely new/modified notices are scored.

## Design notes / assumptions made during build

- **Amendments**: if a notice's `parentNoticeId` points to an already-seen notice, it's
  recorded as seen but silently skipped — no re-scoring, no re-notification.
- **Full descriptions**: SAM.gov's search results sometimes truncate the notice body.
  Confirmed a working, unauthenticated detail endpoint
  (`GET https://sam.gov/api/prod/opps/v2/opportunities/{id}`) that returns the full
  description; the script falls back to it whenever the search result's description is
  under 200 characters.
- **State growth**: `state/seen_ids.json` stores `{id: modifiedDate}` and prunes entries
  older than `SEEN_ID_MAX_AGE_DAYS` (default 400) on every save, so the file doesn't grow
  unbounded.
- **Partial-run safety**: state is only saved once, at the end of a run. If the run
  crashes partway through, some notices may get re-scored (extra Groq calls) on the
  next run, but nothing gets silently lost or double-emailed.
- **Groq model names** default to `llama-3.1-8b-instant` for Stage 1 (fast/cheap, this is
  the high-volume stage) and `llama-3.3-70b-versatile` for Stage 2 (the rare, low-volume
  deep-analysis stage, where quality matters more), overridable via `GROQ_MODEL_STAGE1` /
  `GROQ_MODEL_STAGE2` repo secrets or env vars. Switched from Gemini after its free tier
  repeatedly hit daily quota during a single backlog run; Groq's free tier (1,000
  req/day) has much more headroom for this workload. `llm.py` retries 429s with backoff
  (up to 3 retries, 20/40/60s) before giving up on a single notice.
- **A run fails loudly (non-zero exit) if any Stage 1/2 API call errors**, even though
  individual failures don't stop other notices from being processed. This is deliberate:
  a systemic issue (bad model name, expired key) would otherwise cause every notice to
  silently fail while the job still shows green. Check the Actions log if a run is red.

## Local testing

```bash
python -m venv .venv
.venv/Scripts/activate   # or source .venv/bin/activate on macOS/Linux
pip install -r requirements.txt
cp .env.example .env     # fill in real values
# load .env into the shell, then:
python main.py
```

## Increasing run frequency later

GitHub Actions' free minutes comfortably absorb more than 4-5 runs/day for a script
this lightweight (a few HTTP calls, no build step). To increase frequency, just add
more `cron:` lines to `.github/workflows/sam-monitor.yml`.
