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
- [ ] Design the page (interview) and record design decisions here
- [ ] Build index.html
- [ ] Refine the look
- [ ] Publish live with GitHub Pages
- [ ] Mark complete

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
