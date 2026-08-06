"""Fetch a researcher's works from OpenAlex by ORCID.

Saves:
  - papers.json  : full list with the fields the page needs
                   (title, date, year, venue, type, doi/link, cited_by_count,
                    counts_by_year, authors), ordered newest first by full date
  - papers.csv   : a spreadsheet to skim (title, date, year, venue, type,
                   co-authors)

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
DROP_TYPES = {"conference-abstract", "peer-review", "dataset"}
# Keep preprints, BUT drop any preprint that is a duplicate of a published
# article (same paper). Matched by normalized title exact match or high
# similarity, plus a manual list for near-matches below the threshold.
DEDUPE_PREPRINTS = True
FUZZY_THRESHOLD = 0.90
# Specific works confirmed by hand as duplicates the fuzzy match won't catch.
# W2793912163 = "Comprehensive peptide quantification..." preprint, same paper
# as the published "Chromatogram libraries improve peptide detection..." article.
# W2807897000 = "Quantification of nuclear protein dynamics reveals chromatin
# remodeling during acute protein degradation" (bioRxiv 10.1101/345686), same
# paper as the published "Highly Parallel Quantification and Compartment
# Localization of Transcription Factors and Nuclear Proteins" (Cell Reports,
# 10.1016/j.celrep.2020.01.096). The title was rewritten between versions, so
# similarity is only 0.33 -- far below FUZZY_THRESHOLD.
EXCLUDE_IDS = {
    "https://openalex.org/W2793912163",
    "https://openalex.org/W2807897000",
}

# --- Publication dates OpenAlex gets wrong ---
# We order the list by full date, so a wrong month matters, not just a wrong
# year. OpenAlex's publication_date is derived from Crossref and inherits
# publisher metadata errors. Each override is an ISO date verified against
# Crossref published-online AND PubMed's e-pub date; check_dates.py re-runs the
# whole comparison. Policy: the date is when the paper FIRST APPEARED (online
# ahead of print), which is what readers and citations track.
DATE_OVERRIDES = {
    "10.1093/bioadv/vbaf301": ("2025-12-17",
        "Bioinformatics Advances vol 5(1). Crossref carries a bad "
        "published-print of 2024-12-26 from OUP, which is what OpenAlex picked "
        "up, but published-online is 2025-12-17. PubMed 41425651 says vol 5, "
        "issue 1, 2025, e-pub 2025-12-17, and volume 5 is the 2025 volume "
        "(the journal started at vol 1 in 2021). Published December 2025."),
    "10.1016/j.euprot.2019.07.009": ("2019-10-16",
        "Team COUNCIL OF RICKS / EuPA Open Proteomics. The reverse of the usual "
        "online-ahead-of-print case: Elsevier assigned it to a BACK-DATED issue "
        "(published-print 2019-03), but it did not actually appear until later. "
        "PubMed 31890550 records an ArticleDate of 2019-10-16 explicitly typed "
        "'Electronic', Crossref registered the DOI the same day (created "
        "2019-10-16), and the DOI suffix itself is j.euprot.2019.07.009. First "
        "appearance is October 2019, so the March issue label would sort it "
        "seven months too early."),
    "10.1038/s41467-018-07454-w": ("2018-12-03",
        "Chromatogram libraries. OpenAlex says 2018-11-27, which is Crossref's "
        "'created' timestamp (when the DOI was registered), not publication. "
        "Crossref published-online and PubMed's e-pub both say 2018-12-03. Only "
        "a week out, but it crosses a month boundary so it changes the ordering "
        "and the displayed month."),
}

# Online-first vs print-issue dates where BOTH are real and OpenAlex is fine.
# Noted so a future audit doesn't re-report them as errors:
#   10.1002/mas.21540  The Skyline ecosystem. Online 2017-07-09; the print issue
#     (Mass Spectrom Rev 39(3)) did not appear until May 2020, so PubMed's issue
#     date says 2020. We use 2017-07-09 -- when it appeared and began being
#     cited, and the year the CV uses.
#   Several others (Neuropeptides, Acquiring/Analyzing DIA, Nonlinear
#     Regression) are online in one month and in an issue months later.
#     OpenAlex already gives the earlier online date, so nothing to fix.
#
# Precision note: where a publisher only deposited a year+month, OpenAlex
# synthesizes day 01 (e.g. 2016-05-01). The month is trustworthy, the day is a
# placeholder -- which is why the page displays month + year and not the day.

# --- Works the ORCID query cannot see, added back by DOI ---
# OpenAlex sometimes splits one person across several author records. Where the
# duplicate record has no ORCID on it, filtering by author.orcid (and even by
# the canonical author.id) silently misses the work. Listing the DOI here pulls
# it in explicitly; it then goes through the same curation as everything else.
# Re-check these on a re-run: if OpenAlex merges the author records, the work
# will arrive through the normal query and the entry here becomes a harmless
# no-op (fetch_all_works results are deduped by work id).
INCLUDE_DOIS = {
    "10.64898/2026.05.04.722036":
        "CpG island density predicts CBP/p300 dependency across 3D chromatin "
        "clusters (bioRxiv, 2026). Lindsay is credited on a second, ORCID-less "
        "OpenAlex author record (A5135562179, which OpenAlex also mis-affiliates "
        "to 'TRIA Bioscience'), so neither author.orcid nor author.id:A5020587347 "
        "returns it. Confirmed hers via PubMed 42146532, which lists her "
        "affiliation as 'Talus Bioscience, Inc., Seattle, WA' alongside "
        "co-authors Alexander J Federation and Julia Robbins.",
}


def norm_title(t):
    return re.sub(r"[^a-z0-9]+", " ", (t or "").lower()).strip()


def norm_doi(d):
    """Bare lowercase DOI, so DATE_OVERRIDES keys match OpenAlex's URL form."""
    if not d:
        return ""
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d.strip().lower().rstrip("."))


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


def fetch_by_doi(doi):
    """Fetch a single work by DOI, for the INCLUDE_DOIS escape hatch."""
    url = f"https://api.openalex.org/works/doi:{doi}?mailto={MAILTO}"
    return get_with_retry(url)


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
    doi = work.get("doi")
    date = work.get("publication_date") or ""
    year = work.get("publication_year")
    override = DATE_OVERRIDES.get(norm_doi(doi))
    if override:
        date = override[0]
    # Keep year consistent with the date we actually use, so a corrected date
    # can never leave a stale year behind it.
    if date[:4].isdigit():
        year = int(date[:4])

    return {
        "id": work.get("id"),
        "title": work.get("title") or work.get("display_name"),
        "date": date,
        "year": year,
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
    raw = list(fetch_all_works(ORCID))
    seen = {w.get("id") for w in raw}

    for doi in sorted(INCLUDE_DOIS):
        work = fetch_by_doi(doi)
        if work.get("id") in seen:
            print(f"  {doi}: now in the ORCID results; INCLUDE_DOIS entry is "
                  f"redundant and can be dropped.")
            continue
        print(f"  {doi}: added by hand (not visible to the ORCID query).")
        raw.append(work)

    raw_dates = {norm_doi(w.get("doi")): w.get("publication_date") for w in raw}
    for doi, (date, _) in sorted(DATE_OVERRIDES.items()):
        was = raw_dates.get(doi)
        if was is None:
            print(f"  date override for {doi} matched nothing -- stale entry?")
        elif was == date:
            print(f"  {doi}: OpenAlex now says {date} too; override is redundant.")
        else:
            print(f"  {doi}: date {was} -> {date} (OpenAlex is wrong).")

    papers = [simplify(w) for w in raw]
    papers, dropped = curate(papers)
    print(f"Curation dropped: {dropped['type']} by type "
          f"({', '.join(sorted(DROP_TYPES))}), "
          f"{dropped['dup_preprint']} duplicate preprints, "
          f"{dropped['excluded']} manually excluded.")

    # Reverse chronological to the day. Works with a month-only date sort as if
    # they were on the 1st, which is how OpenAlex represents them anyway; the
    # title tiebreak just keeps the order stable between runs.
    papers.sort(key=lambda p: (p["date"] or f"{p['year'] or 0}-00-00",
                               norm_title(p["title"])), reverse=True)

    undated = [p for p in papers if not p["date"]]
    if undated:
        print(f"\n{len(undated)} works have no date and fell back to year-only "
              f"ordering:")
        for p in undated:
            print(f"  {p['year']}  {p['title'][:70]}")

    with open("papers.json", "w", encoding="utf-8") as f:
        json.dump(papers, f, ensure_ascii=False, indent=2)

    with open("papers.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["title", "date", "year", "venue", "type", "cited_by_count",
                    "co-authors"])
        for p in papers:
            w.writerow([
                p["title"], p["date"], p["year"], p["venue"], p["type"],
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
