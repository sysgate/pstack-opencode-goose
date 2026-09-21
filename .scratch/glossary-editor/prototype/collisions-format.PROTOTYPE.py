#!/usr/bin/env python3
"""PROTOTYPE, THROWAWAY: wipe me. Which format for the collisions list in CONTEXT-MAP.md?

    python3 collisions-format.PROTOTYPE.py

Nothing here is the loader and nothing reads or writes the real CONTEXT-MAP.md. Each variant is a candidate section of that file, with a
rough parser, run against the SAME six real collisions and the SAME four checks:
  1. does it parse to the six pairs (and can a human read it)?
  2. a pair names a term the glossary does not define: does it fail loudly?
  3. edit the note on ONE pair: how many claims' evidence text changes (each change = a claim to revise and re-verify)?
  4. migration: how many of today's six claims keep byte-identical evidence text (the rest need revising once)?
The evidence text of a claim is what the loader hashes into the candidate id, so it is the line (or block) the pair comes from.
"""
import re
import sys
sys.path.insert(0, "/Users/robertlai/Projects/chi-platform/infra/chi_agent_gateway")
from app.hypergraph import glossary as g   # only for parse(), to know which terms the real glossaries define

ROOT = "/Users/robertlai/Projects/chi/"
GATE, CCGF = "Permission gate", "CCGF hypergraph"
TERMS = {GATE: {e["term"] for e in g.parse(open(ROOT + "CONTEXT.md").read())},
         CCGF: {e["term"] for e in g.parse(open(ROOT + "docs/ccgf/CONTEXT.md").read())}}
MAP_LINES = open(ROOT + "CONTEXT-MAP.md").read().split("\n")
TODAY = {  # what today's six claims use as evidence: the whole prose line
    ("Scope", "Scope"): MAP_LINES[10], ("Audit log", "Receipt"): MAP_LINES[10], ("Reconciliation", "Reconciliation"): MAP_LINES[11],
    ("Fast path", "fast-path / diagnostic"): MAP_LINES[11], ("Generative layer (System 1)", "System One"): MAP_LINES[11],
    ("Adjudication layer (System 2)", "System One"): MAP_LINES[11]}


class Bad(Exception):
    pass


def side(kind, name, where):
    """A side of a pair. kind 'term' must be defined in the glossary named WHERE; kind 'outside' is a phrase used at WHERE."""
    if kind == "term" and name not in TERMS.get(where, ()):
        raise Bad(f"'{name}' is not defined in {where!r}" if where in TERMS else f"unknown glossary {where!r}")
    return (kind, name, where)


# ---------------------------------------------------------------- variant A: one line per pair, with an arrow
A = '''## Collisions

- Scope [Permission gate] ≠ Scope [CCGF hypergraph]: a folder tree in the gate, an operational namespace in CCGF
- Audit log [Permission gate] ≠ Receipt [CCGF hypergraph]: the gate's audit log is not a CCGF receipt
- Reconciliation [Permission gate] ≠ Reconciliation [CCGF hypergraph]: comparing transcripts with the audit log, or resolving conflicts and revisions
- Fast path [Permission gate] ≠ "fast-path / diagnostic" {docs/ARCHITECTURE.md}: a router route for non-governed work that CCGF does not define
- Generative layer (System 1) [CCGF hypergraph] ≠ "System One" {TypeSafe}: an authority split, not TypeSafe's models
- Adjudication layer (System 2) [CCGF hypergraph] ≠ "System One" {TypeSafe}: an authority split, not TypeSafe's models
'''


def parse_A(text):
    out = []
    for line in text.split("\n"):
        if not line.startswith("- "):
            continue
        pair, _, note = line[2:].partition(": ")
        parts = pair.split(" ≠ ")
        if len(parts) != 2:
            raise Bad(f"needs exactly one ≠: {line[:60]}")
        sides = []
        for p in parts:
            m = re.fullmatch(r'"(.+)" \{(.+)\}', p) or None
            if m:
                sides.append(side("outside", m.group(1), m.group(2)))
            else:
                m = re.fullmatch(r"(.+) \[(.+)\]", p)
                if not m:
                    raise Bad(f"cannot read a side: {p!r}")
                sides.append(side("term", m.group(1), m.group(2)))
        out.append((sides[0], sides[1], note, line))
    return out


# ---------------------------------------------------------------- variant B: a table, one row per pair
B = '''## Collisions

| Term | In | Must not be confused with | In | Why |
|---|---|---|---|---|
| Scope | Permission gate | Scope | CCGF hypergraph | a folder tree in the gate, an operational namespace in CCGF |
| Audit log | Permission gate | Receipt | CCGF hypergraph | the gate's audit log is not a CCGF receipt |
| Reconciliation | Permission gate | Reconciliation | CCGF hypergraph | comparing transcripts with the audit log, or resolving conflicts and revisions |
| Fast path | Permission gate | fast-path / diagnostic | outside: docs/ARCHITECTURE.md | a router route for non-governed work that CCGF does not define |
| Generative layer (System 1) | CCGF hypergraph | System One | outside: TypeSafe | an authority split, not TypeSafe's models |
| Adjudication layer (System 2) | CCGF hypergraph | System One | outside: TypeSafe | an authority split, not TypeSafe's models |
'''


def parse_B(text):
    out = []
    for line in text.split("\n"):
        if not line.startswith("|") or line.startswith("| Term") or line.startswith("|---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 5:
            raise Bad(f"a row needs 5 cells, got {len(cells)}: {line[:50]}")
        l = side("term", cells[0], cells[1])
        r = side("outside", cells[2], cells[3][len("outside: "):]) if cells[3].startswith("outside: ") else side("term", cells[2], cells[3])
        out.append((l, r, cells[4], line))
    return out


# ---------------------------------------------------------------- variant C: grouped by word, one bullet per meaning
C = '''## Collisions

### Scope
- Permission gate: a folder tree in which the gate is active
- CCGF hypergraph: the operational namespace within which an object or hyperedge holds

### Reconciliation
- Permission gate: comparing transcripts with the audit log
- CCGF hypergraph: resolving conflicts and revision events

### Audit log ≠ Receipt
- Permission gate / Audit log: the gate's own record of every call
- CCGF hypergraph / Receipt: the sealed, chained record of one decision

### Fast path
- Permission gate: tool calls the gate does not judge
- outside docs/ARCHITECTURE.md / "fast-path / diagnostic": a router route CCGF does not define

### System 1 and System 2
- CCGF hypergraph / Generative layer (System 1): an authority split
- CCGF hypergraph / Adjudication layer (System 2): an authority split
- outside TypeSafe / "System One": TypeSafe's models
'''


def parse_C(text):
    out, blocks, cur = [], [], None
    for line in text.split("\n"):
        if line.startswith("### "):
            cur = [line, []]
            blocks.append(cur)
        elif line.startswith("- ") and cur:
            cur[1].append(line)
    for head, bullets in blocks:
        members = []
        for b in bullets:
            who, _, note = b[2:].partition(": ")
            if who.startswith("outside "):
                where, _, phrase = who[len("outside "):].partition(" / ")
                members.append((side("outside", phrase.strip('"'), where), note, b))
            elif " / " in who:
                ctx, _, name = who.partition(" / ")
                members.append((side("term", name, ctx), note, b))
            else:   # "same word in each context": the word is the heading
                members.append((side("term", head[4:], who), note, b))
        for i in range(len(members)):
            for j in range(i + 1, len(members)):
                if members[i][0][0] == "outside" and members[j][0][0] == "outside":
                    continue
                if head.startswith("### System") and members[j][0][1] != "System One" and members[i][0][1] != "System One":
                    continue   # the two System layers are not a collision with each other
                out.append((members[i][0], members[j][0], members[i][1] + " | " + members[j][1], head + "\n" + "\n".join(b for _, _, b in members)))
    return out


# ---------------------------------------------------------------- variant D: keep the prose, mark the pairs inside it
D = '''- **Same word, different meaning**: *Scope* is a folder tree in the gate and an operational namespace in CCGF. <!-- collides: Scope [Permission gate] = Scope [CCGF hypergraph] -->
  The gate's *audit log* is not a CCGF *receipt*. <!-- collides: Audit log [Permission gate] = Receipt [CCGF hypergraph] -->
'''


def parse_D(text):
    out = []
    for line in text.split("\n"):
        m = re.search(r"^(.*?)<!-- collides: (.+?) = (.+?) -->", line)
        if m:
            sides = []
            for p in (m.group(2), m.group(3)):
                mm = re.fullmatch(r"(.+) \[(.+)\]", p)
                sides.append(side("term", mm.group(1), mm.group(2)))
            out.append((sides[0], sides[1], "", m.group(1).strip()))
    return out


VARIANTS = {"A one line per pair": (A, parse_A), "B a table row per pair": (B, parse_B), "C grouped by word": (C, parse_C)}


def show(label, text, parse):
    print("=" * 100 + f"\nVARIANT {label}\n" + "=" * 100)
    print(text.rstrip() if len(text) < 1800 else text[:1800].rstrip() + "\n...")
    pairs = parse(text)
    print(f"\n-> parsed {len(pairs)} pair(s):")
    for l, r, note, ev in pairs:
        print(f"   {l[1]} [{l[2]}]  ≠  {r[1]} [{'outside: ' if r[0] == 'outside' else ''}{r[2]}]")
    # check 2: an undefined term
    broken = text.replace("Receipt", "Ticket")   # every occurrence, so a heading-only rename cannot hide a real reference
    try:
        parse(broken)
        print("\n[2] rename Receipt to Ticket in the section -> NOT caught")
    except Bad as e:
        print(f"\n[2] a pair naming an undefined term -> fails loudly: {e}")
    # check 3: edit ONE note, count claims whose evidence changes
    edited = text.replace("an authority split", "EDITED NOTE", 1)   # the first System-layer note, present in every variant
    before = {(p[0][1], p[1][1]): p[3] for p in pairs}
    after = {(p[0][1], p[1][1]): p[3] for p in parse(edited)}
    changed = [k for k in before if before[k] != after.get(k)]
    print(f"[3] edit the note on the FIRST System-layer pair -> evidence changes for {len(changed)} claim(s): {['%s ~ %s' % k for k in changed]}")
    # check 4: migration
    same = [k for k in before if TODAY.get(k) == before[k]]
    print(f"[4] migration: {len(same)} of today's 6 claims keep byte-identical evidence text; {6 - len(same)} would need revising once")


for name, (text, parse) in VARIANTS.items():
    show(name, text, parse)

print("=" * 100 + "\nVARIANT D keep the prose, mark the pairs in hidden comments (only two pairs shown)\n" + "=" * 100)
print(D.rstrip()); pd = parse_D(D)
print(f"\n-> parsed {len(pd)} pair(s); evidence = the prose sentence, so migration keeps it byte-identical:")
for l, r, _, ev in pd:
    print(f"   {l[1]} ≠ {r[1]}   evidence: {ev[-70:]!r}")
print("   but: the comment is invisible when the file is rendered, and prose line 12 today backs FOUR pairs in one sentence run.")

print("\n" + "=" * 100 + "\nHYPOTHETICAL: a third meaning of Scope is added (illustrative only; not a real term)\n" + "=" * 100)
print("  pairs needed for 3 meanings = 3 (1-2, 1-3, 2-3).  A and B: write 3 rows.  C: add 1 bullet, the parser expands to 3 pairs,")
print("  but all 3 pairs' evidence is the same block, so editing any one meaning changes the evidence of all 3 claims.")
