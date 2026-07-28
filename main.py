"""SAM.gov IT Contract Monitor — orchestrator.

Run flow:
  1. Load state (previously seen notice ids).
  2. First-ever run: bootstrap — record current listings as seen without
     scoring them (avoids a burst of Stage 2 calls / a giant first email).
  3. Otherwise: page SAM.gov for anything not yet seen, run Stage 1 (cheap
     Groq score) on each, run Stage 2 (full capture analysis) on anything
     scoring >= STAGE1_THRESHOLD, skip amendments to already-seen notices.
  4. If anything cleared Stage 2, compile a PDF and email it.
  5. Save state.
"""
import sys
import time
from datetime import datetime, timezone

from src import config, sam_gov, llm, state as state_mod, pdf_report, email_sender

BOOTSTRAP_PAGES = 3


def log(msg):
    print(f"[{datetime.now(timezone.utc).isoformat()}] {msg}", flush=True)


def _description_from_search_result(result):
    descriptions = result.get("descriptions", [])
    return descriptions[0].get("content", "") if descriptions else ""


def run():
    if not config.GROQ_API_KEY:
        log("FATAL: GROQ_API_KEY is not set.")
        sys.exit(1)

    st = state_mod.load()
    run_ts = datetime.now(timezone.utc).isoformat()

    if not st["bootstrapped"]:
        log("First run detected — bootstrapping seen-id list without scoring.")
        seen_before = set(st["seen"].keys())
        new_results = sam_gov.fetch_new_opportunities(seen_before, max_pages=BOOTSTRAP_PAGES)
        for r in new_results:
            state_mod.mark_seen(st, r["_id"], r.get("modifiedDate", run_ts))
        st["bootstrapped"] = True
        state_mod.save(st, run_ts)
        log(f"Bootstrap complete: {len(new_results)} existing notices recorded as seen. "
            f"Monitoring starts from the next run.")
        return

    seen_before = set(st["seen"].keys())
    new_results = sam_gov.fetch_new_opportunities(seen_before)
    log(f"Found {len(new_results)} notice(s) not previously seen.")

    scored_contracts = []
    skipped_amendments = 0
    failures = 0

    for r in new_results:
        notice_id = r["_id"]
        parent_id = r.get("parentNoticeId")
        modified_date = r.get("modifiedDate", run_ts)

        if parent_id and state_mod.is_seen(st, parent_id):
            state_mod.mark_seen(st, notice_id, modified_date)
            skipped_amendments += 1
            continue

        title = r.get("title", "Untitled")
        notice_type = r.get("type", {}).get("value", "Unknown")
        agency = sam_gov.agency_name(r)
        description = _description_from_search_result(r)
        if len(description) < 200:
            description = sam_gov.fetch_full_description(notice_id) or description

        try:
            score, reason = llm.score_opportunity(title, notice_type, agency, description)
        except Exception as e:
            log(f"Stage 1 scoring failed for {notice_id!r} ({title!r}): {e}")
            failures += 1
            continue

        state_mod.mark_seen(st, notice_id, modified_date)
        log(f"Stage 1: [{score:.1f}] {title!r} — {reason}")

        if score < config.STAGE1_THRESHOLD:
            continue

        if len(description) < 200:
            description = sam_gov.fetch_full_description(notice_id) or description

        link = sam_gov.notice_link(notice_id)
        try:
            stage2_report = llm.capture_analysis(
                title=title,
                notice_type=notice_type,
                solicitation_number=r.get("solicitationNumber"),
                agency=agency,
                publish_date=r.get("publishDate"),
                response_date=r.get("responseDate"),
                link=link,
                description=description,
            )
        except Exception as e:
            log(f"Stage 2 analysis failed for {notice_id!r} ({title!r}): {e}")
            failures += 1
            continue

        scored_contracts.append({
            "title": title,
            "agency": agency,
            "notice_type": notice_type,
            "link": link,
            "stage1_score": score,
            "stage1_reason": reason,
            "publish_date": r.get("publishDate"),
            "stage2_report": stage2_report,
        })
        time.sleep(1)  # light pacing against free-tier rate limits

    log(f"Skipped {skipped_amendments} amendment(s) to already-seen notices.")
    log(f"{len(scored_contracts)} contract(s) cleared Stage 2 and will be reported.")

    if scored_contracts:
        output_path = f"{config.OUTPUT_DIR}/sam_report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.pdf"
        pdf_report.build_pdf(scored_contracts, output_path)
        log(f"PDF built at {output_path}")
        email_sender.send_report(output_path, len(scored_contracts))
        log(f"Email sent to {', '.join(config.RECIPIENT_EMAILS)}")

    state_mod.save(st, run_ts)
    log("State saved.")

    if failures:
        log(f"FATAL: {failures} scoring/analysis call(s) failed this run — failing the job so it's visible.")
        sys.exit(1)


if __name__ == "__main__":
    run()
