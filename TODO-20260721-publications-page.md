# TODO: publications page

**Goal:** an interactive web page of my published papers, with charts of how my
citations have grown over the years, published live so I can share it.

This spec is the running plan and map for the work. Keep it current as we go,
noting what we learn at each step, so the whole thing can be re-run later.

## Plan / status
- [x] Set up MyPublications repo (public, on GitHub)
- [x] Find and confirm my ORCID — 0000-0003-1857-7222 (confirmed)
- [x] Fetch papers from OpenAlex; save papers.json + papers.csv to skim
- [x] Check the list is really mine; curate (see decisions below)
- [x] Design the page (interview) — decisions below
- [x] Build index.html (via build_page.py — regenerates from papers.json)
- [x] Refine the look — dropped datasets (0 citations, no effect on stats);
      kept articles + preprints. Name stays "Lindsay Pino", no intro line.
- [x] Publish live with GitHub Pages — https://lindsaypino.github.io/MyPublications/
- [x] Mark complete ✅ (2026-07-21)
- [x] Combine with Talus team coauthor network (from my-practice-project) —
      added a "Talus collaboration network" section below the personal page,
      my node highlighted. Published publicly (approved). (2026-07-21)
- [x] Recover missing papers; cross-check the record against PubMed and the CV
      repo (lindsaypino/cv). Found 2, now on the page. (2026-08-06) — see
      "Recovering missing papers" below.
- [x] Audit every publication year against Crossref + PubMed (check_dates.py).
      Fixed 1 real error, documented 1 online-first/print split. (2026-08-06)
- [x] Add month-level dates; order the list reverse-chronologically to the day.
      3 dates corrected, audit clean. (2026-08-06)

## Recovering missing papers (2026-08-06)
Two works were missing. Record went 28 -> 30 works, 2,492 -> 2,510 citations.

1. **Structure-free, site-resolved contrastive learning extends small-molecule
   discovery beyond the reach...** (bioRxiv, 10.64898/2026.07.28.741295).
   Only cause was a stale papers.json — the preprint was posted 2026-07-28, a
   week after the last fetch. A plain re-run picks it up. No code change needed.
2. **CpG island density predicts CBP/p300 dependency across 3D chromatin
   clusters** (bioRxiv, 10.64898/2026.05.04.722036). This one the pipeline
   *could not* see, and it is the interesting failure:
   - OpenAlex split my identity. My canonical author record is A5020587347
     (ORCID attached, 58 works). On this paper I am credited on a *second*
     record, A5135562179, with **no ORCID** and a garbled affiliation
     ("TRIA Bioscience" — a mangling of Talus Bioscience).
   - So both `author.orcid:...` **and** `author.id:A5020587347` miss it. Widening
     the filter from ORCID to author-id does not help; I checked, both return the
     same 58 works.
   - Confirmed it is genuinely mine, not a same-name collision: PubMed 42146532
     lists my affiliation as "Talus Bioscience, Inc., Seattle, WA" with Alex
     Federation and Julia Robbins as co-authors.
   - Fix: `INCLUDE_DOIS` in fetch_papers.py — an escape hatch that fetches a work
     by DOI and merges it in before curation, with the reason recorded inline.
     If OpenAlex ever merges the two author records the work arrives through the
     normal query and the script says the entry is now redundant.

## Auditing publication years (2026-08-06)
Prompted by spotting that the computational mass spec perspective was showing
2024 when it was published Dec 2025. Checked all 30 years against Crossref (the
DOI registrar) and PubMed via `check_dates.py`. Two disagreements, different in
kind — one a real error, one only apparent:

1. **Perspectives in computational mass spectrometry** (10.1093/bioadv/vbaf301)
   — **was wrong, now fixed to 2025.** OUP registered a `published-print` of
   2024-12-26 that contradicts its own `published-online` of 2025-12-17. OpenAlex
   derives `publication_year` from Crossref and took the bad field, giving 2024.
   It is Bioinformatics Advances **vol 5(1)**, and volume 5 is the 2025 volume
   (journal started at vol 1 in 2021); PubMed 41425651 says 2025, e-pub
   2025-12-17. Corrected via `DATE_OVERRIDES` in fetch_papers.py.
2. **The Skyline ecosystem** (10.1002/mas.21540) — **left at 2017, deliberately.**
   Genuinely online-first 2017-07-09, but the print issue (Mass Spectrom Rev
   39(3)) didn't appear until May 2020, so PubMed reports 2020. Both dates are
   real. 2017 is when it appeared and began being cited, and it's the year the CV
   uses, so the page keeps 2017.

Everything else agreed across all three sources. Note Crossref does cover
bioRxiv's newer `10.64898/...` DOI prefix, so preprints are checkable too.
This audit is what prompted moving to month-level dates (next section), which
turned up two further date errors that a year-only check could never have seen.

**Lesson:** OpenAlex years are only as good as publisher Crossref deposits, and
a `published-print` date *later* than `published-online` (or vice versa across a
year boundary) is the tell. Prefer `published-online` — it's when the paper
actually appeared, and it's what the page claims. Re-run `check_dates.py` after
any fetch; it reports unexplained mismatches and keeps a `SETTLED` list of the
real-but-decided divergences so they don't get re-litigated.

## Month-level dates and reverse-chronological order (2026-08-06)
The list was sorted by year only, so order within a year was arbitrary. Now it
carries a full ISO `date` per work and sorts newest-first to the day.

- **Source:** OpenAlex `publication_date`. Compared it against Crossref and
  PubMed for all 30 works before trusting it — it agrees on month for 27 of 30.
- **Display:** month + year ("Dec 2025"). Deliberately *not* the day: where a
  publisher deposited only year+month, OpenAlex fills the day with `01`, so
  showing it would invent precision the source doesn't have.
- **Policy:** the date is when the paper **first appeared**. For anything online
  ahead of its issue that's the online date. This is the rule the audit enforces,
  and it's why the Skyline paper stays at Jul 2017 rather than its May 2020 issue.
- **Sort:** `(date, normalized title)` descending, in both fetch_papers.py and
  build_page.py, so a hand-edited papers.json still renders in the right order.
  The title tiebreak only exists to keep runs stable.

Three dates needed correcting (all now in `DATE_OVERRIDES`):
1. `10.1093/bioadv/vbaf301` → 2025-12-17 (the year error, above).
2. `10.1038/s41467-018-07454-w` Chromatogram libraries → 2018-12-03. OpenAlex
   reported Crossref's `created` timestamp (2018-11-27, DOI registration) as the
   publication date. Only a week out, but it crosses a month boundary.
3. `10.1016/j.euprot.2019.07.009` EuPA / COUNCIL OF RICKS → 2019-10-16. The
   *reverse* of online-ahead-of-print: Elsevier back-dated the issue to March
   2019, but PubMed 31890550 gives an ArticleDate explicitly typed "Electronic"
   of 2019-10-16 and the DOI was registered the same day. The issue label would
   have sorted it seven months too early.

**Known limit.** Five works have month-only precision (Crossref deposited no day
and no online date): Profiling mouse brown/white adipocytes, Optimization of a
processing workflow, Highly Parallel Quantification, COUNCIL OF RICKS, and
Reduced-representation Phosphosignatures. Their *months* are sound, which is all
the page shows, but ordering *within* those months is not meaningful — it falls
back to the title tiebreak. `check_dates.py` lists them under "MONTH-ONLY
PRECISION" so this stays visible rather than looking like real precision.

**Method worth repeating.** The ORCID/author-id query is not a complete record;
it is only as good as OpenAlex's disambiguation. Cross-check against PubMed,
which indexes by author-name string and so catches the split-identity cases:

    https://pubmed.ncbi.nlm.nih.gov/?term=Pino+LK%5BAuthor%5D

`cv/audit_pubs.py` in the CV repo diffs the CV against this papers.json and had
already flagged the CpG paper in its docstring as a known blind spot. That audit
now reports both new preprints as "in the record, not in the CV" — a CV decision
(which section, author-list wording), so left alone here.

## Talus network integration
- Source: my-practice-project/data/coauthor_network.json (team-wide coauthor
  graph, built from PubMed + Semantic Scholar). Copied into this repo as
  coauthor_network.json so the public page is self-contained.
- build_page.py now inlines the network and renders a force-directed canvas
  (plain JS, no libs, ported from that repo's dashboard). Theme-aware colors;
  my node ("Lindsay K Pino") highlighted in purple, labeled "(me)".
- 794 nodes (12 team + 782 coauthors), 975 edges.
- Visibility: MyPublications is PUBLIC, so the whole team's network is now
  public. Approved by Lindsay (she's Talus co-founder; data is from public
  bibliographic sources). my-practice-project stays private and untouched.
- To refresh the network: re-run my-practice-project/scripts/update_all.py,
  copy its coauthor_network.json here, and re-run build_page.py.
- Refreshed 2026-08-06: 833 nodes (12 team + 821 coauthors), 1028 edges, up from
  794/975. Picks up coauthors from the two recovered preprints.
- That refresh needed three fixes in my-practice-project first (all committed
  there separately, not in this repo):
  1. `lib/pubmed.py` swallowed efetch failures and returned None, which the
     caller treated as "no affiliations". One transient NCBI hiccup silently
     relabelled all 153 papers `unverified` and wrote it out as data (the
     committed dataset had 25 confirmed / 33 unverified / 86 not_talus; the bad
     run produced 0 / 153 / 0). Now retries with backoff and raises instead.
  2. Every `open()` in all four scripts lacked an explicit encoding, so on
     Windows they defaulted to cp1252 and `build_dataset.py` died writing a
     `β` in a title -- leaving talus_team_publications.csv truncated from 34 KB
     to 1.3 KB. All 14 opens now specify UTF-8.
  3. `update_all.py` spawned each step with `subprocess.run([sys.executable, ...])`,
     and `-X utf8` is a flag, not inherited -- so running it exactly as
     documented still left every child in cp1252. Now passes `PYTHONUTF8=1`.
  Good news: build_coauthor_network.py never reads `talus_affiliated` (it only
  drops >40-author consortium papers), so the published network was never at
  risk from bug 1 -- that field feeds the dashboard only. Verified before
  copying anything across.
- Note the two networks use different name formats: this repo's papers.json
  comes from OpenAlex/PubMed ("Khan MIH") while the network comes from Semantic
  Scholar ("M. I. H. Khan"). Don't cross-check them by exact string match.

## Design (approved plan for index.html)
- **Look:** Talus-branded — navy `#0C015B` + teal `#36C8C8`/`#1FA6A6`, Rethink Sans
  (Google Fonts), clean and modern. Teal is the accent.
- **Header:** name (LK Pino / Lindsay Pino), one-line role (CTO & co-founder,
  Talus Bio), link to ORCID. Dark-mode toggle in the corner.
- **Stat cards (hero row):** Total citations = 2,492 (hero) · h-index = 13 ·
  Years active = 2016–2026 (11 yrs).
- **Chart:** citations per year (bar or area), 2016–2026. Built from the summed
  counts_by_year across all works. Note 2026 is partial; label it. Pre-2012 not
  in per-year data (n/a here — career starts 2016).
- **Publication list:** grouped by type — Articles (25), Preprints (4),
  Datasets (8) — each section newest-first. Each entry: title (linked to DOI/
  source), venue, year, citation count. Render `<i>` tags in titles as italics.
- **Footer:** data source (OpenAlex), generated date, ORCID.
- **Build:** single self-contained index.html. Read papers.json at runtime
  (fetch) or inline the data so the page works when opened directly and on
  GitHub Pages. Charts via inline SVG or a lightweight approach — no heavy deps.

## Notes as we learn
- Me: Lindsay (LK Pino), CTO/co-founder of Talus Bio.
- Run Python with `-X utf8` (special characters in titles/names crash otherwise on Windows).
- ORCID: 0000-0003-1857-7222 (confirmed — Talus Bio, UW, UPenn, Broad, Penn State on record)
- Fetch: use OpenAlex works API filtered by author.orcid, cursor-paginated, polite pool (mailto), retry on 429.
- Curation choices (baked into fetch_papers.py, reproducible on re-run):
  - Drop types: conference-abstract, peer-review (the eLife "Author response" record).
  - Keep preprints, but dedupe against published articles (exact + fuzzy >= 0.90 title match).
  - Manual exclude: W2793912163 (chromatogram-libraries preprint, same as published article),
    W2807897000 (the Cell Reports preprint, retitled so fuzzy dedupe misses it).
  - Manual include: INCLUDE_DOIS, for works OpenAlex hides behind a split author
    record (see "Recovering missing papers" above).
  - Date fixes: DATE_OVERRIDES, for dates OpenAlex inherits wrong from a bad
    publisher Crossref deposit (see the two date sections above).
  - Result (2026-08-06): 30 works — 25 articles, 5 preprints. 2,510 lifetime
    citations, h-index 13. Datasets dropped by type, so the count is the page's.
- Titles may contain <i>...</i> HTML tags from OpenAlex — render as italics, not literal text.
- OpenAlex breaks citations out by year only from ~2012 on; older citations count in
  lifetime totals but not in the per-year chart.
