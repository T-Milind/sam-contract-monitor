"""SAM.gov public search + notice-detail client. No API key required."""
import io
import time
import requests
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from . import config

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SAMContractMonitor/1.0)"}
RETRY_ATTEMPTS = 3
RETRY_BACKOFF_SECONDS = 5


def _get_json_with_retry(url, **kwargs):
    """SAM.gov's backend occasionally returns 503s/hangs, or a non-JSON block/
    maintenance page with a 200 (this is an unauthenticated, unofficial
    endpoint) — retry a few times with backoff before giving up."""
    last_error = None
    for attempt in range(RETRY_ATTEMPTS):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30, **kwargs)
            resp.raise_for_status()
            return resp.json()
        except (requests.RequestException, ValueError) as e:
            last_error = e
            if attempt < RETRY_ATTEMPTS - 1:
                time.sleep(RETRY_BACKOFF_SECONDS * (attempt + 1))
    raise last_error


def fetch_new_opportunities(seen_ids, max_pages=config.MAX_PAGES_PER_RUN):
    """Page through search results (newest-modified first) until a page contains
    no unseen ids, or the safety cap is hit. Returns list of raw result dicts,
    newest first."""
    new_results = []
    for page in range(max_pages):
        data = _search_page(page)
        results = data.get("_embedded", {}).get("results", [])
        if not results:
            break

        page_had_new = False
        for r in results:
            if r.get("_id") not in seen_ids:
                new_results.append(r)
                page_had_new = True

        total_pages = data.get("page", {}).get("totalPages", page + 1)
        if not page_had_new or page + 1 >= total_pages:
            break
    return new_results


def _search_page(page):
    params = {
        "random": str(int(time.time() * 1000)),
        "index": "ac",
        "page": page,
        "sort": "-modifiedDate",
        "size": config.PAGE_SIZE,
        "mode": "search",
        "responseType": "json",
        "domain": "ac",
        "q": config.SAM_QUERY,
        "qMode": "ALL",
    }
    return _get_json_with_retry(config.SAM_SEARCH_URL, params=params)


def fetch_full_description(notice_id):
    """Search results sometimes truncate the description; the detail endpoint
    returns the full body. Falls back to empty string on any failure."""
    try:
        url = config.SAM_DETAIL_URL.format(id=notice_id)
        data = _get_json_with_retry(url)
        descriptions = data.get("description", [])
        return "\n\n".join(d.get("body", "") for d in descriptions if d.get("body"))
    except (requests.RequestException, ValueError):
        return ""


def fetch_pdf_attachment_texts(notice_id):
    """Downloads and extracts text from this notice's PDF attachments — these
    are often the actual SOW/PWS, much more detailed than the search
    description. Best-effort: any failure (network, non-PDF-parseable file,
    scanned/image-only PDF) just skips that attachment rather than raising,
    since this is Stage 2 enrichment, not core data the run depends on."""
    try:
        data = _get_json_with_retry(
            config.SAM_RESOURCES_URL.format(id=notice_id),
            params={"excludeDeleted": "false", "withScanResult": "false"},
        )
    except (requests.RequestException, ValueError):
        return []

    attachment_lists = data.get("_embedded", {}).get("opportunityAttachmentList", [])
    attachments = attachment_lists[0].get("attachments", []) if attachment_lists else []
    pdf_attachments = [a for a in attachments if a.get("mimeType") == ".pdf"]
    pdf_attachments = pdf_attachments[: config.MAX_ATTACHMENTS_PER_NOTICE]

    texts = []
    total_chars = 0
    for a in pdf_attachments:
        if total_chars >= config.MAX_ATTACHMENT_CHARS_TOTAL:
            break
        name = a.get("name", "attachment.pdf")
        text = _download_and_extract_pdf(a.get("resourceId"))
        if not text:
            continue
        text = text[: config.MAX_ATTACHMENT_CHARS_PER_FILE]
        remaining = config.MAX_ATTACHMENT_CHARS_TOTAL - total_chars
        text = text[:remaining]
        total_chars += len(text)
        texts.append((name, text))
    return texts


def _download_and_extract_pdf(resource_id):
    if not resource_id:
        return ""
    try:
        url = config.SAM_ATTACHMENT_DOWNLOAD_URL.format(resource_id=resource_id)
        resp = requests.get(url, headers=HEADERS, params={"api_key": "null", "token": ""}, timeout=60)
        resp.raise_for_status()
        reader = PdfReader(io.BytesIO(resp.content))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except (requests.RequestException, PdfReadError, ValueError):
        return ""


def agency_name(result):
    hierarchy = result.get("organizationHierarchy", [])
    return hierarchy[-1].get("name", "Unknown Agency") if hierarchy else "Unknown Agency"


def notice_link(notice_id):
    return config.SAM_NOTICE_VIEW_URL.format(id=notice_id)
