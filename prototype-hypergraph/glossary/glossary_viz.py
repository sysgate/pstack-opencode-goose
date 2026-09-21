#!/usr/bin/env python3
"""Render the CHI glossary hypergraph as ONE self-contained HTML page (offline, no server).

    python3 glossary_viz.py                 # reads ../../hypergraph-db/chi_hypergraph.PROTOTYPE.sqlite3, writes chi-glossary-hypergraph.html
    python3 glossary_viz.py --out /tmp/g.html
    python3 glossary_viz.py --db chi-glossary.PROTOTYPE-rebuildable.sqlite3   # the old, frozen prototype store

The default is the current store described in hypergraph-db/README.md ("Which store is which"). It is opened READ-ONLY,
so it is safe while another session is writing to it. The page is a SNAPSHOT: it does not follow later changes. To pick
up new glossary entries, rebuild that store from the Markdown (see hypergraph-db/README.md), then run this script again.
The page header shows which store it came from and when it was generated.

Rendering: a hypergraph cannot be drawn by an ordinary graph library directly, so each hyperedge (a CLAIM) becomes its
own small diamond node joined to its members: SUBJECT -> claim -> OBJECT, plus a dashed CONDITION link when the claim
has one. The claim's PREDICATE is shown as the diamond's colour and label instead of as a link, because the four
predicate objects would otherwise be giant hubs (up to 135 links each); a checkbox draws them if wanted.

Cytoscape.js is pinned by version and SHA-256, downloaded once into ./.viz-cache/ (gitignored) and inlined, so the
finished page needs no network. Standard library only. The output holds glossary text from the source Markdown, and
absolute paths are reduced to file names.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import sqlite3
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB = os.path.normpath(os.path.join(HERE, "..", "..", "hypergraph-db", "chi_hypergraph.PROTOTYPE.sqlite3"))
DEFAULT_OUT = os.path.join(HERE, "chi-glossary-hypergraph.html")
CACHE_DIR = os.path.join(HERE, ".viz-cache")
CYTOSCAPE_VERSION = "3.30.2"
CYTOSCAPE_URL = f"https://cdnjs.cloudflare.com/ajax/libs/cytoscape/{CYTOSCAPE_VERSION}/cytoscape.min.js"
CYTOSCAPE_SHA256 = "83e8c54a6bec655bfd81df07df605649c268af69aeca67a5ea2da54ea42dac81"
TEXT_LIMIT = 700


def cytoscape_source() -> str:
    """The pinned library text: from the cache when its hash matches, else downloaded, verified, then cached."""
    path = os.path.join(CACHE_DIR, f"cytoscape-{CYTOSCAPE_VERSION}.min.js")
    if os.path.isfile(path):
        data = open(path, "rb").read()
        if hashlib.sha256(data).hexdigest() == CYTOSCAPE_SHA256:
            return data.decode("utf-8")
    with urllib.request.urlopen(CYTOSCAPE_URL, timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != CYTOSCAPE_SHA256:
        sys.exit("ABORT: downloaded Cytoscape.js does not match the pinned SHA-256; nothing was written")
    os.makedirs(CACHE_DIR, exist_ok=True)
    open(path, "wb").write(data)
    return data.decode("utf-8")


ABS_PATH = re.compile(r"(?:file://)?/(?:Users|home|private|var|tmp|Volumes)/(?:[^/\s\"'`<>]+/)*([^/\s\"'`<>]+)")


def scrub(text: str) -> str:
    """Reduce every absolute filesystem path inside a text to its file name (the store keeps full source paths)."""
    return ABS_PATH.sub(lambda m: m.group(1), text)


def clip(value, limit: int = TEXT_LIMIT):
    if value is None:
        return None
    text = scrub(str(value))
    return text if len(text) <= limit else text[: limit - 1] + "…"


def source_name(value):
    """Reduce an absolute source path to its file name; leave non-paths (such as 'glossary model') alone."""
    return scrub(value) if isinstance(value, str) else value


def export(db_path: str) -> dict:
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    objects = {}
    for r in conn.execute("SELECT id, type, label, scope, source_context, dsn_state, admission_state, meanings, "
                          "narrowing_basis, original_text FROM semantic_objects ORDER BY type, label"):
        objects[r["id"]] = {
            "id": r["id"], "type": r["type"], "label": r["label"], "scope": r["scope"],
            "source": source_name(r["source_context"]), "dsn": r["dsn_state"], "admission": r["admission_state"],
            "meanings": clip(r["meanings"], 300), "basis": clip(r["narrowing_basis"], 300),
            "original": clip(r["original_text"], 300),
        }
    members: dict[str, list] = {}
    for r in conn.execute("SELECT hyperedge_id, node_id, role, ordinal FROM hyperedge_members ORDER BY hyperedge_id, ordinal"):
        members.setdefault(r["hyperedge_id"], []).append({"node": r["node_id"], "role": r["role"]})
    evidence: dict[str, list] = {}
    for r in conn.execute("SELECT he.hyperedge_id, he.polarity, e.authority_tier, e.extracted_text, e.provenance_uri "
                          "FROM hyperedge_evidence he JOIN evidence_records e ON e.id = he.evidence_id "
                          "WHERE he.void_reason IS NULL"):
        evidence.setdefault(r["hyperedge_id"], []).append({
            "polarity": r["polarity"], "tier": r["authority_tier"],
            "text": clip(r["extracted_text"]), "source": source_name(r["provenance_uri"])})
    claims = []
    for r in conn.execute("SELECT id, relation_type, scope, admission_state, confidence_bound, receipt_id "
                          "FROM hyperedges ORDER BY id"):
        ms = members.get(r["id"], [])
        predicate = next((objects[m["node"]]["label"] for m in ms if m["role"] == "PREDICATE"), r["relation_type"])
        claims.append({"id": r["id"], "relation": r["relation_type"], "scope": r["scope"], "admission": r["admission_state"],
                       "confidence": r["confidence_bound"], "receipt": r["receipt_id"], "predicate": predicate,
                       "members": ms, "evidence": evidence.get(r["id"], [])})
    chain = conn.execute("SELECT COUNT(*) AS n, MAX(seq) AS head FROM receipts").fetchone()
    conn.close()
    known = set(objects)
    for c in claims:
        for m in c["members"]:
            if m["node"] not in known:
                sys.exit(f"ABORT: claim {c['id']} names an unknown object {m['node']}")
    return {"objects": list(objects.values()), "claims": claims, "receipts": {"count": chain["n"], "head_seq": chain["head"]},
            "store": os.path.basename(db_path),
            "generated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}


def render(data: dict, library: str) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return (TEMPLATE.replace("__CYTOSCAPE_VERSION__", CYTOSCAPE_VERSION)
                    .replace("/*__DATA__*/{}", payload)
                    .replace("/*__CYTOSCAPE__*/", library.replace("</script", "<\\/script")))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--db", default=DEFAULT_DB)
    ap.add_argument("--out", default=DEFAULT_OUT)
    args = ap.parse_args()
    if not os.path.isfile(args.db):
        sys.exit(f"store not found: {args.db}\nThe current store is built as described in hypergraph-db/README.md "
                 f"(the old prototype store: python3 glossary_load.py --rebuild, then pass it with --db).")
    data = export(args.db)
    leftover = ABS_PATH.search(json.dumps(data, ensure_ascii=False))
    if leftover:
        sys.exit(f"ABORT: an absolute path survived scrubbing ({leftover.group(0)[:40]}...); nothing was written")
    html = render(data, cytoscape_source())
    with open(args.out, "w", encoding="utf-8") as handle:
        handle.write(html)
    print(f"wrote {args.out}  ({len(html) / 1024:.0f} KB)  objects={len(data['objects'])} claims={len(data['claims'])} "
          f"receipts={data['receipts']['count']}")
    return 0


TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>CHI glossary hypergraph</title>
<style>
:root{--bg:#fafaf9;--panel:#ffffff;--ink:#1c1917;--muted:#57534e;--line:#d6d3d1;--accent:#1d4ed8;--canvas:#f5f5f4;--edge:#a8a29e;--dim:.14}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#171412;--panel:#1f1b18;--ink:#f5f5f4;--muted:#a8a29e;--line:#3a3532;--accent:#93c5fd;--canvas:#131110;--edge:#57534e}}
:root[data-theme="dark"]{--bg:#171412;--panel:#1f1b18;--ink:#f5f5f4;--muted:#a8a29e;--line:#3a3532;--accent:#93c5fd;--canvas:#131110;--edge:#57534e}
*{box-sizing:border-box}
html,body{height:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,-apple-system,Segoe UI,sans-serif}
.app{display:grid;grid-template-columns:minmax(0,1fr) 340px;grid-template-rows:auto minmax(0,1fr);height:100vh}
header{grid-column:1/-1;display:flex;flex-wrap:wrap;gap:8px 16px;align-items:center;padding:10px 16px;border-bottom:1px solid var(--line);background:var(--panel)}
h1{font-size:16px;margin:0;font-weight:650}
.stats{color:var(--muted);font-size:12.5px}
.spacer{flex:1}
input[type=search]{min-width:200px;padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit}
button{padding:6px 10px;border:1px solid var(--line);border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;cursor:pointer}
button:hover{border-color:var(--accent)}
:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
#cy{background:var(--canvas);min-height:320px}
aside{overflow:auto;padding:14px 16px;border-left:1px solid var(--line);background:var(--panel)}
aside h2{font-size:12px;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin:16px 0 6px}
aside h2:first-child{margin-top:0}
.legend,.filters{display:grid;gap:5px}
.row{display:flex;align-items:center;gap:8px}
.sw{width:14px;height:14px;flex:none;border-radius:50%;border:2px solid transparent}
.sw.diamond{border-radius:2px;transform:rotate(45deg) scale(.8)}
.sw.hex{border-radius:4px}
.note{color:var(--muted);font-size:12.5px}
#detail dl{margin:0;display:grid;grid-template-columns:auto 1fr;gap:3px 10px}
#detail dt{color:var(--muted)}
#detail dd{margin:0;overflow-wrap:anywhere}
#detail blockquote{margin:6px 0 0;padding:6px 10px;border-left:3px solid var(--line);color:var(--muted);font-size:13px;overflow-wrap:anywhere}
#tip{position:fixed;pointer-events:none;background:var(--ink);color:var(--bg);padding:3px 8px;border-radius:5px;font-size:12px;display:none;z-index:5;max-width:320px}
@media (max-width:820px){.app{grid-template-columns:1fr;grid-template-rows:auto minmax(320px,60vh) auto;height:auto}aside{border-left:0;border-top:1px solid var(--line)}}
</style>
</head>
<body>
<div class="app">
<header>
  <h1>CHI glossary hypergraph</h1>
  <span class="stats" id="stats"></span>
  <span class="spacer"></span>
  <input id="q" type="search" placeholder="Search terms, aliases, contexts…" aria-label="Search the glossary">
  <button id="relayout" type="button">Re-layout</button>
  <button id="fit" type="button">Fit</button>
  <span class="stats" id="snap" style="flex-basis:100%"></span>
</header>
<div id="cy" role="img" aria-label="Glossary hypergraph: terms, contexts and groups joined through claim nodes"></div>
<aside>
  <h2>What you are looking at</h2>
  <p class="note" id="explain"></p>
  <h2>Objects (circles)</h2><div class="legend" id="legend-objects"></div>
  <h2>Claims (diamonds, by predicate)</h2><div class="legend" id="legend-claims"></div>
  <h2>Outline = scope</h2><div class="legend" id="legend-scope"></div>
  <h2>Show</h2><div class="filters" id="filters"></div>
  <h2>Selected</h2>
  <div id="detail"><p class="note">Click a node to see what it is, what supports it and its neighbours. Click the background to clear.</p></div>
</aside>
</div>
<div id="tip"></div>
<script>/*__CYTOSCAPE__*/</script>
<script>
"use strict";
const DATA = /*__DATA__*/{};
const OBJ_COLORS = {"Term":"#4e79a7","Avoided alias":"#f28e2b","Avoid note":"#b07aa1","Context":"#59a14f","Glossary group":"#e15759","Outside usage":"#76b7b2","Predicate":"#9c9c9c"};
const OBJ_SHAPE = {"Context":"round-rectangle","Glossary group":"round-hexagon","Predicate":"round-tag"};
const PRED_COLORS = {"is defined in":"#1b9e77","belongs to group":"#7570b3","is avoided in favour of":"#d95f02","must not be confused with":"#e7298a"};
const SCOPE_STYLE = {"CCGF hypergraph":{style:"solid",width:3,name:"CCGF hypergraph"},"Permission gate":{style:"dashed",width:3,name:"Permission gate"},"platform-glossary":{style:"solid",width:0,name:"Platform glossary (contexts, groups, predicates)"},"other":{style:"dotted",width:3,name:"Other scope (outside usage, named elsewhere)"}};
const ROLE_ORDER = {"SUBJECT":0,"PREDICATE":1,"OBJECT":2,"CONDITION":3};
const hidden = new Set(["Predicate"]);      // predicate hubs are drawn only on request
const byId = Object.fromEntries(DATA.objects.map(o => [o.id, o]));
const claimById = Object.fromEntries(DATA.claims.map(c => [c.id, c]));

const els = [];
for (const o of DATA.objects) els.push({group:"nodes",data:{id:o.id,label:o.label,kind:"object",type:o.type,scope:o.scope}});
for (const c of DATA.claims) {
  els.push({group:"nodes",data:{id:c.id,label:c.predicate,kind:"claim",type:"claim",predicate:c.predicate,scope:c.scope}});
  for (const m of c.members) {
    els.push({group:"edges",data:{id:c.id+"|"+m.role+"|"+m.node,source:m.role==="OBJECT"?c.id:(m.role==="SUBJECT"||m.role==="CONDITION"?m.node:c.id),
      target:m.role==="OBJECT"?m.node:(m.role==="SUBJECT"||m.role==="CONDITION"?c.id:m.node),role:m.role}});
  }
}
const cssVar = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
function styleSheet(){
  const ink = cssVar("--ink"), edge = cssVar("--edge"), canvas = cssVar("--canvas");
  return [
    {selector:"node",style:{"label":"data(label)","font-size":9,"color":ink,"text-valign":"bottom","text-margin-y":3,"text-wrap":"ellipsis","text-max-width":90,"min-zoomed-font-size":9,"text-outline-color":canvas,"text-outline-width":2,"width":15,"height":15}},
    ...Object.entries(OBJ_COLORS).map(([t,col]) => ({selector:`node[type = "${t}"]`,style:{"background-color":col,"shape":OBJ_SHAPE[t]||"ellipse"}})),
    {selector:'node[type = "Context"]',style:{"width":46,"height":28,"font-size":13,"font-weight":700,"min-zoomed-font-size":0,"text-valign":"center","text-margin-y":0,"color":"#fff","text-outline-color":OBJ_COLORS.Context,"text-max-width":120}},
    {selector:'node[type = "Glossary group"]',style:{"width":36,"height":26,"font-size":11,"font-weight":600,"min-zoomed-font-size":0,"text-max-width":110}},
    {selector:'node[type = "Term"]',style:{"width":20,"height":20}},
    {selector:'node[type = "Predicate"]',style:{"width":24,"height":14,"font-size":9}},
    {selector:'node[scope = "CCGF hypergraph"][kind = "object"]',style:{"border-width":3,"border-style":"solid","border-color":ink}},
    {selector:'node[scope = "Permission gate"][kind = "object"]',style:{"border-width":3,"border-style":"dashed","border-color":ink}},
    {selector:'node[kind = "object"][scope != "CCGF hypergraph"][scope != "Permission gate"][scope != "platform-glossary"]',style:{"border-width":3,"border-style":"dotted","border-color":ink}},
    {selector:'node[kind = "claim"]',style:{"shape":"diamond","width":11,"height":11,"label":"","background-color":ele => PRED_COLORS[ele.data("predicate")]||"#777","border-width":0}},
    {selector:"edge",style:{"width":1,"line-color":edge,"curve-style":"bezier","opacity":.75}},
    {selector:'edge[role = "OBJECT"]',style:{"target-arrow-shape":"triangle","target-arrow-color":edge,"arrow-scale":.7}},
    {selector:'edge[role = "CONDITION"]',style:{"line-style":"dashed","label":"when","font-size":8,"color":ink,"text-outline-color":canvas,"text-outline-width":2,"min-zoomed-font-size":8}},
    {selector:'edge[role = "PREDICATE"]',style:{"line-style":"dotted","opacity":.5}},
    {selector:".off",style:{"display":"none"}},
    {selector:".dim",style:{"opacity":+cssVar("--dim")||.14}},
    {selector:".hit",style:{"border-width":4,"border-color":"#facc15","z-index":10}},
    {selector:"node:selected",style:{"border-width":4,"border-color":"#facc15"}}
  ];
}
const cy = cytoscape({container:document.getElementById("cy"),elements:els,style:styleSheet(),wheelSensitivity:.25,minZoom:.05,maxZoom:5,boxSelectionEnabled:false});

function visibleSet(){
  cy.batch(() => {
    cy.elements().removeClass("off");
    cy.nodes().filter(n => n.data("kind")==="object" && hidden.has(n.data("type"))).addClass("off");
    if (hidden.has("claim")) cy.nodes('[kind = "claim"]').addClass("off");
    cy.edges().filter(e => e.source().hasClass("off") || e.target().hasClass("off")).addClass("off");
    // a claim whose subject or object is hidden would dangle: hide it too, then re-check its links
    cy.nodes('[kind = "claim"]').forEach(cl => { if (cl.connectedEdges().filter(e => !e.hasClass("off")).length < 2) cl.addClass("off"); });
    cy.edges().filter(e => e.source().hasClass("off") || e.target().hasClass("off")).addClass("off");
    // the predicate role is a colour, not a link, unless predicate hubs are shown
    if (hidden.has("Predicate")) cy.edges('[role = "PREDICATE"]').addClass("off");
  });
}
function layout(){
  cy.resize();
  const vis = cy.elements(":visible");
  vis.layout({name:"cose",animate:false,randomize:true,nodeRepulsion:() => 14000,idealEdgeLength:() => 46,edgeElasticity:() => 90,gravity:.9,numIter:1800,nodeOverlap:8,padding:30}).run();
  cy.fit(vis, 30);
}
function refresh(){ visibleSet(); layout(); }

// ---------- legend, filters, stats ----------
const counts = {}; DATA.objects.forEach(o => counts[o.type] = (counts[o.type]||0) + 1);
for (const t of Object.keys(counts)) if (!(t in OBJ_COLORS)) OBJ_COLORS[t] = "#bab0ac";   // unknown type: neutral colour, still listed
const sw = (cls, bg, extra="") => `<span class="sw ${cls}" style="background:${bg};${extra}"></span>`;
document.getElementById("legend-objects").innerHTML = Object.keys(OBJ_COLORS).map(t =>
  `<div class="row">${sw(t==="Context"||t==="Glossary group"?"hex":"",OBJ_COLORS[t])}<span>${t}</span><span class="note">${counts[t]||0}</span></div>`).join("");
const predCounts = {}; DATA.claims.forEach(c => predCounts[c.predicate] = (predCounts[c.predicate]||0) + 1);
document.getElementById("legend-claims").innerHTML = Object.entries(PRED_COLORS).map(([p,col]) =>
  `<div class="row">${sw("diamond",col)}<span>${p}</span><span class="note">${predCounts[p]||0}</span></div>`).join("");
document.getElementById("legend-scope").innerHTML = Object.values(SCOPE_STYLE).map(s =>
  `<div class="row"><span class="sw" style="background:transparent;border:${s.width?s.width:1}px ${s.style} ${s.width?"currentColor":"var(--line)"}"></span><span>${s.name}</span></div>`).join("");
const FILTER_LABEL = {"Term":"Terms","Avoided alias":"Avoided aliases","Avoid note":"Avoid notes","Context":"Contexts","Glossary group":"Glossary groups","Outside usage":"Outside usages","Predicate":"Predicate hubs (noisy)","claim":"Claim diamonds"};
document.getElementById("filters").innerHTML = [...Object.keys(OBJ_COLORS).filter(t => counts[t]), "claim"].map(t => {
  const label = FILTER_LABEL[t] || t;
  return `<label class="row"><input type="checkbox" data-t="${t}" ${hidden.has(t)?"":"checked"}><span>${label}</span></label>`; }).join("");
document.getElementById("filters").addEventListener("change", e => { const t = e.target.dataset.t; e.target.checked ? hidden.delete(t) : hidden.add(t); refresh(); });
document.getElementById("stats").textContent = `${DATA.objects.length} objects · ${DATA.claims.length} claims · ${DATA.claims.reduce((n,c)=>n+c.members.length,0)} memberships · receipt chain head #${DATA.receipts.head_seq}`;
document.getElementById("snap").textContent = `Snapshot of ${DATA.store}, generated ${DATA.generated}. It does not update by itself: rebuild the store, then run glossary_viz.py again.`;
document.getElementById("explain").textContent = "Every claim is a hyperedge: subject → claim → object (dashed 'when' link for a condition). The claim's predicate is the diamond's colour. Contexts and groups anchor the clusters.";

// ---------- interaction ----------
const detail = document.getElementById("detail"), tip = document.getElementById("tip");
const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const dl = rows => "<dl>" + rows.filter(r => r[1] !== null && r[1] !== undefined && r[1] !== "").map(r => `<dt>${esc(r[0])}</dt><dd>${esc(r[1])}</dd>`).join("") + "</dl>";
function showObject(o){
  const claims = DATA.claims.filter(c => c.members.some(m => m.node === o.id));
  detail.innerHTML = `<strong>${esc(o.label)}</strong>` + dl([["Type",o.type],["Scope",o.scope],["Source",o.source],["State",`${o.dsn} · ${o.admission}`],["Meanings",o.meanings],["Narrowing basis",o.basis],["Original text",o.original],["In claims",claims.length]]);
}
function showClaim(c){
  const part = r => c.members.filter(m => m.role === r).map(m => byId[m.node].label).join(", ");
  const ev = c.evidence[0];
  detail.innerHTML = `<strong>${esc(part("SUBJECT"))} — ${esc(c.predicate)} — ${esc(part("OBJECT"))}</strong>` +
    dl([["Relation",c.relation],["Condition",part("CONDITION")],["Scope",c.scope],["State",c.admission],["Confidence bound",c.confidence],["Receipt",c.receipt]]) +
    (ev ? `<h2>Evidence (${esc(ev.tier)}, ${esc(ev.polarity)})</h2><blockquote>${esc(ev.text)}</blockquote><p class="note">${esc(ev.source)} — extracted text says the source states this, not that the statement is correct.</p>` : "");
}
function clearFocus(){ cy.elements().removeClass("dim hit"); }
cy.on("tap", "node", e => {
  const n = e.target; clearFocus();
  const hood = n.closedNeighborhood(":visible");
  cy.elements(":visible").not(hood).addClass("dim");
  n.data("kind") === "claim" ? showClaim(claimById[n.id()]) : showObject(byId[n.id()]);
});
cy.on("tap", e => { if (e.target === cy) { clearFocus(); detail.innerHTML = '<p class="note">Click a node to see what it is, what supports it and its neighbours.</p>'; } });
cy.on("mouseover", "node", e => { const n = e.target; tip.textContent = n.data("kind") === "claim" ? `claim: ${n.data("predicate")}` : `${n.data("type")}: ${n.data("label")}`; tip.style.display = "block"; });
cy.on("mousemove", e => { if (e.originalEvent) { tip.style.left = (e.originalEvent.clientX + 12) + "px"; tip.style.top = (e.originalEvent.clientY + 12) + "px"; } });
cy.on("mouseout", "node", () => { tip.style.display = "none"; });

const q = document.getElementById("q");
q.addEventListener("input", () => {
  clearFocus(); const term = q.value.trim().toLowerCase(); if (!term) return;
  const hits = cy.nodes(":visible").filter(n => n.data("kind")==="object" && n.data("label").toLowerCase().includes(term));
  if (!hits.length) return;
  cy.elements(":visible").not(hits.closedNeighborhood(":visible")).addClass("dim"); hits.addClass("hit"); cy.animate({fit:{eles:hits.closedNeighborhood(":visible"),padding:60},duration:250});
});
q.addEventListener("keydown", e => { if (e.key === "Escape") { q.value = ""; clearFocus(); } });
document.getElementById("relayout").addEventListener("click", layout);
document.getElementById("fit").addEventListener("click", () => cy.fit(cy.elements(":visible"), 30));
new ResizeObserver(() => cy.resize()).observe(document.getElementById("cy"));
window.addEventListener("load", () => { cy.resize(); cy.fit(cy.elements(":visible"), 30); });
matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => cy.style(styleSheet()));
refresh();
window.__ready = true;
</script>
</body>
</html>
"""

if __name__ == "__main__":
    raise SystemExit(main())
