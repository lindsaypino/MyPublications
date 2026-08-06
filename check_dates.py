"""Audit every publication date in papers.json against Crossref and PubMed.

The page orders papers reverse-chronologically by full date and displays month +
year, so a wrong month matters, not just a wrong year. OpenAlex's
publication_date is derived from Crossref and inherits publisher metadata errors,
so this compares three sources per work:

  - papers.json  what the page shows (OpenAlex, plus DATE_OVERRIDES)
  - Crossref     published-online (preferred) and published-print
  - PubMed       the ArticleDate e-pub, and the issue date

Policy being checked: the date is when the paper FIRST APPEARED. For anything
published online ahead of an issue, that is the online date, not the issue date.

Writes nothing. Exit status 1 if there are unexplained mismatches, so it can be
wired into CI later.

Usage:  py -X utf8 check_dates.py
"""
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

UA = "MyPublications date-audit (lindsay.pino@gmail.com)"
EMAIL = "lindsay.pino@gmail.com"

# Divergences that are real but settled, so they stop being reported as errors.
# Keep the reason -- that is the whole point of the list.
SETTLED = {
    "10.1002/mas.21540":
        "The Skyline ecosystem. Online 2017-07-09, but the print issue (Mass "
        "Spectrom Rev 39(3)) only appeared May 2020, so PubMed's issue date says "
        "2020. We use 2017-07 -- when it appeared and began being cited, and the "
        "year the CV uses.",
    "10.1093/bioadv/vbaf301":
        "Perspectives in computational MS. Crossref carries a bad published-print "
        "of 2024-12-26 from OUP; the real date is 2025-12-17 (vol 5(1), PubMed "
        "41425651). Corrected in fetch_papers.py DATE_OVERRIDES, but Crossref's "
        "issued/print fields still disagree with it.",
    "10.1038/s41467-018-07454-w":
        "Chromatogram libraries. OpenAlex reports Crossref's 'created' timestamp "
        "(2018-11-27, DOI registration) instead of publication. Corrected to "
        "2018-12-03 in DATE_OVERRIDES, matching Crossref published-online and "
        "PubMed's e-pub.",
    "10.1016/j.euprot.2019.07.009":
        "Team COUNCIL OF RICKS / EuPA. Elsevier back-dated the issue to 2019-03; "
        "PubMed 31890550 gives an 'Electronic' ArticleDate of 2019-10-16 and the "
        "DOI was registered the same day. Corrected to 2019-10-16 in "
        "DATE_OVERRIDES, so Crossref's print/issued fields still disagree.",
}

PMIDS = ["42146532", "41959400", "41425651", "40505655", "40667134", "39356573",
         "39574686", "38605454", "37417926", "36916610", "36599300", "33947439",
         "33764077", "33079175", "32648542", "32312845", "28691345", "32037841",
         "32101728", "31890550", "30510204", "30350613", "29438992"]


def norm(d):
    if not d:
        return ""
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", d.strip().lower().rstrip("."))


def get(url, tries=4):
    delay = 2
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code in (400, 404):
                return None
            if i == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2
        except Exception:
            if i == tries - 1:
                raise
            time.sleep(delay)
            delay *= 2
    return None


def date_parts(msg, key):
    v = (msg.get(key) or {}).get("date-parts", [[None]])[0]
    if not v or v[0] is None:
        return ""
    return "-".join(str(x).zfill(2) if i else str(x)
                    for i, x in enumerate(v) if x is not None)


def crossref(doi):
    raw = get("https://api.crossref.org/works/" + urllib.parse.quote(doi, safe=""))
    if not raw:
        return None
    m = json.loads(raw)["message"]
    return {
        "online": date_parts(m, "published-online"),
        "print": date_parts(m, "published-print"),
        "issued": date_parts(m, "issued"),
        "created": (m.get("created") or {}).get("date-time", "")[:10],
        "volume": m.get("volume") or "",
    }


def load_pubmed():
    root = ET.fromstring(get(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed"
        "&retmode=xml&id=" + ",".join(PMIDS)
        + f"&tool=mypublications&email={EMAIL}"))
    out = {}
    for art in root.iter("PubmedArticle"):
        doi = ""
        idl = art.find("./PubmedData/ArticleIdList")
        for aid in (idl if idl is not None else []):
            if aid.get("IdType") == "doi":
                doi = norm(aid.text)
        ad = art.find(".//Article/ArticleDate")
        epub = ""
        if ad is not None:
            epub = f"{ad.findtext('Year')}-{ad.findtext('Month')}-{ad.findtext('Day')}"
        pd = art.find(".//JournalIssue/PubDate")
        issue_year = pd.findtext("Year") or (pd.findtext("MedlineDate") or "")[:4]
        if doi:
            out[doi] = {"epub": epub, "issue_year": issue_year}
    return out


def main():
    papers = json.load(open("papers.json", encoding="utf-8"))
    pubmed = load_pubmed()
    print(f"Auditing {len(papers)} works -- comparing month precision\n")

    problems, imprecise = [], []
    for p in sorted(papers, key=lambda p: (p.get("date") or ""), reverse=True):
        doi = norm(p.get("doi"))
        ours = (p.get("date") or "")[:7]
        cr = crossref(doi) if doi else None
        pm = pubmed.get(doi)

        # The authority for "first appeared": Crossref online, else PubMed's
        # e-pub, else the print/issue date as a last resort.
        best, src = "", ""
        if cr and cr["online"]:
            best, src = cr["online"][:7], "crossref-online"
        elif pm and pm["epub"]:
            best, src = pm["epub"][:7], "pubmed-epub"
        elif cr and (cr["print"] or cr["issued"]):
            best, src = (cr["print"] or cr["issued"])[:7], "crossref-print"

        settled = doi in SETTLED
        agree = (not best) or best == ours
        if not agree and not settled:
            problems.append((p, ours, best, src, cr, pm))
        flag = "" if agree else ("  (settled)" if settled else "  *** MONTH MISMATCH ***")

        # A day of 01 usually means the publisher deposited only year+month.
        if p.get("date", "").endswith("-01") and cr and not cr["online"]:
            imprecise.append(p)

        print(f"  {ours}  ours | {best or '?':7} {src:15}{flag}")
        print(f"           {(p.get('title') or '')[:78]}")

    print("\n" + "=" * 74)
    print(f"{len(problems)} UNEXPLAINED MONTH MISMATCHES")
    print("=" * 74)
    if not problems:
        print("  none -- every month matches the first-appearance date, or is settled.")
    for p, ours, best, src, cr, pm in problems:
        print(f"\n  {p['title'][:78]}")
        print(f"    doi       {norm(p['doi'])}")
        print(f"    ours      {ours}   <-- what the page shows and sorts by")
        print(f"    authority {best}  (from {src})")
        if cr:
            bits = [f"{k}={cr[k]}" for k in ("online", "print", "issued") if cr[k]]
            print(f"    crossref  {'  '.join(bits)}  created={cr['created']}")
        if pm:
            print(f"    pubmed    epub={pm['epub'] or '-'}  issue_year={pm['issue_year']}")
        print(f"    fix       add to DATE_OVERRIDES in fetch_papers.py once verified")

    if imprecise:
        print("\n" + "=" * 74)
        print(f"MONTH-ONLY PRECISION ({len(imprecise)} works)")
        print("=" * 74)
        print("  The publisher deposited only year+month, so OpenAlex fills the day")
        print("  with 01. The month is sound and that is all the page displays, but")
        print("  ordering *within* these months is not meaningful -- it falls back")
        print("  to a title tiebreak.")
        for p in imprecise:
            print(f"    {p['date']}  {p['title'][:66]}")

    print("\n" + "=" * 74)
    print("SETTLED DIVERGENCES (real, decided, no action needed)")
    print("=" * 74)
    for doi, why in SETTLED.items():
        print(f"\n  {doi}\n    {why}")

    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
