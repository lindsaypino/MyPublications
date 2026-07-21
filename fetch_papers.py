"""Fetch a researcher's works from OpenAlex by ORCID.

Saves:
  - papers.json  : full list with the fields the page needs
                   (title, year, venue, type, doi/link, cited_by_count,
                    counts_by_year, authors)
  - papers.csv   : a spreadsheet to skim (title, year, venue, type, co-authors)

Reusable: change ORCID below (or pass as the first CLI arg) and re-run.
Run on Windows with:  py -X utf8 fetch_papers.py
"""
import csv
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from difflib import SequenceMatcher

# Polite pool: OpenAlex asks for a contact email; it gets you faster, more
# reliable service. Not secret, just a courtesy header.
MAILTO = "lindsay.pino@gmail.com"
ORCID = sys.argv[1] if len(sys.argv) > 1 else "0000-0003-1857-7222"

# --- Curation choices (Lindsay, 2026-07-21), applied on every re-run ---
# Work types to drop entirely.
DROP_TYPES = {"conference-abstract", "peer-review"}
# Keep preprints, BUT drop any preprint that is a duplicate of a published
# article (same paper). Matched by normalized title exact match or high
# similarity, plus a manual list for near-matches below the threshold.
DEDUPE_PREPRINTS = True
FUZZY_THRESHOLD = 0.90
# Specific works confirmed by hand as duplicates the fuzzy match won't catch.
# W2793912163 = "Comprehensive peptide quantification..." preprint, same paper
# as the published "Chromatogram libraries improve peptide detection..." article.
EXCLUDE_IDS = {"https://openalex.org/W2793912163"}


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def fetch_all_works(orcid):
    """Yield every work for an ORCID, paging through OpenAlex with a cursor."""
    base = "https://api.openalex.org/works"
    cursor = "*"
    while cursor:
        params = {
            "filter": f"author.orcid:{orcid}",
            "per-page": "200",
            "cursor": cursor,
            "mailto": MAILTO,
        }
        url = base + "?" + urllib.parse.urlencode(params)
        data = get_with_retry(url)
        for work in data.get("results", []):
            yield work
        cursor = data.get("meta", {}).get("next_cursor")


def get_with_retry(url, max_tries=6):
    """GET JSON, backing off and retrying if OpenAlex asks us to slow down."""
    delay = 2
    for attempt in range(1, max_tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": f"mailto:{MAILTO}"})
            with urllib.request.urlopen(req) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < max_tries:
                print(f"  OpenAlex is busy (429); waiting {delay}s and retrying...")
                time.sleep(delay)
                delay *= 2
                continue
            raise
    raise RuntimeError("Exhausted retries fetching " + url)


def simplify(work):
    """Pull just the fields the page needs out of a raw OpenAlex work."""
    src = (work.get("primary_location") or {}).get("source") or {}
    authors = [
        (a.get("author") or {}).get("display_name")
        for a in work.get("authorships", [])
    ]
    return {
        "id": work.get("id"),
        "title": work.get("title") or work.get("display_name"),
        "year": work.get("publication_year"),
        "venue": src.get("display_name"),
        "type": work.get("type"),
        "doi": work.get("doi"),
        "link": work.get("doi") or work.get("id"),
        "cited_by_count": work.get("cited_by_count", 0),
        "counts_by_year": work.get("counts_by_year", []),
        "authors": authors,
    }


def curate(papers):
    """Apply Lindsay's curation choices: drop types, dedupe preprints, exclude IDs."""
    kept = []
    dropped = {"type": 0, "excluded": 0, "dup_preprint": 0}
    article_titles = {norm_title(p["title"]) for p in papers if p["type"] == "article"}

    def is_dup_preprint(p):
        if not (DEDUPE_PREPRINTS and p["type"] == "preprint"):
            return False
        nt = norm_title(p["title"])
        if nt in article_titles:
            return True
        return any(
            SequenceMatcher(None, nt, at).ratio() >= FUZZY_THRESHOLD
            for at in article_titles
        )

    for p in papers:
        if p["id"] in EXCLUDE_IDS:
            dropped["excluded"] += 1
        elif p["type"] in DROP_TYPES:
            dropped["type"] += 1
        elif is_dup_preprint(p):
            dropped["dup_preprint"] += 1
        else:
            kept.append(p)
    return kept, dropped


def main():
    print(f"Fetching works for ORCID {ORCID} from OpenAlex...")
    papers = [simplify(w) for w in fetch_all_works(ORCID)]
    papers, dropped = curate(papers)
    print(f"Curation dropped: {dropped['type']} by type "
          f"({', '.join(sorted(DROP_TYPES))}), "
          f"{dropped['dup_preprint']} duplicate preprints, "
          f"{dropped['excluded']} manually excluded.")

    papers.sort(key=lambda p: (p["year"] or 0), reverse=True)

    with open("papers.json", "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    with open("papers.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "year", "venue", "type", "cited_by_count", "co-authors"])
        for p in papers:
            w.writerow([
                p["title"], p["year"], p["venue"], p["type"],
                p["cited_by_count"], "; ".join(a for a in p["authors"] if a),
            ])

    # Summary
    total_citations = sum(p["cited_by_count"] for p in papers)
    by_type = {}
    for p in papers:
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1

    print(f"\nSaved {len(papers)} works to papers.json and papers.csv")
    print(f"Total citations (lifetime): {total_citations}")
    print("Breakdown by type:")
    for t, n in sorted(by_type.items(), key=lambda kv: -kv[1]):
        print(f"  {t:15} {n}")


if __name__ == "__main__":
    main()
