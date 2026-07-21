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
  - Manual exclude: W2793912163 (chromatogram-libraries preprint, same as published article).
  - Result: 37 works — 25 articles, 8 datasets, 4 preprints. 2,492 lifetime citations.
- Titles may contain <i>...</i> HTML tags from OpenAlex — render as italics, not literal text.
- OpenAlex breaks citations out by year only from ~2012 on; older citations count in
  lifetime totals but not in the per-year chart.
