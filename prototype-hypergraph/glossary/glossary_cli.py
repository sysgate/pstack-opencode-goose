"""PROTOTYPE, THROWAWAY: query the CHI glossary held in the prototype hypergraph store.

    python3 glossary_cli.py stats
    python3 glossary_cli.py term "Scope"          # every context's definition, group, avoided aliases, collisions
    python3 glossary_cli.py avoid "node"          # what to say instead
    python3 glossary_cli.py collisions            # same word, different meaning, with both definitions
    python3 glossary_cli.py groups
    python3 glossary_cli.py verify                # reopen the file fresh; check it against the source glossaries
"""
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE)); sys.path.insert(0, HERE)
from glossary_load import DB, GATE, CCGF, MAP, P_AVOID, P_COLLIDE, P_DEF, P_GROUP, SOURCES, parse  # noqa: E402
from hypergraph import Store  # noqa: E402


def load_all(s):
    O = {r["id"]: dict(r) for r in s._all("SELECT * FROM semantic_objects")}
    claims = []
    for he in s._all("SELECT id, admission_state FROM hyperedges ORDER BY created_at"):
        m = {r["role"]: r["node_id"] for r in s._members(he["id"])}
        ev = s._all("SELECT e.extracted_text, e.provenance_uri, e.authority_tier FROM hyperedge_evidence b JOIN evidence_records e ON e.id=b.evidence_id WHERE b.hyperedge_id=? AND b.polarity='SUPPORTS'", he["id"])
        claims.append({"id": he["id"], "state": he["admission_state"], "pred": O[m["PREDICATE"]]["label"], "subject": m["SUBJECT"], "object": m["OBJECT"],
                       "note": O[m["CONDITION"]]["label"] if "CONDITION" in m else None, "evidence": [dict(e) for e in ev]})
    return O, claims


def find_terms(O, name):
    terms = [o for o in O.values() if o["type"] == "Term"]
    exact = [o for o in terms if o["label"].lower() == name.lower()]
    return exact or [o for o in terms if name.lower() in o["label"].lower()]


def definition(O, claims, term_id):
    return next(c["evidence"][0]["extracted_text"] for c in claims if c["pred"] == P_DEF and c["subject"] == term_id)


def cmd_term(s, name):
    O, claims = load_all(s)
    hits = find_terms(O, name)
    if not hits:
        print(f"no term matching {name!r}"); return
    for t in hits:
        grp = next((O[c["object"]]["label"] for c in claims if c["pred"] == P_GROUP and c["subject"] == t["id"]), None)
        print(f"\n{t['label']}   [{t['scope']}]" + (f"   group: {grp}" if grp else ""))
        print("  " + definition(O, claims, t["id"]).replace("\n", "\n  "))
        av = [O[c["subject"]]["label"] + (f" ({c['note']})" if c["note"] else "") for c in claims if c["pred"] == P_AVOID and c["object"] == t["id"]]
        if av:
            print("  avoid:", ", ".join(av))
        for c in claims:
            if c["pred"] == P_COLLIDE and t["id"] in (c["subject"], c["object"]):
                o = O[c["object"] if c["subject"] == t["id"] else c["subject"]]
                print(f"  must not be confused with: '{o['label']}' in {o['scope']}: {definition(O, claims, o['id'])}")
        print(f"  receipts on this term: {len(s.trail(t['id']))}, on its definition claim: {len(s.trail(next(c['id'] for c in claims if c['pred'] == P_DEF and c['subject'] == t['id'])))}")


def cmd_avoid(s, alias):
    O, claims = load_all(s)
    hits = [a for a in O.values() if a["type"] == "Avoided alias" and a["label"].lower() == alias.lower()]
    if not hits:
        print(f"{alias!r} is not an avoided alias in either glossary"); return
    for a in hits:
        for c in claims:
            if c["pred"] == P_AVOID and c["subject"] == a["id"]:
                t = O[c["object"]]
                print(f"In {a['scope']}, do not say '{a['label']}'" + (f" ({c['note']})" if c["note"] else "") + f": use '{t['label']}'")


def cmd_collisions(s):
    O, claims = load_all(s)
    for c in claims:
        if c["pred"] == P_COLLIDE:
            a, b = O[c["subject"]], O[c["object"]]
            print(f"\n'{a['label']}' ({a['scope']})  vs  '{b['label']}' ({b['scope']})")
            print(f"  {a['scope']}: {definition(O, claims, a['id'])}")
            print(f"  {b['scope']}: {definition(O, claims, b['id'])}")
            print(f"  stated in the map: {c['evidence'][0]['extracted_text']}")


def cmd_groups(s):
    O, claims = load_all(s)
    g = collections.defaultdict(list)
    for c in claims:
        if c["pred"] == P_GROUP:
            g[(O[c["object"]]["scope"], O[c["object"]]["label"])].append(O[c["subject"]]["label"])
    for (ctx, name), ts in g.items():
        print(f"\n{ctx} / {name} ({len(ts)}): " + ", ".join(ts))


def cmd_stats(s):
    O, claims = load_all(s)
    print("semantic objects:", dict(collections.Counter((o["type"], o["admission_state"]) for o in O.values())))
    print("claims by predicate:", dict(collections.Counter((c["pred"], c["state"]) for c in claims)))
    print("evidence tiers:", dict(collections.Counter(r["authority_tier"] for r in s._all("SELECT authority_tier FROM evidence_records"))))
    print("receipts:", s._one("SELECT COUNT(*) AS n FROM receipts")["n"], "| chain:", s.verify_chain())


def cmd_verify(s):
    """Round trip: what the store returns must equal what the source files say."""
    O, claims = load_all(s)
    bad, n = [], collections.Counter()
    for ctx, path in SOURCES:
        for e in parse(path):
            t = next((o for o in O.values() if o["type"] == "Term" and o["scope"] == ctx and o["label"] == e["term"]), None)
            if not t:
                bad.append(f"missing term {ctx}/{e['term']}"); continue
            n["terms"] += 1
            if definition(O, claims, t["id"]) != e["definition"]:
                bad.append(f"definition differs: {ctx}/{e['term']}")
            grp = next((O[c["object"]]["label"] for c in claims if c["pred"] == P_GROUP and c["subject"] == t["id"]), None)
            if grp != e["group"]:
                bad.append(f"group differs: {ctx}/{e['term']}: {grp!r} vs {e['group']!r}")
            stored = sorted(O[c["subject"]]["label"] for c in claims if c["pred"] == P_AVOID and c["object"] == t["id"])
            if stored != sorted(a for a, _ in e["avoid"]):
                bad.append(f"avoid list differs: {ctx}/{e['term']}")
            notes = sorted((O[c["subject"]]["label"], c["note"]) for c in claims if c["pred"] == P_AVOID and c["object"] == t["id"] and c["note"])
            if notes != sorted((a, nt) for a, nt in e["avoid"] if nt):
                bad.append(f"avoid notes differ: {ctx}/{e['term']}")
            n["aliases"] += len(stored)
    map_lines = set(open(MAP, encoding="utf8").read().split("\n"))   # collision claims must still be stated by the map
    for c in claims:
        if c["pred"] == P_COLLIDE and c["evidence"][0]["extracted_text"] not in map_lines:
            bad.append(f"collision evidence is no longer a line of CONTEXT-MAP.md: {O[c['subject']]['label']} / {O[c['object']]['label']}")
        if c["pred"] == P_COLLIDE:
            n["collisions"] += 1
    not_admitted = [o["id"] for o in O.values() if o["admission_state"] != "ADMITTED"] + [c["id"] for c in claims if c["state"] != "ADMITTED"]
    ok, at = s.verify_chain()
    forged = s.verify_integrity()   # store-level checks that do not need the source files
    print(f"round trip: {n['terms']} terms, {n['aliases']} avoided aliases and {n['collisions']} collisions compared with the source files, {len(bad)} differences")
    for b in bad[:10]:
        print("  ", b)
    for f in forged[:5]:
        print("   integrity:", f)
    print(f"everything ADMITTED: {not not_admitted} | receipt chain verifies: {ok} | store integrity (evidence and state vs receipts) clean: {not forged} | claims: {len(claims)}")
    sys.exit(0 if not bad and not not_admitted and ok and not forged else 1)


if __name__ == "__main__":
    if not os.path.exists(DB):
        sys.exit("no store yet: run  python3 glossary_load.py --rebuild")
    st = Store(DB)
    cmd, args = (sys.argv[1] if len(sys.argv) > 1 else "stats"), sys.argv[2:]
    {"stats": lambda: cmd_stats(st), "term": lambda: cmd_term(st, " ".join(args)), "avoid": lambda: cmd_avoid(st, " ".join(args)),
     "collisions": lambda: cmd_collisions(st), "groups": lambda: cmd_groups(st), "verify": lambda: cmd_verify(st)}[cmd]()
