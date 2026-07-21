"""Build index.html from papers.json.

Reads the curated papers.json, computes the stats, and writes a single
self-contained, Talus-branded page with the data inlined (so it works both
when opened locally and on GitHub Pages). Re-run after fetch_papers.py to
regenerate the page.

Run on Windows with:  py -X utf8 build_page.py
"""
import datetime
import html
import json

NAME = "Lindsay Pino"
ROLE = "CTO & co-founder, Talus Bio"
ORCID = "0000-0003-1857-7222"

TYPE_ORDER = [("article", "Articles"), ("preprint", "Preprints"), ("dataset", "Datasets")]


def esc(text):
    """Escape a title for HTML but keep <i>...</i> italics from OpenAlex."""
    e = html.escape(text or "")
    return e.replace("&lt;i&gt;", "<i>").replace("&lt;/i&gt;", "</i>")


def compute(papers):
    cites = sorted((p["cited_by_count"] for p in papers), reverse=True)
    h = 0
    for i, c in enumerate(cites, 1):
        if c >= i:
            h = i
    years = [p["year"] for p in papers if p["year"]]
    per_year = {}
    for p in papers:
        for c in p["counts_by_year"]:
            per_year[c["year"]] = per_year.get(c["year"], 0) + c["cited_by_count"]
    return {
        "total_citations": sum(p["cited_by_count"] for p in papers),
        "h_index": h,
        "year_min": min(years),
        "year_max": max(years),
        "per_year": dict(sorted(per_year.items())),
    }


def chart_svg(per_year):
    """Inline SVG bar chart of citations per year, teal bars, 2026 marked partial."""
    W, H = 720, 300
    pad_l, pad_b, pad_t = 44, 34, 16
    plot_w, plot_h = W - pad_l - 16, H - pad_b - pad_t
    years = list(per_year)
    vals = list(per_year.values())
    vmax = max(vals) or 1
    n = len(years)
    gap = 10
    bw = (plot_w - gap * (n - 1)) / n
    partial_year = max(years)  # latest year is partial (current year)

    bars, labels = [], []
    for i, (y, v) in enumerate(per_year.items()):
        x = pad_l + i * (bw + gap)
        bh = (v / vmax) * plot_h
        by = pad_t + plot_h - bh
        cls = "bar partial" if y == partial_year else "bar"
        bars.append(f'<rect class="{cls}" x="{x:.1f}" y="{by:.1f}" '
                    f'width="{bw:.1f}" height="{bh:.1f}" rx="3"><title>{y}: {v} citations'
                    f'{" (partial year)" if y == partial_year else ""}</title></rect>')
        bars.append(f'<text class="barval" x="{x + bw/2:.1f}" y="{by - 5:.1f}">{v}</text>')
        labels.append(f'<text class="axlbl" x="{x + bw/2:.1f}" y="{H - pad_b + 18:.1f}">'
                      f"{str(y)[2:]}</text>")

    # y gridlines
    grid = []
    for frac in (0, 0.5, 1.0):
        gy = pad_t + plot_h - frac * plot_h
        grid.append(f'<line class="grid" x1="{pad_l}" y1="{gy:.1f}" x2="{W-16}" y2="{gy:.1f}"/>')
        grid.append(f'<text class="axlbl" x="{pad_l-8}" y="{gy+4:.1f}" '
                    f'text-anchor="end">{int(vmax*frac)}</text>')

    return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" '
            f'aria-label="Citations per year, {years[0]} to {years[-1]}">'
            + "".join(grid) + "".join(bars) + "".join(labels) + "</svg>")


def paper_row(p):
    title = esc(p["title"])
    link = p.get("link") or p.get("id")
    title_html = f'<a href="{html.escape(link)}" target="_blank" rel="noopener">{title}</a>' if link else title
    venue = html.escape(p.get("venue") or "")
    year = p.get("year") or ""
    cites = p.get("cited_by_count", 0)
    cite_label = f'{cites} citation{"s" if cites != 1 else ""}'
    return (f'<li class="paper"><div class="paper-title">{title_html}</div>'
            f'<div class="paper-meta"><span class="venue">{venue}</span>'
            f'<span class="dot">·</span><span>{year}</span>'
            f'<span class="cite-pill">{cite_label}</span></div></li>')


def main():
    papers = json.load(open("papers.json", encoding="utf-8"))
    stats = compute(papers)
    generated = datetime.date.today().isoformat()

    # sections grouped by type, newest first
    sections = []
    for key, label in TYPE_ORDER:
        group = sorted([p for p in papers if p["type"] == key],
                       key=lambda p: (p["year"] or 0), reverse=True)
        if not group:
            continue
        rows = "".join(paper_row(p) for p in group)
        sections.append(f'<section class="pub-section"><h3>{label} '
                         f'<span class="count">{len(group)}</span></h3>'
                         f'<ul class="paper-list">{rows}</ul></section>')

    span = f'{stats["year_min"]}–{stats["year_max"]}'
    n_years = stats["year_max"] - stats["year_min"] + 1

    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(NAME)} — Publications</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rethink+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root {{
    --navy:#0C015B; --teal:#36C8C8; --teal-deep:#1FA6A6; --gray:#E9E7E8;
    --bg:#ffffff; --fg:#0C015B; --muted:#5b5b7a; --card:#f5f4f6;
    --line:#E9E7E8; --accent:var(--teal-deep); --bar:var(--teal);
  }}
  html[data-theme="dark"] {{
    --bg:#0a0430; --fg:#eceaf7; --muted:#a9a6c6; --card:#171048;
    --line:#2a2270; --accent:var(--teal); --bar:var(--teal);
  }}
  * {{ box-sizing:border-box; }}
  body {{
    margin:0; font-family:'Rethink Sans',system-ui,sans-serif;
    background:var(--bg); color:var(--fg); line-height:1.5;
    transition:background .2s,color .2s;
  }}
  .wrap {{ max-width:860px; margin:0 auto; padding:48px 24px 80px; }}
  header {{ display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }}
  h1 {{ font-size:38px; font-weight:800; letter-spacing:-.02em; margin:0; }}
  .role {{ font-size:18px; color:var(--accent); font-weight:500; margin:6px 0 0; }}
  .orcid {{ font-size:13px; margin:10px 0 0; }}
  .orcid a {{ color:var(--muted); text-decoration:none; font-family:'JetBrains Mono',monospace; }}
  .orcid a:hover {{ color:var(--accent); }}
  .toggle {{
    flex:none; border:1px solid var(--line); background:var(--card); color:var(--fg);
    border-radius:999px; padding:8px 14px; font-family:inherit; font-size:13px;
    font-weight:600; cursor:pointer;
  }}
  .toggle:hover {{ border-color:var(--accent); }}
  .stats {{ display:flex; gap:16px; margin:36px 0 12px; flex-wrap:wrap; }}
  .stat {{ flex:1; min-width:150px; background:var(--card); border:1px solid var(--line);
    border-radius:14px; padding:22px 20px; }}
  .stat .num {{ font-size:40px; font-weight:800; line-height:1; letter-spacing:-.02em;
    color:var(--accent); }}
  .stat .lbl {{ font-size:13px; color:var(--muted); margin-top:8px; text-transform:uppercase;
    letter-spacing:.04em; font-weight:600; }}
  .chart-card {{ background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:22px 20px 12px; margin:20px 0 8px; }}
  .chart-card h2 {{ font-size:16px; margin:0 0 8px; font-weight:700; }}
  .chart-card .note {{ font-size:12px; color:var(--muted); margin:0 0 8px; }}
  .chart {{ width:100%; height:auto; }}
  .chart .bar {{ fill:var(--bar); }}
  .chart .bar.partial {{ fill:var(--bar); opacity:.45; }}
  .chart .barval {{ fill:var(--muted); font-size:10px; text-anchor:middle;
    font-family:'JetBrains Mono',monospace; }}
  .chart .axlbl {{ fill:var(--muted); font-size:11px; text-anchor:middle;
    font-family:'JetBrains Mono',monospace; }}
  .chart .grid {{ stroke:var(--line); stroke-width:1; }}
  .pub-section {{ margin-top:40px; }}
  .pub-section h3 {{ font-size:20px; font-weight:700; border-bottom:2px solid var(--accent);
    padding-bottom:8px; display:flex; align-items:center; gap:10px; }}
  .pub-section h3 .count {{ font-size:13px; color:var(--muted); font-weight:600;
    background:var(--card); border-radius:999px; padding:2px 10px; }}
  .paper-list {{ list-style:none; padding:0; margin:0; }}
  .paper {{ padding:16px 0; border-bottom:1px solid var(--line); }}
  .paper-title {{ font-size:16px; font-weight:600; }}
  .paper-title a {{ color:var(--fg); text-decoration:none; }}
  .paper-title a:hover {{ color:var(--accent); text-decoration:underline; }}
  .paper-meta {{ font-size:13.5px; color:var(--muted); margin-top:5px; display:flex;
    align-items:center; gap:8px; flex-wrap:wrap; }}
  .paper-meta .venue {{ font-style:italic; }}
  .paper-meta .dot {{ opacity:.5; }}
  .cite-pill {{ margin-left:auto; background:var(--card); border:1px solid var(--line);
    border-radius:999px; padding:2px 10px; font-size:12px; font-weight:600;
    color:var(--accent); font-family:'JetBrains Mono',monospace; }}
  footer {{ margin-top:48px; padding-top:20px; border-top:1px solid var(--line);
    font-size:12px; color:var(--muted); font-family:'JetBrains Mono',monospace;
    display:flex; gap:8px; flex-wrap:wrap; }}
  footer .dot {{ opacity:.5; }}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div>
      <h1>{html.escape(NAME)}</h1>
      <p class="role">{html.escape(ROLE)}</p>
      <p class="orcid"><a href="https://orcid.org/{ORCID}" target="_blank" rel="noopener">ORCID {ORCID}</a></p>
    </div>
    <button class="toggle" id="themeToggle" aria-label="Toggle dark mode">🌙 Dark</button>
  </header>

  <div class="stats">
    <div class="stat"><div class="num">{stats['total_citations']:,}</div><div class="lbl">Total citations</div></div>
    <div class="stat"><div class="num">{stats['h_index']}</div><div class="lbl">h-index</div></div>
    <div class="stat"><div class="num">{n_years}</div><div class="lbl">Years active · {span}</div></div>
  </div>

  <div class="chart-card">
    <h2>Citations per year</h2>
    <p class="note">Aggregated across all works via OpenAlex. Latest year is partial (year in progress).</p>
    {chart_svg(stats['per_year'])}
  </div>

  {''.join(sections)}

  <footer>
    <span>Data: OpenAlex</span><span class="dot">·</span>
    <span>Generated {generated}</span><span class="dot">·</span>
    <span>ORCID {ORCID}</span>
  </footer>
</div>
<script>
  (function () {{
    var btn = document.getElementById('themeToggle');
    var root = document.documentElement;
    var saved = null;
    try {{ saved = localStorage.getItem('theme'); }} catch (e) {{}}
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    var theme = saved || (prefersDark ? 'dark' : 'light');
    apply(theme);
    btn.addEventListener('click', function () {{
      theme = (root.getAttribute('data-theme') === 'dark') ? 'light' : 'dark';
      apply(theme);
      try {{ localStorage.setItem('theme', theme); }} catch (e) {{}}
    }});
    function apply(t) {{
      root.setAttribute('data-theme', t);
      btn.textContent = (t === 'dark') ? '☀️ Light' : '🌙 Dark';
    }}
  }})();
</script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(doc)
    print(f"Wrote index.html — {sum(1 for _ in papers)} works, "
          f"{stats['total_citations']:,} citations, h-index {stats['h_index']}.")


if __name__ == "__main__":
    main()
