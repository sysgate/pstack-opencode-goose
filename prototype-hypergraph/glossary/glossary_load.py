"""PROTOTYPE, THROWAWAY: load the CHI glossaries into the prototype hypergraph store.

    python3 glossary_load.py --rebuild      # delete and rebuild chi-glossary.PROTOTYPE-rebuildable.sqlite3

Sources (read only): the permission gate glossary (CONTEXT.md), the CCGF glossary (docs/ccgf/CONTEXT.md)
and the cross-context collisions stated in CONTEXT-MAP.md. Nothing is invented: every claim is bound to the
exact source text it came from. The store file is REBUILDABLE from those files; the files stay authoritative.

Modelling (all through the store's own rules, so anything the doctrine forbids fails loudly):
  semantic objects : a Context, a Glossary group, a Term (scoped to its context, so "Scope" in the gate and
                     "Scope" in CCGF are two objects), an Avoided alias, and four Predicates
  hyperedges       : CLAIM(SUBJECT, PREDICATE, OBJECT) for "is defined in", "belongs to group",
                     "is avoided in favour of" and "must not be confused with"
  evidence         : the definition / Avoid line / map line, TIER_3_EXTRACTED (extracted by an adapter, awaiting
                     verification), bound with polarity SUPPORTS
  the claim made   : "the source says this", not "the definition is correct", so its confidence bound is 1.0
"""
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from hypergraph import Store  # noqa: E402

ROOT = "/Users/robertlai/Projects/chi"
GATE, CCGF = "Permission gate", "CCGF hypergraph"
SOURCES = [(GATE, ROOT + "/CONTEXT.md"), (CCGF, ROOT + "/docs/ccgf/CONTEXT.md")]
MAP = ROOT + "/CONTEXT-MAP.md"
DB = os.path.join(HERE, "chi-glossary.PROTOTYPE-rebuildable.sqlite3")
ADAPTER, SYS = "adapter:glossary-md", "sys:adjudicator"
SCOPE = "platform-glossary"
VALID_FROM = int(datetime.datetime(2026, 9, 19, tzinfo=datetime.timezone.utc).timestamp())
NOTE = "the claim is that the source states this, not that the statement is correct"
P_DEF, P_GROUP, P_AVOID, P_COLLIDE = "is defined in", "belongs to group", "is avoided in favour of", "must not be confused with"
# collisions the map states in words; each must be found in the map text or the load fails
COLLISIONS = [(GATE, "Scope", CCGF, "Scope", "*Scope* is a folder tree"),
              (GATE, "Audit log", CCGF, "Receipt", "*audit log* is not a CCGF *receipt*"),
              (GATE, "Reconciliation", CCGF, "Reconciliation", "*Reconciliation* is comparing")]


def parse(path):
    """CONTEXT.md -> [{term, definition, avoid_line, avoid, group}]"""
    lines = open(path, encoding="utf8").read().split("\n")
    entries, group, i = [], None, 0
    while i < len(lines):
        if lines[i].startswith("### "):
            group = lines[i][4:].strip()
        m = re.match(r"^\*\*(.+?)\*\*:\s*$", lines[i])
        if m:
            j, body = i + 1, []
            while j < len(lines) and lines[j].strip():
                body.append(lines[j]); j += 1
            avoid_line = next((b for b in body if b.startswith("_Avoid_:")), None)
            entries.append({"term": m.group(1), "definition": "\n".join(b for b in body if not b.startswith("_Avoid_:")).strip(),
                            "avoid_line": avoid_line, "avoid": split_avoid(avoid_line[len("_Avoid_:"):]) if avoid_line else [], "group": group})
            i = j
            continue
        i += 1
    return entries


def split_avoid(text):
    """'a, b (note, with comma), c' -> [('a', None), ('b', 'note, with comma'), ('c', None)]"""
    items, depth, cur = [], 0, ""
    for ch in text:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            items.append(cur.strip()); cur = ""
        else:
            cur += ch
    if cur.strip():
        items.append(cur.strip())
    out = []
    for it in items:
        m = re.match(r"^(.*?)\s*\((.*)\)\s*$", it)
        out.append((m.group(1).strip(), m.group(2).strip()) if m else (it, None))
    return out


def load(s, parsed, map_text):
    ids = {}   # (kind, scope, label) -> object id

    def obj(kind, scope, label, alternatives, source):
        key = (kind, scope, label)
        if key not in ids:
            o = s.propose_candidate(label, scope, source, ADAPTER)
            # DSN: narrowed on a recorded basis (the glossary itself); alternatives are the other meanings considered
            s.narrow(o, "NARROWED", ADAPTER, {"kind": "source", "detail": f"{kind} '{label}' as written in {source}", "alternatives": alternatives}, semantic_type=kind, label=label)
            s.admit_semantic_object(o, SYS)
            ids[key] = o
        return ids[key]

    def claim(subject, pred, target, evidence_id, text, uri, condition=None):
        members = [(subject, "SUBJECT"), (pred, "PREDICATE"), (target, "OBJECT")] + ([(condition, "CONDITION")] if condition else [])
        he = s.propose_hyperedge("CLAIM", members, SCOPE, VALID_FROM, None, 1.0, ADAPTER, uncertainty_notes=[NOTE])
        ev = s.add_evidence(evidence_id, "Document", "TIER_3_EXTRACTED", text, SYS, provenance_uri=uri)
        s.bind_evidence(he, ev, "SUPPORTS", SYS, proposed_by=ADAPTER)
        r = s.admit_hyperedge(he, SYS)
        assert r["admitted"], (subject, pred, target, r)
        return he

    labels = {ctx: {e["term"] for e in ents} for ctx, ents in parsed.items()}
    other = {GATE: CCGF, CCGF: GATE}
    preds = {p: obj("Predicate", SCOPE, p, [p, "general-language meaning"], "glossary model") for p in (P_DEF, P_GROUP, P_AVOID, P_COLLIDE)}
    n = {"terms": 0, "aliases": 0, "claims": 0}
    for ctx, path in SOURCES:
        c = obj("Context", SCOPE, ctx, [ctx, "another glossary context"], path)
        for e in parsed[ctx]:
            uri = f"file://{path}#{e['term']}"
            alt = [f"'{e['term']}' as defined in {ctx}", (f"'{e['term']}' as defined in {other[ctx]}" if e["term"] in labels[other[ctx]] else "general-language meaning of the word")]
            t = obj("Term", ctx, e["term"], alt, path)
            n["terms"] += 1
            claim(t, preds[P_DEF], c, f"{path}#{e['term']}/definition", e["definition"], uri)
            n["claims"] += 1
            if e["group"]:
                g = obj("Glossary group", ctx, e["group"], [e["group"], "another grouping"], path)
                claim(t, preds[P_GROUP], g, f"{path}#{e['term']}/group", f"### {e['group']}\n**{e['term']}**:", uri)
                n["claims"] += 1
            for alias, note in e["avoid"]:
                a = obj("Avoided alias", ctx, alias, [f"'{alias}' as an acceptable synonym", f"'{alias}' as a distinct concept"], path)
                # the qualifying note, if any, is a CONDITION of the claim: "avoid this word, but only in this sense"
                cond = obj("Avoid note", ctx, note, [note, "no qualification"], path) if note else None
                claim(a, preds[P_AVOID], t, f"{path}#{e['term']}/avoid/{alias}", e["avoid_line"], uri, condition=cond)
                n["aliases"] += 1; n["claims"] += 1; n["notes"] = n.get("notes", 0) + (1 if note else 0)
    for c1, t1, c2, t2, needle in COLLISIONS:
        line = next((ln for ln in map_text.split("\n") if needle in ln), None)
        assert line, f"the map no longer says: {needle!r}"
        claim(ids[("Term", c1, t1)], preds[P_COLLIDE], ids[("Term", c2, t2)], f"{MAP}#{t1}~{t2}", line, f"file://{MAP}")
        n["claims"] += 1
    return ids, n


def main():
    if os.path.exists(DB):
        if "--rebuild" not in sys.argv:
            sys.exit(f"{os.path.basename(DB)} exists. It is rebuildable; run with --rebuild to delete it and load again.")
        os.remove(DB)
    parsed = {ctx: parse(path) for ctx, path in SOURCES}
    map_text = open(MAP, encoding="utf8").read()
    s = Store(DB)
    s.db.execute("PRAGMA synchronous = OFF")   # rebuildable prototype data: speed over durability
    ids, n = load(s, parsed, map_text)
    s.db.commit()
    print(f"loaded into {os.path.basename(DB)}: {n['terms']} terms, {n['aliases']} avoided aliases ({n.get('notes', 0)} with a qualifying note), {n['claims']} claims")
    print("receipt chain verifies:", s.verify_chain())
    print("observations on the source glossaries themselves:")
    both = {t.lower() for t in {e['term'] for e in parsed[GATE]}} & {t.lower() for t in {e['term'] for e in parsed[CCGF]}}
    declared = {t1.lower() for _, t1, _, t2, _ in COLLISIONS if t1.lower() == t2.lower()}
    print(f"  terms defined in BOTH contexts: {sorted(both)}; declared as collisions in the map: {sorted(declared)}; undeclared: {sorted(both - declared)}")
    all_terms = {(ctx, e["term"].lower()) for ctx, ents in parsed.items() for e in ents}
    hits = [(ctx, e["term"], a) for ctx, ents in parsed.items() for e in ents for a, _ in e["avoid"] if (ctx, a.lower()) in all_terms]
    print(f"  Avoid aliases that are also defined terms in the same context: {hits}")
    for phrase in ("Fast path", "System One"):
        if phrase.lower() in map_text.lower():
            where = [ctx for ctx in parsed if any(phrase.lower() in e["term"].lower() for e in parsed[ctx])]
            print(f"  the map mentions '{phrase}': defined as a term in {where if where else 'neither glossary'}")


if __name__ == "__main__":
    main()
