"""Build index.html from papers.json + coauthor_network.json.

Reads the curated papers.json (Lindsay's personal "breakout") and the Talus
team coauthor_network.json (the "social network"), and writes a single
self-contained, Talus-branded page:
  - personal stats + citations-per-year chart + publications on top
  - the Talus team coauthor network (force-directed canvas, no libraries) below,
    with Lindsay's node highlighted

Data is inlined so the page works both when opened locally and on GitHub Pages.
Re-run after fetch_papers.py to regenerate. Run on Windows with:
  py -X utf8 build_page.py
"""
import datetime
import html
import json

NAME = "Lindsay Pino"
ROLE = "CTO & co-founder, Talus Bio"
ORCID = "0000-0003-1857-7222"
# The team node to highlight as "you" in the network (matches team_members.json).
HIGHLIGHT = "Lindsay K Pino"

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
    """Inline SVG bar chart of citations per year, teal bars, latest year dimmed."""
    W, H = 720, 300
    pad_l, pad_b, pad_t = 44, 34, 16
    plot_w, plot_h = W - pad_l - 16, H - pad_b - pad_t
    years = list(per_year)
    vals = list(per_year.values())
    vmax = max(vals) or 1
    n = len(years)
    gap = 10
    bw = (plot_w - gap * (n - 1)) / n
    partial_year = max(years)

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


BASE_CSS = """
  :root {
    --navy:#0C015B; --teal:#36C8C8; --teal-deep:#1FA6A6; --gray:#E9E7E8;
    --bg:#ffffff; --fg:#0C015B; --muted:#5b5b7a; --card:#f5f4f6;
    --line:#E9E7E8; --accent:var(--teal-deep); --bar:var(--teal);
    /* network colors (light) */
    --net-team:#1FA6A6; --net-coauthor:#9AA6AC; --net-highlight:#594AE1;
    --net-edge:rgba(139,152,160,0.35); --net-edge-dim:rgba(139,152,160,0.12);
    --net-edge-active:rgba(31,166,166,0.6); --net-label-bg:rgba(12,1,91,0.92);
    --net-label-fg:#ffffff; --net-ring:#ffffff;
  }
  html[data-theme="dark"] {
    --bg:#0a0430; --fg:#eceaf7; --muted:#a9a6c6; --card:#171048;
    --line:#2a2270; --accent:var(--teal); --bar:var(--teal);
    --net-team:#36C8C8; --net-coauthor:#8b86b8; --net-highlight:#8a7bff;
    --net-edge:rgba(150,150,190,0.35); --net-edge-dim:rgba(150,150,190,0.12);
    --net-edge-active:rgba(54,200,200,0.7); --net-label-bg:rgba(236,234,247,0.94);
    --net-label-fg:#0a0430; --net-ring:#0a0430;
  }
  * { box-sizing:border-box; }
  body {
    margin:0; font-family:'Rethink Sans',system-ui,sans-serif;
    background:var(--bg); color:var(--fg); line-height:1.5;
    transition:background .2s,color .2s;
  }
  .wrap { max-width:860px; margin:0 auto; padding:48px 24px 80px; }
  header { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }
  h1 { font-size:38px; font-weight:800; letter-spacing:-.02em; margin:0; }
  .role { font-size:18px; color:var(--accent); font-weight:500; margin:6px 0 0; }
  .orcid { font-size:13px; margin:10px 0 0; }
  .orcid a { color:var(--muted); text-decoration:none; font-family:'JetBrains Mono',monospace; }
  .orcid a:hover { color:var(--accent); }
  .toggle {
    flex:none; border:1px solid var(--line); background:var(--card); color:var(--fg);
    border-radius:999px; padding:8px 14px; font-family:inherit; font-size:13px;
    font-weight:600; cursor:pointer;
  }
  .toggle:hover { border-color:var(--accent); }
  .stats { display:flex; gap:16px; margin:36px 0 12px; flex-wrap:wrap; }
  .stat { flex:1; min-width:150px; background:var(--card); border:1px solid var(--line);
    border-radius:14px; padding:22px 20px; }
  .stat .num { font-size:40px; font-weight:800; line-height:1; letter-spacing:-.02em;
    color:var(--accent); }
  .stat .lbl { font-size:13px; color:var(--muted); margin-top:8px; text-transform:uppercase;
    letter-spacing:.04em; font-weight:600; }
  .chart-card { background:var(--card); border:1px solid var(--line); border-radius:14px;
    padding:22px 20px 12px; margin:20px 0 8px; }
  .chart-card h2 { font-size:16px; margin:0 0 8px; font-weight:700; }
  .chart-card .note { font-size:12px; color:var(--muted); margin:0 0 8px; }
  .chart { width:100%; height:auto; }
  .chart .bar { fill:var(--bar); }
  .chart .bar.partial { fill:var(--bar); opacity:.45; }
  .chart .barval { fill:var(--muted); font-size:10px; text-anchor:middle;
    font-family:'JetBrains Mono',monospace; }
  .chart .axlbl { fill:var(--muted); font-size:11px; text-anchor:middle;
    font-family:'JetBrains Mono',monospace; }
  .chart .grid { stroke:var(--line); stroke-width:1; }
  .pub-section { margin-top:40px; }
  .pub-section h3 { font-size:20px; font-weight:700; border-bottom:2px solid var(--accent);
    padding-bottom:8px; display:flex; align-items:center; gap:10px; }
  .pub-section h3 .count { font-size:13px; color:var(--muted); font-weight:600;
    background:var(--card); border-radius:999px; padding:2px 10px; }
  .paper-list { list-style:none; padding:0; margin:0; }
  .paper { padding:16px 0; border-bottom:1px solid var(--line); }
  .paper-title { font-size:16px; font-weight:600; }
  .paper-title a { color:var(--fg); text-decoration:none; }
  .paper-title a:hover { color:var(--accent); text-decoration:underline; }
  .paper-meta { font-size:13.5px; color:var(--muted); margin-top:5px; display:flex;
    align-items:center; gap:8px; flex-wrap:wrap; }
  .paper-meta .venue { font-style:italic; }
  .paper-meta .dot { opacity:.5; }
  .cite-pill { margin-left:auto; background:var(--card); border:1px solid var(--line);
    border-radius:999px; padding:2px 10px; font-size:12px; font-weight:600;
    color:var(--accent); font-family:'JetBrains Mono',monospace; }
  footer { margin-top:48px; padding-top:20px; border-top:1px solid var(--line);
    font-size:12px; color:var(--muted); font-family:'JetBrains Mono',monospace;
    display:flex; gap:8px; flex-wrap:wrap; }
  footer .dot { opacity:.5; }

  /* ---- Talus coauthor network ---- */
  .net-section { margin-top:52px; }
  .net-section h2 { font-size:24px; font-weight:800; letter-spacing:-.01em; margin:0 0 6px; }
  .net-section .lead { font-size:15px; color:var(--muted); margin:0 0 16px; max-width:640px; }
  .network-panel { position:relative; background:var(--card); border:1px solid var(--line);
    border-radius:14px; overflow:hidden; }
  #networkCanvas { display:block; width:100%; cursor:grab; }
  #networkCanvas.dragging { cursor:grabbing; }
  .network-controls { display:flex; align-items:center; gap:10px; padding:10px 14px;
    border-bottom:1px solid var(--line); font-family:'JetBrains Mono',monospace;
    font-size:11px; color:var(--muted); }
  .network-controls button { font-family:'JetBrains Mono',monospace; font-size:11px;
    padding:5px 10px; border:1px solid var(--line); border-radius:6px; background:var(--bg);
    color:var(--muted); cursor:pointer; margin-left:auto; }
  .network-controls button:hover { color:var(--accent); border-color:var(--accent); }
  .net-legend { display:flex; gap:18px; flex-wrap:wrap; margin:14px 0 0; font-size:13px;
    color:var(--muted); align-items:center; }
  .net-legend span { display:flex; align-items:center; gap:7px; }
  .sw-team-dot { width:12px; height:12px; border-radius:50%; background:var(--net-team);
    box-shadow:0 0 0 2px var(--bg),0 0 0 3px var(--net-team); display:inline-block; }
  .sw-you-dot { width:12px; height:12px; border-radius:50%; background:var(--net-highlight);
    box-shadow:0 0 0 2px var(--bg),0 0 0 3px var(--net-highlight); display:inline-block; }
  .sw-coauthor-dot { width:9px; height:9px; border-radius:50%; background:var(--net-coauthor);
    display:inline-block; }
  .net-note { font-size:12px; color:var(--muted); margin:14px 0 0; max-width:640px; }
  .tooltip { position:absolute; background:var(--net-label-bg); color:var(--net-label-fg);
    font-family:'JetBrains Mono',monospace; font-size:11.5px; padding:8px 10px;
    border-radius:6px; pointer-events:none; opacity:0; transition:opacity .1s;
    max-width:240px; line-height:1.4; z-index:10; }
"""


def network_section_html(meta):
    excluded = meta.get("papers_excluded_consortium_scale", 0)
    threshold = meta.get("max_authors_threshold", 40)
    return f"""
  <section class="net-section">
    <h2>Inside the Talus collaboration network</h2>
    <p class="lead">My publications don't stand alone — they're woven into Talus Bio's
      wider web of collaborators. Below is the coauthor network of the whole team:
      each teammate (teal) sits on a ring, and every coauthor (grey) settles near
      whoever they've published with. <strong>My node is highlighted in purple.</strong>
      Hover a name to trace its collaborations; scroll to zoom, drag to pan.</p>
    <div class="network-panel">
      <div class="network-controls">
        <span>Scroll to zoom · drag background to pan · drag a coauthor to reposition</span>
        <button id="networkReset">Reset view</button>
      </div>
      <canvas id="networkCanvas"></canvas>
    </div>
    <div class="net-legend">
      <span><i class="sw-you-dot"></i>Me (Lindsay)</span>
      <span><i class="sw-team-dot"></i>Talus team member</span>
      <span><i class="sw-coauthor-dot"></i>Coauthor</span>
    </div>
    <p class="net-note">{excluded} large consortium paper(s) (more than {threshold} authors)
      are left out of this graph — including one would connect a team member to hundreds of
      one-off coauthors and bury every real collaboration under the noise. Team publication
      and coauthor data via PubMed and Semantic Scholar.</p>
  </section>
"""


TOGGLE_JS = """
  (function () {
    var btn = document.getElementById('themeToggle');
    var root = document.documentElement;
    var saved = null;
    try { saved = localStorage.getItem('theme'); } catch (e) {}
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    var theme = saved || (prefersDark ? 'dark' : 'light');
    apply(theme);
    btn.addEventListener('click', function () {
      theme = (root.getAttribute('data-theme') === 'dark') ? 'light' : 'dark';
      apply(theme);
      try { localStorage.setItem('theme', theme); } catch (e) {}
    });
    function apply(t) {
      root.setAttribute('data-theme', t);
      btn.textContent = (t === 'dark') ? '\\u2600\\ufe0f Light' : '\\ud83c\\udf19 Dark';
      if (window.__netRedraw) window.__netRedraw();  // recolor canvas for the new theme
    }
  })();
"""

# Force-directed coauthor network, ported from the Talus team dashboard. Plain
# JS canvas (no libraries). Colors are read from CSS variables at draw time so
# the graph follows the page's light/dark theme. Lindsay's node is highlighted.
NETWORK_JS = r"""
(function () {
  var NETWORK = __NETWORK_JSON__;
  var HIGHLIGHT = "__HIGHLIGHT__";
  function cssVar(name){ return getComputedStyle(document.documentElement).getPropertyValue(name).trim(); }

  var tooltip = document.getElementById("netTooltip");
  function showTooltip(evt, htmlStr){
    tooltip.innerHTML = htmlStr; tooltip.style.opacity = 1;
    tooltip.style.left = (evt.pageX + 12) + "px";
    tooltip.style.top = (evt.pageY - 10) + "px";
  }
  function hideTooltip(){ tooltip.style.opacity = 0; }

  var TEAM_RADIUS = 260;
  var teamLabels = NETWORK.nodes.filter(function(n){return n.type==="team";}).map(function(n){return n.label;}).sort();
  var teamAngle = {};
  teamLabels.forEach(function(label,i){ teamAngle[label] = -Math.PI/2 + i*(2*Math.PI/teamLabels.length); });

  var nodesById = {};
  var nodes = NETWORK.nodes.map(function(n){
    var isTeam = n.type === "team";
    var x, y, fx = null, fy = null;
    if(isTeam){
      var ang = teamAngle[n.label];
      x = Math.cos(ang)*TEAM_RADIUS; y = Math.sin(ang)*TEAM_RADIUS;
      fx = x; fy = y;
    } else {
      x = (Math.random()-0.5)*700; y = (Math.random()-0.5)*700;
    }
    var o = {
      id:n.id, label:n.label, type:n.type, papers:n.papers,
      x:x, y:y, vx:0, vy:0, fx:fx, fy:fy,
      highlight: (n.label === HIGHLIGHT),
      r: isTeam ? 8 + Math.min(n.papers,40)*0.14 : 2.5 + Math.min(n.papers-1,8)*0.5
    };
    nodesById[n.id] = o;
    return o;
  });
  var edges = NETWORK.edges
    .map(function(e){ return {source:nodesById[e.source], target:nodesById[e.target], weight:e.weight}; })
    .filter(function(e){ return e.source && e.target; });
  var neighbors = {};
  nodes.forEach(function(n){ neighbors[n.id]=new Set(); });
  edges.forEach(function(e){ neighbors[e.source.id].add(e.target.id); neighbors[e.target.id].add(e.source.id); });

  var canvas = document.getElementById("networkCanvas");
  var ctx = canvas.getContext("2d");
  if(!ctx) return;
  var wrap = canvas.parentElement;
  var reduceMotion = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var width, height, dpr;
  var view = {x:0, y:0, k:1};
  function resize(){
    dpr = window.devicePixelRatio || 1;
    width = wrap.clientWidth; height = 560;
    canvas.width = Math.round(width*dpr); canvas.height = Math.round(height*dpr);
    canvas.style.width = width+"px"; canvas.style.height = height+"px";
    ctx.setTransform(dpr,0,0,dpr,0,0);
    view.x = width/2; view.y = height/2;
  }
  resize();
  window.addEventListener("resize", function(){ resize(); draw(); });
  function screenToWorld(sx,sy){ return [(sx-view.x)/view.k, (sy-view.y)/view.k]; }

  var CHARGE = -110, LINK_DIST = 55, LINK_STRENGTH = 0.4, CENTER_STRENGTH = 0.01, MAX_SPEED = 40;
  var alpha = 1;
  function tick(){
    for(var i=0;i<nodes.length;i++){
      var a = nodes[i];
      for(var j=i+1;j<nodes.length;j++){
        var b = nodes[j];
        var dx = a.x-b.x, dy = a.y-b.y;
        var distSq = Math.max(dx*dx+dy*dy, 1);
        if(distSq > 90000) continue;
        var dist = Math.sqrt(distSq);
        var force = CHARGE/distSq*alpha;
        var fx = dx/dist*force, fy = dy/dist*force;
        a.vx -= fx; a.vy -= fy; b.vx += fx; b.vy += fy;
      }
    }
    edges.forEach(function(e){
      var a=e.source, b=e.target;
      var dx=b.x-a.x, dy=b.y-a.y;
      var dist = Math.max(Math.sqrt(dx*dx+dy*dy), 0.01);
      var f = (dist-LINK_DIST)/dist*LINK_STRENGTH*alpha;
      var fx=dx*f, fy=dy*f;
      a.vx += fx; a.vy += fy; b.vx -= fx; b.vy -= fy;
    });
    nodes.forEach(function(n){ n.vx += -n.x*CENTER_STRENGTH*alpha; n.vy += -n.y*CENTER_STRENGTH*alpha; });
    nodes.forEach(function(n){
      if(n.fx!=null){ n.x=n.fx; n.y=n.fy; n.vx=0; n.vy=0; return; }
      n.vx *= 0.82; n.vy *= 0.82;
      var speed = Math.sqrt(n.vx*n.vx+n.vy*n.vy);
      if(speed > MAX_SPEED){ n.vx *= MAX_SPEED/speed; n.vy *= MAX_SPEED/speed; }
      n.x += n.vx; n.y += n.vy;
    });
    alpha *= 0.988;
  }

  var hovered = null, running = false;
  function loop(){
    if(alpha > 0.015){ tick(); draw(); requestAnimationFrame(loop); }
    else { running = false; draw(); }
  }
  function restart(a){ alpha = Math.max(alpha, a); if(!running){ running = true; requestAnimationFrame(loop); } }
  if(reduceMotion){ for(var s=0;s<400;s++) tick(); } else { running = true; requestAnimationFrame(loop); }

  function draw(){
    var C = {
      team: cssVar("--net-team"), coauthor: cssVar("--net-coauthor"),
      highlight: cssVar("--net-highlight"), edge: cssVar("--net-edge"),
      edgeDim: cssVar("--net-edge-dim"), edgeActive: cssVar("--net-edge-active"),
      labelBg: cssVar("--net-label-bg"), labelFg: cssVar("--net-label-fg"),
      ring: cssVar("--net-ring")
    };
    ctx.clearRect(0,0,width,height);
    ctx.save();
    ctx.translate(view.x, view.y); ctx.scale(view.k, view.k);
    var focus = hovered ? neighbors[hovered.id] : null;
    function dim(n){ return focus && n.id!==hovered.id && !focus.has(n.id); }

    edges.forEach(function(e){
      var active = hovered && (e.source.id===hovered.id || e.target.id===hovered.id);
      ctx.globalAlpha = dim(e.source) && dim(e.target) ? 0.5 : 1;
      ctx.strokeStyle = active ? C.edgeActive : (focus ? C.edgeDim : C.edge);
      ctx.lineWidth = Math.min(5, 0.6 + Math.log2(e.weight+1)*1.1)/view.k;
      ctx.beginPath(); ctx.moveTo(e.source.x, e.source.y); ctx.lineTo(e.target.x, e.target.y); ctx.stroke();
    });
    ctx.globalAlpha = 1;

    nodes.filter(function(n){return n.type==="coauthor";}).forEach(function(n){
      ctx.beginPath();
      ctx.globalAlpha = dim(n) ? 0.35 : 1;
      ctx.fillStyle = (n===hovered) ? C.highlight : C.coauthor;
      ctx.arc(n.x, n.y, n.r, 0, Math.PI*2); ctx.fill();
    });
    ctx.globalAlpha = 1;
    nodes.filter(function(n){return n.type==="team";}).forEach(function(n){
      var r = n.highlight ? n.r + 2 : n.r;
      ctx.beginPath();
      ctx.globalAlpha = dim(n) ? 0.4 : 1;
      ctx.fillStyle = n.highlight ? C.highlight : C.team;
      ctx.arc(n.x, n.y, r, 0, Math.PI*2); ctx.fill();
      ctx.lineWidth = (n.highlight ? 3 : 2)/view.k;
      ctx.strokeStyle = C.ring; ctx.stroke();
    });
    ctx.globalAlpha = 1;
    ctx.restore();

    ctx.font = "600 11px " + getComputedStyle(document.body).fontFamily;
    ctx.textBaseline = "middle";
    nodes.filter(function(n){return n.type==="team";}).forEach(function(n){
      var sx = view.x + n.x*view.k, sy = view.y + n.y*view.k;
      var label = n.highlight ? (n.label + " (me)") : n.label;
      var tw = ctx.measureText(label).width;
      ctx.fillStyle = n.highlight ? C.highlight : C.labelBg;
      ctx.fillRect(sx+n.r*view.k+4, sy-8, tw+8, 16);
      ctx.fillStyle = n.highlight ? "#ffffff" : C.labelFg;
      ctx.fillText(label, sx+n.r*view.k+8, sy);
    });
    if(hovered && hovered.type==="coauthor"){
      var hx = view.x + hovered.x*view.k, hy = view.y + hovered.y*view.k;
      var htw = ctx.measureText(hovered.label).width;
      ctx.fillStyle = C.labelBg;
      ctx.fillRect(hx+hovered.r*view.k+4, hy-8, htw+8, 16);
      ctx.fillStyle = C.labelFg;
      ctx.fillText(hovered.label, hx+hovered.r*view.k+8, hy);
    }
  }
  window.__netRedraw = draw;  // let the theme toggle recolor the canvas

  function nodeAt(sx, sy){
    var wc = screenToWorld(sx, sy), wx = wc[0], wy = wc[1];
    var best = null, bestDist = Infinity;
    for(var i=0;i<nodes.length;i++){
      var n = nodes[i];
      var dx = n.x-wx, dy = n.y-wy; var d = Math.sqrt(dx*dx+dy*dy);
      var hitR = Math.max(n.r, 6/view.k);
      if(d <= hitR && d < bestDist){ best = n; bestDist = d; }
    }
    return best;
  }

  var dragNode = null, panning = false, panStart = null, viewStart = null;
  canvas.addEventListener("mousedown", function(evt){
    var rect = canvas.getBoundingClientRect();
    var sx = evt.clientX-rect.left, sy = evt.clientY-rect.top;
    var hit = nodeAt(sx, sy);
    if(hit && hit.type === "coauthor"){
      dragNode = hit;
      var wc = screenToWorld(sx,sy); dragNode.fx = wc[0]; dragNode.fy = wc[1];
      restart(0.3); canvas.classList.add("dragging");
    } else if(!hit){
      panning = true; panStart = [evt.clientX, evt.clientY]; viewStart = [view.x, view.y];
      canvas.classList.add("dragging");
    }
  });
  window.addEventListener("mousemove", function(evt){
    var rect = canvas.getBoundingClientRect();
    var sx = evt.clientX-rect.left, sy = evt.clientY-rect.top;
    if(dragNode){ var wc = screenToWorld(sx,sy); dragNode.fx = wc[0]; dragNode.fy = wc[1]; if(!running) draw(); return; }
    if(panning){ view.x = viewStart[0] + (evt.clientX-panStart[0]); view.y = viewStart[1] + (evt.clientY-panStart[1]); if(!running) draw(); return; }
    if(sx<0 || sy<0 || sx>width || sy>height){ if(hovered){hovered=null; hideTooltip(); if(!running) draw();} return; }
    var hit = nodeAt(sx, sy);
    if(hit !== hovered){ hovered = hit; if(!running) draw(); }
    if(hit){
      var label = hit.type==="team"
        ? "<strong>"+hit.label+(hit.highlight?" (me)":"")+"</strong><br>Talus team member · "+hit.papers+" paper(s) in this network"
        : "<strong>"+hit.label+"</strong><br>Coauthor · "+hit.papers+" shared paper(s)";
      showTooltip(evt, label);
    } else { hideTooltip(); }
  });
  window.addEventListener("mouseup", function(){
    if(dragNode){ dragNode.fx = null; dragNode.fy = null; restart(0.15); }
    dragNode = null; panning = false; canvas.classList.remove("dragging");
  });
  canvas.addEventListener("mouseleave", function(){ hovered=null; hideTooltip(); if(!running) draw(); });
  canvas.addEventListener("wheel", function(evt){
    evt.preventDefault();
    var rect = canvas.getBoundingClientRect();
    var sx = evt.clientX-rect.left, sy = evt.clientY-rect.top;
    var wc = screenToWorld(sx,sy);
    var factor = evt.deltaY < 0 ? 1.12 : 1/1.12;
    view.k = Math.min(6, Math.max(0.15, view.k*factor));
    view.x = sx - wc[0]*view.k; view.y = sy - wc[1]*view.k;
    if(!running) draw();
  }, {passive:false});
  document.getElementById("networkReset").addEventListener("click", function(){
    view.k = 1; view.x = width/2; view.y = height/2; draw();
  });
  draw();
})();
"""


def main():
    papers = json.load(open("papers.json", encoding="utf-8"))
    network = json.load(open("coauthor_network.json", encoding="utf-8"))
    stats = compute(papers)
    generated = datetime.date.today().isoformat()

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

    net_js = (NETWORK_JS
              .replace("__NETWORK_JSON__", json.dumps(network))
              .replace("__HIGHLIGHT__", HIGHLIGHT))

    head = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(NAME)} — Publications</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Rethink+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{BASE_CSS}</style>
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

  {network_section_html(network.get('meta', {}))}

  <footer>
    <span>Personal data: OpenAlex</span><span class="dot">·</span>
    <span>Network: PubMed + Semantic Scholar</span><span class="dot">·</span>
    <span>Generated {generated}</span><span class="dot">·</span>
    <span>ORCID {ORCID}</span>
  </footer>
</div>
<div class="tooltip" id="netTooltip"></div>
<script>{TOGGLE_JS}</script>
<script>{net_js}</script>
</body>
</html>
"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(head)
    n_team = sum(1 for n in network["nodes"] if n["type"] == "team")
    print(f"Wrote index.html — {len(papers)} works, {stats['total_citations']:,} citations, "
          f"h-index {stats['h_index']}; network: {len(network['nodes'])} nodes "
          f"({n_team} team), {len(network['edges'])} edges.")


if __name__ == "__main__":
    main()
