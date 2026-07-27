"""SAM.gov public search + notice-detail client. No API key required."""
import time
import requests

from . import config

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; SAMContractMonitor/1.0)"}


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
    resp = requests.get(config.SAM_SEARCH_URL, params=params, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_full_description(notice_id):
    """Search results sometimes truncate the description; the detail endpoint
    returns the full body. Falls back to empty string on any failure."""
    try:
        url = config.SAM_DETAIL_URL.format(id=notice_id)
        resp = requests.get(url, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        descriptions = data.get("description", [])
        return "\n\n".join(d.get("body", "") for d in descriptions if d.get("body"))
    except requests.RequestException:
        return ""


def agency_name(result):
    hierarchy = result.get("organizationHierarchy", [])
    return hierarchy[-1]["name"] if hierarchy else "Unknown Agency"


def notice_link(notice_id):
    return config.SAM_NOTICE_VIEW_URL.format(id=notice_id)
