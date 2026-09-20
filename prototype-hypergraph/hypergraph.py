"""PROTOTYPE, THROWAWAY: CHI hypergraph authority store.

Question this answers: when the accepted CCGF doctrine (docs/ARCHITECTURE.md, AGENTS.md,
docs/ccgf/CONTEXT.md, ADR 0001 and 0002) is implemented as a SQLite authority store, does it
hold together, or do hard cases expose gaps in it?

Not production code. In-memory SQLite, stdlib only, no abstractions. Where the doctrine is
silent or contradicts itself, the choice made here is tagged  # FINDING Fn  and listed in FINDINGS.md.
"Generation proposes. Governance admits."  Anything here that admits requires a governance actor.
"""
import hashlib
import json
import sqlite3


class Refused(Exception):
    """Fail closed: the request is refused and leaves no change behind."""

    def __init__(self, code, message=""):
        super().__init__(f"{code}: {message}" if message else code)
        self.code, self.message = code, message


ADMISSION_STATES = ("CANDIDATE", "PENDING", "ADMITTED", "DENIED", "CHALLENGED", "UNDER_REVIEW", "REVISED", "REVOKED", "CLOSED")
DSN_STATES = ("NARROWED", "BOUNDED_AMBIGUOUS", "UNRESOLVED", "CONFLICT", "DENIED")
TERMINAL = ("DENIED", "REVOKED", "CLOSED")
LEGAL = {  # ARCHITECTURE.md section 7 as applied
    "CANDIDATE": {"PENDING"},
    "PENDING": {"ADMITTED", "PENDING", "UNDER_REVIEW", "DENIED"},
    "ADMITTED": {"CHALLENGED", "REVOKED"},
    "CHALLENGED": {"UNDER_REVIEW"},
    "UNDER_REVIEW": {"REVISED", "ADMITTED", "PENDING", "DENIED", "REVOKED"},
    "REVISED": {"CLOSED"},
    "DENIED": set(), "REVOKED": set(), "CLOSED": set(),
}
ROLES = ("SUBJECT", "OBJECT", "PREDICATE", "CONDITION", "SCOPE_QUALIFIER", "BENEFICIARY", "ASSUMPTION")
SIGNATURES = {  # ARCHITECTURE.md section 8.5
    "CLAIM": ({"SUBJECT"}, {"PREDICATE", "OBJECT", "CONDITION", "ASSUMPTION", "SCOPE_QUALIFIER"}),
    "OBLIGATION": ({"SUBJECT", "OBJECT", "BENEFICIARY"}, {"CONDITION", "ASSUMPTION", "SCOPE_QUALIFIER"}),
    "RISK_CONTROL": ({"SUBJECT", "OBJECT"}, {"CONDITION", "ASSUMPTION", "SCOPE_QUALIFIER"}),
    "CAUSAL": ({"SUBJECT", "OBJECT"}, {"CONDITION", "ASSUMPTION", "SCOPE_QUALIFIER"}),
}
TIERS = ("TIER_1_CANONICAL", "TIER_2_ADMITTED", "TIER_3_EXTRACTED", "TIER_4_GENERATIVE")
BASIS_KINDS = ("context", "ontology", "evidence", "policy", "source", "user_constraint")  # AGENTS.md narrowing basis
DSN_DECISION = {"NARROWED": "CLEAR",   # decision 1 (F2): a narrowed term is cleared for admission, not admitted
                 "BOUNDED_AMBIGUOUS": "BOUND", "UNRESOLVED": "PEND", "CONFLICT": "PEND", "DENIED": "DENY"}

SCHEMA = """
CREATE TABLE receipts (
  id TEXT PRIMARY KEY, seq INTEGER UNIQUE NOT NULL, receipt_type TEXT NOT NULL CHECK (receipt_type IN ('DSN_COMMIT','SEMANTIC_ADMIT','EVIDENCE_ADMIT','HYPEREDGE_ADMIT','PATH_VALIDATE','UNCERTAINTY_BOUND','AMBIGUITY_ALLOW','REVISION_OPEN','REVISION_CLOSE')), subject_id TEXT NOT NULL,
  decision TEXT NOT NULL CHECK (decision IN ('ADMIT','DENY','REVISE','REVOKE','BOUND','PEND','CLEAR')),
  basis TEXT NOT NULL, actor TEXT NOT NULL, created_at INTEGER NOT NULL, previous_receipt_id TEXT
);
CREATE TRIGGER receipts_append_only_u BEFORE UPDATE ON receipts BEGIN SELECT RAISE(ABORT, 'receipts are append-only'); END;
CREATE TRIGGER receipts_append_only_d BEFORE DELETE ON receipts BEGIN SELECT RAISE(ABORT, 'receipts are append-only'); END;

CREATE TABLE semantic_objects (
  id TEXT PRIMARY KEY, type TEXT, label TEXT, original_text TEXT NOT NULL, scope TEXT NOT NULL, source_context TEXT,
  dsn_state TEXT CHECK (dsn_state IS NULL OR dsn_state IN ('NARROWED','BOUNDED_AMBIGUOUS','UNRESOLVED','CONFLICT','DENIED')),
  admission_state TEXT NOT NULL CHECK (admission_state IN ('CANDIDATE','PENDING','ADMITTED','DENIED','CHALLENGED','UNDER_REVIEW','REVISED','REVOKED','CLOSED')),
  meanings TEXT NOT NULL DEFAULT '[]',          -- FINDING F3: not in the doctrine's SemanticObject schema
  narrowing_basis TEXT,                          -- FINDING F3: likewise
  predecessor_ids TEXT NOT NULL DEFAULT '[]', lineage_hash TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
);
CREATE TRIGGER so_terminal BEFORE UPDATE OF admission_state ON semantic_objects
  WHEN OLD.admission_state IN ('DENIED','REVOKED','CLOSED') BEGIN SELECT RAISE(ABORT, 'terminal state is never resumed'); END;

CREATE TABLE hyperedges (
  id TEXT PRIMARY KEY,
  relation_type TEXT NOT NULL CHECK (relation_type IN ('CLAIM','OBLIGATION','RISK_CONTROL','CAUSAL')),
  scope TEXT NOT NULL,
  admission_state TEXT NOT NULL CHECK (admission_state IN ('CANDIDATE','PENDING','ADMITTED','DENIED','CHALLENGED','UNDER_REVIEW','REVISED','REVOKED','CLOSED')),
  valid_from INTEGER NOT NULL, valid_to INTEGER, confidence_bound REAL CHECK (confidence_bound IS NULL OR (confidence_bound >= 0 AND confidence_bound <= 1)),
  uncertainty_notes TEXT NOT NULL DEFAULT '[]', receipt_id TEXT REFERENCES receipts(id),
  predecessor_ids TEXT NOT NULL DEFAULT '[]', lineage_hash TEXT NOT NULL DEFAULT '',
  created_at INTEGER NOT NULL, updated_at INTEGER NOT NULL
);
CREATE TRIGGER he_terminal BEFORE UPDATE OF admission_state ON hyperedges
  WHEN OLD.admission_state IN ('DENIED','REVOKED','CLOSED') BEGIN SELECT RAISE(ABORT, 'terminal state is never resumed'); END;

CREATE TABLE hyperedge_members (
  hyperedge_id TEXT NOT NULL REFERENCES hyperedges(id), node_id TEXT NOT NULL REFERENCES semantic_objects(id),
  role TEXT NOT NULL CHECK (role IN ('SUBJECT','OBJECT','PREDICATE','CONDITION','SCOPE_QUALIFIER','BENEFICIARY','ASSUMPTION')),
  ordinal INTEGER NOT NULL, PRIMARY KEY (hyperedge_id, ordinal)
);
CREATE TABLE evidence_records (   -- FINDING F8: the doctrine's EvidenceRecord has no admission state or lifecycle
  id TEXT PRIMARY KEY, source_id TEXT NOT NULL, source_type TEXT NOT NULL,
  authority_tier TEXT NOT NULL CHECK (authority_tier IN ('TIER_1_CANONICAL','TIER_2_ADMITTED','TIER_3_EXTRACTED','TIER_4_GENERATIVE')),
  provenance_uri TEXT NOT NULL, extracted_text TEXT NOT NULL, content_hash TEXT NOT NULL,
  receipt_id TEXT NOT NULL REFERENCES receipts(id)
);
CREATE TABLE hyperedge_evidence (
  hyperedge_id TEXT NOT NULL REFERENCES hyperedges(id), evidence_id TEXT NOT NULL REFERENCES evidence_records(id),
  polarity TEXT NOT NULL CHECK (polarity IN ('SUPPORTS','CONTRADICTS')),
  receipt_id TEXT NOT NULL REFERENCES receipts(id), allowance_receipt_id TEXT REFERENCES receipts(id),
  proposed_by TEXT NOT NULL, void_reason TEXT, voided_receipt_id TEXT REFERENCES receipts(id),   -- decision 5 (F9): voided, never deleted
  PRIMARY KEY (hyperedge_id, evidence_id)
);
CREATE TABLE allowances (   -- decision 6 (F11): one allowance per binding, naming COMBINATIONS of meanings
  receipt_id TEXT PRIMARY KEY REFERENCES receipts(id), hyperedge_id TEXT NOT NULL, evidence_id TEXT NOT NULL,
  combinations TEXT NOT NULL, member_hashes TEXT NOT NULL, reason TEXT NOT NULL
);
"""


def h(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def _kind(actor):
    return actor.split(":", 1)[0]


class Store:
    def __init__(self, path=":memory:"):
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        if self._one("SELECT 1 FROM sqlite_master WHERE name='receipts'"):
            # reopening a persisted store: resume the counter clock after the latest recorded time
            self.t = max(self._one("SELECT COALESCE(MAX(created_at), 0) AS m FROM receipts")["m"],
                         self._one("SELECT COALESCE(MAX(updated_at), 0) AS m FROM semantic_objects")["m"],
                         self._one("SELECT COALESCE(MAX(updated_at), 0) AS m FROM hyperedges")["m"], 1_000_000)
        else:
            self.db.executescript(SCHEMA)
            self.t = 1_000_000  # a counter clock keeps ids and receipts reproducible

    # ---------------------------------------------------------------- plumbing
    def _now(self):
        self.t += 1
        return self.t

    def _one(self, sql, *a):
        return self.db.execute(sql, a).fetchone()

    def _all(self, sql, *a):
        return self.db.execute(sql, a).fetchall()

    def _governance(self, actor):
        if _kind(actor) not in ("sys", "human"):
            raise Refused("GENERATION_CANNOT_ADMIT", f"{actor} may propose but only governance may decide")

    def _receipt(self, rtype, subject, decision, basis, actor):
        prev = self._one("SELECT id, seq FROM receipts ORDER BY seq DESC LIMIT 1")
        seq = (prev["seq"] + 1) if prev else 1
        prev_id = prev["id"] if prev else None
        payload = {"type": rtype, "subject": subject, "decision": decision, "basis": basis, "actor": actor,
                   "at": self._now(), "prev": prev_id, "seq": seq}
        rid = h(payload)
        self.db.execute("INSERT INTO receipts VALUES (?,?,?,?,?,?,?,?,?)",
                        (rid, seq, rtype, subject, decision, json.dumps(basis, sort_keys=True, ensure_ascii=False), actor, payload["at"], prev_id))
        return rid

    def _move(self, table, oid, new_state, actor):
        cur = self._one(f"SELECT admission_state FROM {table} WHERE id=?", oid)["admission_state"]
        if new_state not in LEGAL[cur]:
            raise Refused("ILLEGAL_TRANSITION", f"{cur} -> {new_state}")
        self.db.execute(f"UPDATE {table} SET admission_state=?, updated_at=? WHERE id=?", (new_state, self._now(), oid))

    def _lineage_hash(self, pred_ids):
        return h([[p, (self._one("SELECT id FROM receipts WHERE subject_id=? ORDER BY seq DESC LIMIT 1", p) or {"id": None})["id"]]
                  for p in sorted(pred_ids)]) if pred_ids else ""

    def _check_predecessors(self, table, pred_ids):
        for p in pred_ids:
            row = self._one(f"SELECT admission_state FROM {table} WHERE id=?", p)
            if not row:
                raise Refused("UNKNOWN_PREDECESSOR", p)
            if row["admission_state"] not in TERMINAL:
                raise Refused("PREDECESSOR_NOT_TERMINAL", f"{p} is {row['admission_state']}; it must be challenged and reviewed, not replaced")

    def state(self, table, oid):
        return self._one(f"SELECT admission_state FROM {table} WHERE id=?", oid)["admission_state"]

    def trail(self, subject_id):
        return [(r["seq"], r["receipt_type"], r["decision"], json.loads(r["basis"]), r["actor"])
                for r in self._all("SELECT * FROM receipts WHERE subject_id=? ORDER BY seq", subject_id)]

    def verify_chain(self):
        prev = None
        for r in self._all("SELECT * FROM receipts ORDER BY seq"):
            payload = {"type": r["receipt_type"], "subject": r["subject_id"], "decision": r["decision"], "basis": json.loads(r["basis"]),
                       "actor": r["actor"], "at": r["created_at"], "prev": prev, "seq": r["seq"]}
            if r["previous_receipt_id"] != prev or h(payload) != r["id"]:
                return False, r["seq"]
            prev = r["id"]
        return True, None

    def verify_integrity(self):
        """FINDING F17: the receipt chain covers receipts only. This checks that evidence and state are explained by them."""
        problems = []
        for r in self._all("SELECT e.id, e.extracted_text, e.content_hash, r.basis FROM evidence_records e JOIN receipts r ON r.id=e.receipt_id"):
            if hashlib.sha256(r["extracted_text"].encode()).hexdigest() != r["content_hash"]:
                problems.append(("evidence text does not match its content hash", r["id"]))
            if json.loads(r["basis"]).get("content_hash") != r["content_hash"]:
                problems.append(("evidence content hash does not match the hash sealed in its receipt", r["id"]))
        for rtype, table, prefix in (("HYPEREDGE_ADMIT", "hyperedges", None), ("SEMANTIC_ADMIT", "semantic_objects", None), ("EVIDENCE_ADMIT", "evidence_records", "ev_")):
            for r in self._all(f"SELECT DISTINCT subject_id FROM receipts WHERE receipt_type=? AND subject_id NOT IN (SELECT id FROM {table})", rtype):
                if prefix is None or r["subject_id"].startswith(prefix):
                    problems.append((f"{rtype} receipt for a record that no longer exists in {table}", r["subject_id"]))
        for table, states, rtype in (("hyperedges", "'ADMITTED','CHALLENGED','REVISED','CLOSED'", "HYPEREDGE_ADMIT"), ("semantic_objects", "'ADMITTED'", "SEMANTIC_ADMIT")):
            for r in self._all(f"SELECT id FROM {table} WHERE admission_state IN ({states}) AND id NOT IN (SELECT subject_id FROM receipts WHERE receipt_type=?)", rtype):
                problems.append((f"{table} row is in an admitted-or-later state with no {rtype} receipt", r["id"]))
        return problems

    # ---------------------------------------------------------------- semantic objects
    def propose_candidate(self, original_text, scope, context, actor, predecessor_ids=()):
        """A semantic candidate (D3): anyone may propose it, nothing is admitted."""
        with self.db:
            pred = sorted(predecessor_ids)
            self._check_predecessors("semantic_objects", pred)
            # FINDING F5: the doctrine says ids are deterministic but never says from what. Here: from the SOURCE
            # (text, scope, context, predecessors), not from the narrowed result, so narrowing does not change the id.
            oid = "so_" + h({"k": "so", "t": original_text, "s": scope, "c": context, "p": pred})[:10]
            if self._one("SELECT 1 FROM semantic_objects WHERE id=?", oid):
                raise Refused("DUPLICATE_CANDIDATE", f"{oid} exists; to retry a denied one, name it as a predecessor")
            now = self._now()
            self.db.execute("INSERT INTO semantic_objects (id, original_text, scope, source_context, admission_state, predecessor_ids, lineage_hash, created_at, updated_at) "
                            "VALUES (?,?,?,?, 'CANDIDATE', ?,?,?,?)", (oid, original_text, scope, context, json.dumps(pred), self._lineage_hash(pred), now, now))
            self._move("semantic_objects", oid, "PENDING", actor)   # ingestion
            return oid

    def narrow(self, oid, dsn_state, actor, basis, semantic_type=None, label=None, meanings=()):
        """DSN: record a narrowing outcome. It needs a recorded basis (D6); it never admits."""
        with self.db:
            o = self._one("SELECT * FROM semantic_objects WHERE id=?", oid)
            if dsn_state not in DSN_STATES:
                raise Refused("UNKNOWN_DSN_STATE", dsn_state)
            if basis.get("kind") not in BASIS_KINDS:      # D6: a model's most probable reading alone never counts
                raise Refused("NO_RECORDED_BASIS", f"basis kind {basis.get('kind')!r} is not one of {BASIS_KINDS}")
            meanings = list(meanings)
            if dsn_state in ("NARROWED", "BOUNDED_AMBIGUOUS", "CONFLICT") and not basis.get("alternatives"):
                raise Refused("ALTERNATIVES_NOT_RECORDED", "candidate meanings considered must be recorded")
            if dsn_state == "BOUNDED_AMBIGUOUS" and len(meanings) < 2:   # D4: an explicit, finite set of remaining meanings
                raise Refused("BOUNDED_NEEDS_A_FINITE_SET", "bounded ambiguity needs at least two named meanings")
            if dsn_state == "UNRESOLVED" and meanings:
                raise Refused("UNRESOLVED_HAS_NO_SET", "if a finite set of meanings can be named it is bounded ambiguity, not unresolved")
            if dsn_state == "NARROWED":
                if not (semantic_type and label):
                    raise Refused("NARROWED_NEEDS_TYPE_AND_LABEL")
                meanings = [label]
            cur = o["admission_state"]
            renarrow_admitted = cur == "ADMITTED" and o["dsn_state"] == "BOUNDED_AMBIGUOUS" and dsn_state == "NARROWED"
            if cur != "PENDING" and not renarrow_admitted:
                raise Refused("CANNOT_NARROW_IN_STATE", f"{cur}/{o['dsn_state']}")
            self.db.execute("UPDATE semantic_objects SET dsn_state=?, type=COALESCE(?,type), label=COALESCE(?,label), meanings=?, narrowing_basis=?, updated_at=? WHERE id=?",
                            (dsn_state, semantic_type, label, json.dumps(sorted(meanings), ensure_ascii=False), json.dumps(basis, sort_keys=True, ensure_ascii=False), self._now(), oid))
            # B5: every DSN outcome, UNRESOLVED included, leaves a receipt on the same subject.
            # decision 1 (F2): CLEAR, not ADMIT
            rid = self._receipt("DSN_COMMIT", oid, DSN_DECISION[dsn_state], {"dsn_state": dsn_state, "meanings": sorted(meanings), **basis}, actor)
            if not renarrow_admitted:
                if dsn_state == "CONFLICT":
                    self._move("semantic_objects", oid, "UNDER_REVIEW", actor)
                elif dsn_state == "DENIED":
                    self._move("semantic_objects", oid, "DENIED", actor)
                else:
                    self._move("semantic_objects", oid, "PENDING", actor)   # PENDING -> PENDING: reason recorded
            else:
                for (he,) in self._all("SELECT DISTINCT hyperedge_id FROM hyperedge_members WHERE node_id=?", oid):
                    self.revalidate_bindings(he, "sys:adjudicator")   # the loss of an allowance is handled by the system, automatically
            return rid

    def admit_semantic_object(self, oid, actor):
        """Semantic admission (名界) alone admits a semantic object (ADR 0002)."""
        with self.db:
            self._governance(actor)
            o = self._one("SELECT * FROM semantic_objects WHERE id=?", oid)
            if o["admission_state"] != "PENDING":
                raise Refused("NOT_PENDING", o["admission_state"])
            if o["dsn_state"] not in ("NARROWED", "BOUNDED_AMBIGUOUS"):
                raise Refused("DSN_NOT_ADMISSIBLE", f"dsn_state is {o['dsn_state']}")
            self._move("semantic_objects", oid, "ADMITTED", actor)
            # decision 1 (F1): SEMANTIC_ADMIT is a receipt type
            return self._receipt("SEMANTIC_ADMIT", oid, "ADMIT", {"dsn_state": o["dsn_state"]}, actor)

    def revoke_object(self, oid, actor, reason):
        with self.db:
            self._governance(actor)
            self._move("semantic_objects", oid, "REVOKED", actor)
            self._receipt("REVISION_CLOSE", oid, "REVOKE", {"reason": reason}, actor)
            # ARCHITECTURE section 8.3: 修界 cascades invalidations across connected hyperedges.
            for (he,) in self._all("SELECT DISTINCT m.hyperedge_id FROM hyperedge_members m JOIN hyperedges e ON e.id=m.hyperedge_id "
                                   "WHERE m.node_id=? AND e.admission_state='ADMITTED'", oid):
                self._challenge(he, f"member {oid} revoked", actor)

    def reopen_object(self, old_id, actor):
        """L2: a terminal object is never resumed; raise a new candidate that names it."""
        o = self._one("SELECT * FROM semantic_objects WHERE id=?", old_id)
        return self.propose_candidate(o["original_text"], o["scope"], o["source_context"], actor, predecessor_ids=[old_id])

    # ---------------------------------------------------------------- evidence
    def add_evidence(self, source_id, source_type, tier, text, actor, provenance_uri="prototype://none"):
        with self.db:
            self._governance(actor)
            if tier not in TIERS:
                raise Refused("UNKNOWN_TIER", tier)
            ch = hashlib.sha256(text.encode()).hexdigest()
            eid = "ev_" + h({"s": source_id, "c": ch})[:10]
            # D9: tier 4 is tracked but never admitted evidence.
            rid = self._receipt("EVIDENCE_ADMIT", eid, "PEND" if tier == TIERS[3] else "ADMIT", {"tier": tier, "source": source_id, "content_hash": ch}, actor)   # F17: the chain now covers the evidence text
            self.db.execute("INSERT INTO evidence_records VALUES (?,?,?,?,?,?,?,?)", (eid, source_id, source_type, tier, provenance_uri, text, ch, rid))
            return eid

    # ---------------------------------------------------------------- hyperedges
    def propose_hyperedge(self, relation_type, members, scope, valid_from, valid_to, confidence_bound, actor,
                          predecessor_ids=(), uncertainty_notes=()):
        with self.db:
            if relation_type not in SIGNATURES:
                raise Refused("UNKNOWN_RELATION_TYPE", relation_type)
            roles = {r for _, r in members}
            for r in roles:
                if r not in ROLES:
                    raise Refused("UNKNOWN_ROLE", r)
            required, allowed = SIGNATURES[relation_type]
            if not required <= roles:
                raise Refused("SIGNATURE_MISSING_ROLES", f"{relation_type} requires {sorted(required - roles)}")
            if not roles <= (required | allowed):
                raise Refused("SIGNATURE_ROLE_NOT_ALLOWED", f"{relation_type} does not allow {sorted(roles - required - allowed)}")
            for oid, _ in members:
                row = self._one("SELECT admission_state FROM semantic_objects WHERE id=?", oid)
                if not row or row["admission_state"] != "ADMITTED":   # D3: only admitted semantic objects may be members
                    raise Refused("MEMBER_NOT_ADMITTED", f"{oid} is {row['admission_state'] if row else 'unknown'}")
            pred = sorted(predecessor_ids)
            self._check_predecessors("hyperedges", pred)
            eid = "he_" + h({"k": "he", "r": relation_type, "s": scope, "m": sorted(map(list, members)), "f": valid_from, "t": valid_to, "p": pred})[:10]
            if self._one("SELECT 1 FROM hyperedges WHERE id=?", eid):
                raise Refused("DUPLICATE_CANDIDATE", eid)
            now = self._now()
            self.db.execute("INSERT INTO hyperedges (id, relation_type, scope, admission_state, valid_from, valid_to, confidence_bound, uncertainty_notes, predecessor_ids, lineage_hash, created_at, updated_at) "
                            "VALUES (?,?,?, 'CANDIDATE', ?,?,?,?,?,?,?,?)",
                            (eid, relation_type, scope, valid_from, valid_to, confidence_bound, json.dumps(list(uncertainty_notes)), json.dumps(pred), self._lineage_hash(pred), now, now))
            for i, (oid, role) in enumerate(members):
                self.db.execute("INSERT INTO hyperedge_members VALUES (?,?,?,?)", (eid, oid, role, i))
            self._move("hyperedges", eid, "PENDING", actor)
            return eid

    def _members(self, he):
        return self._all("SELECT m.node_id, m.role, o.dsn_state, o.label, o.meanings, o.admission_state FROM hyperedge_members m "
                         "JOIN semantic_objects o ON o.id=m.node_id WHERE m.hyperedge_id=? ORDER BY m.ordinal", he)

    def _allowance_state(self, aid):
        """Decision 6. Returns (status, reason, surviving combinations).
        ACTIVE: at least one covered term is still bounded and at least one granted combination still matches.
        STANDS: every covered term is now narrowed and a granted combination matches: an ordinary binding.
        VOID:   no granted combination remains, a term's meanings changed, or something is terminal."""
        a = self._one("SELECT * FROM allowances WHERE receipt_id=?", aid)
        if not a:
            return "VOID", "NO_SUCH_ALLOWANCE", []
        if self.state("hyperedges", a["hyperedge_id"]) in TERMINAL:
            return "VOID", "HYPEREDGE_TERMINAL", []
        combos, hashes, still_bounded = json.loads(a["combinations"]), json.loads(a["member_hashes"]), 0
        for mid, hsh in hashes.items():
            o = self._one("SELECT dsn_state, meanings, label, admission_state FROM semantic_objects WHERE id=?", mid)
            if o["admission_state"] in TERMINAL:
                return "VOID", "MEMBER_TERMINAL", []
            if o["dsn_state"] == "BOUNDED_AMBIGUOUS":
                if h(json.loads(o["meanings"])) != hsh:
                    return "VOID", "MEANINGS_CHANGED", []
                still_bounded += 1
            elif o["dsn_state"] == "NARROWED":
                combos = [c for c in combos if c[mid] == o["label"]]   # combinations that no longer match are dropped
            else:
                return "VOID", f"MEMBER_{o['dsn_state']}", []
        if not combos:
            return "VOID", "NO_GRANTED_COMBINATION_REMAINS", []
        # FINDING F8: "lapses when the evidence is revised or revoked" cannot be evaluated; evidence has no lifecycle.
        return ("ACTIVE" if still_bounded else "STANDS"), "OK", combos

    def grant_allowance(self, he, ev, combinations, reason, actor, proposed_by):
        """Ambiguity allowance: a human, not the proposer, for one binding, naming the COMBINATIONS of meanings it holds under.
        Each combination assigns one remaining meaning to every bounded member, e.g. {the_fund: 'Alpha', the_trust: 'North'}."""
        with self.db:
            if _kind(actor) != "human":
                raise Refused("ALLOWANCE_NEEDS_A_HUMAN", actor)
            if actor == proposed_by:
                raise Refused("ALLOWANCE_SELF_GRANT", "the actor that proposed the binding cannot grant its allowance")
            if not reason.strip():
                raise Refused("ALLOWANCE_NEEDS_A_REASON")
            bounded = {m["node_id"]: m for m in self._members(he) if m["dsn_state"] == "BOUNDED_AMBIGUOUS"}
            if not bounded:
                raise Refused("NO_BOUNDED_MEMBER", he)
            combos, seen = [dict(c) for c in combinations], set()
            if not combos:
                raise Refused("ALLOWANCE_MUST_NAME_COMBINATIONS", "no combination named")
            for c in combos:
                if set(c) != set(bounded):
                    raise Refused("ALLOWANCE_MUST_NAME_COMBINATIONS", f"each combination must assign a meaning to every bounded member {sorted(bounded)}")
                for mid, meaning in c.items():
                    if meaning not in json.loads(bounded[mid]["meanings"]):
                        raise Refused("ALLOWANCE_MUST_NAME_COMBINATIONS", f"{meaning!r} is not a remaining meaning of {mid}")
                key = json.dumps(c, sort_keys=True)
                if key in seen:
                    raise Refused("ALLOWANCE_MUST_NAME_COMBINATIONS", "duplicate combination")
                seen.add(key)
            if not self._one("SELECT 1 FROM evidence_records WHERE id=?", ev):
                raise Refused("UNKNOWN_EVIDENCE", ev)
            combos = sorted(combos, key=lambda c: json.dumps(c, sort_keys=True, ensure_ascii=False))
            rid = self._receipt("AMBIGUITY_ALLOW", he, "BOUND", {"evidence": ev, "combinations": combos, "reason": reason}, actor)
            self.db.execute("INSERT INTO allowances VALUES (?,?,?,?,?,?)",
                            (rid, he, ev, json.dumps(combos, ensure_ascii=False), json.dumps({mid: h(json.loads(m["meanings"])) for mid, m in bounded.items()}), reason))
            return rid

    def bind_evidence(self, he, ev, polarity, actor, allowance=None, proposed_by=None):
        with self.db:
            state = self.state("hyperedges", he)
            if state not in ("PENDING", "ADMITTED"):
                raise Refused("CANNOT_BIND_IN_STATE", state)
            e = self._one("SELECT authority_tier FROM evidence_records WHERE id=?", ev)
            if not e:
                raise Refused("UNKNOWN_EVIDENCE", ev)
            bounded = [m for m in self._members(he) if m["dsn_state"] == "BOUNDED_AMBIGUOUS"]
            if bounded:   # D5 and decision 6: only under an ambiguity allowance for THIS binding, covering every bounded member
                if not allowance:
                    raise Refused("AMBIGUITY_ALLOWANCE_REQUIRED", "bounded ambiguous: " + ", ".join(f"{m['node_id']} ({m['label'] or 'unnarrowed'})" for m in bounded))
                a = self._one("SELECT * FROM allowances WHERE receipt_id=?", allowance)
                if not a or (a["hyperedge_id"], a["evidence_id"]) != (he, ev):
                    raise Refused("ALLOWANCE_COVERS_ONE_BINDING", "this allowance was granted for a different binding")
                if not {m["node_id"] for m in bounded} <= set(json.loads(a["member_hashes"])):
                    raise Refused("ALLOWANCE_DOES_NOT_COVER_MEMBERS", "a bounded member is not covered by this allowance")
                status, why, _ = self._allowance_state(allowance)
                if status != "ACTIVE":
                    raise Refused("ALLOWANCE_LAPSED", why)
            rid = self._receipt("EVIDENCE_ADMIT", he, "ADMIT", {"evidence": ev, "polarity": polarity, "tier": e["authority_tier"], "allowance": allowance}, actor)
            self.db.execute("INSERT INTO hyperedge_evidence VALUES (?,?,?,?,?,?,NULL,NULL)", (he, ev, polarity, rid, allowance if bounded else None, proposed_by or actor))
            if polarity == "CONTRADICTS" and state == "ADMITTED":
                self._challenge(he, f"contradicting evidence {ev}", actor)
            return rid

    def _void(self, he, ev, reason, actor):
        rid = self._receipt("REVISION_CLOSE", he, "REVISE", {"binding_voided": ev, "reason": reason}, actor)
        self.db.execute("UPDATE hyperedge_evidence SET void_reason=?, voided_receipt_id=? WHERE hyperedge_id=? AND evidence_id=?", (reason, rid, he, ev))
        return rid

    def void_binding(self, he, ev, reason, actor):
        """Decision 5: a binding is never deleted, only voided with a reason and a REVISION_CLOSE receipt.
        Dismissing a CONTRADICTS binding, which is what unblocks a reaffirmation, needs a human authority."""
        with self.db:
            self._governance(actor)
            b = self._one("SELECT polarity, void_reason FROM hyperedge_evidence WHERE hyperedge_id=? AND evidence_id=?", he, ev)
            if not b:
                raise Refused("NO_SUCH_BINDING", f"{he} / {ev}")
            if b["void_reason"]:
                raise Refused("ALREADY_VOIDED", b["void_reason"])
            if b["polarity"] == "CONTRADICTS" and _kind(actor) != "human":
                raise Refused("DISMISSING_A_CONTRADICTION_NEEDS_A_HUMAN", actor)
            return self._void(he, ev, reason, actor)

    def _support(self, he):
        rows = self._all("SELECT b.polarity, e.authority_tier FROM hyperedge_evidence b JOIN evidence_records e ON e.id=b.evidence_id "
                         "WHERE b.hyperedge_id=? AND b.void_reason IS NULL", he)
        sup = [r for r in rows if r["polarity"] == "SUPPORTS"]
        return {"sufficient": [r for r in sup if r["authority_tier"] != TIERS[3]], "supports": sup,
                "contradicts": [r for r in rows if r["polarity"] == "CONTRADICTS"]}

    def revalidate_bindings(self, he, actor):
        """A covered term was narrowed: re-evaluate each allowance-bound binding (decision 6), voiding automatically (decision 5)."""
        out = []
        for b in self._all("SELECT * FROM hyperedge_evidence WHERE hyperedge_id=? AND allowance_receipt_id IS NOT NULL AND void_reason IS NULL", he):
            status, why, surviving = self._allowance_state(b["allowance_receipt_id"])
            if status == "ACTIVE":
                continue
            if status == "STANDS":
                self._receipt("EVIDENCE_ADMIT", he, "ADMIT", {"evidence": b["evidence_id"], "revalidated": "stands as an ordinary binding", "surviving_combinations": surviving}, actor)
                out.append((b["evidence_id"], "stands"))
            else:
                self._void(he, b["evidence_id"], f"allowance lapsed: {why}", actor)
                out.append((b["evidence_id"], "voided"))
        if any(r == "voided" for _, r in out) and not self._support(he)["sufficient"]:
            state = self.state("hyperedges", he)
            if state == "PENDING":
                self._receipt("EVIDENCE_ADMIT", he, "PEND", {"reason": "UNSUPPORTED"}, actor)
            elif state == "ADMITTED":
                # decision 4 (F6): an ADMITTED hyperedge that loses support is CHALLENGED; ADMITTED -> PENDING is not a legal edge.
                self._challenge(he, "support lost: UNSUPPORTED", actor)
        return out

    def set_uncertainty(self, he, confidence_bound, notes, actor):
        """幅界 input: bind the uncertainty envelope of a hyperedge that has none yet."""
        with self.db:
            self._governance(actor)
            if self.state("hyperedges", he) != "PENDING":
                raise Refused("CANNOT_SET_UNCERTAINTY_IN_STATE", self.state("hyperedges", he))
            self.db.execute("UPDATE hyperedges SET confidence_bound=?, uncertainty_notes=?, updated_at=? WHERE id=?", (confidence_bound, json.dumps(list(notes)), self._now(), he))
            return self._receipt("UNCERTAINTY_BOUND", he, "BOUND", {"confidence_bound": confidence_bound, "notes": list(notes)}, actor)

    # ---------------------------------------------------------------- the four boundaries
    def _causal_cycle(self, he):
        def ends(e):
            m = {r["role"]: r["node_id"] for r in self._members(e) if r["role"] in ("SUBJECT", "OBJECT")}
            return m["SUBJECT"], m["OBJECT"]
        edges = [ends(r["id"]) for r in self._all("SELECT id FROM hyperedges WHERE relation_type='CAUSAL' AND admission_state='ADMITTED' AND id<>?", he)]
        edges.append(ends(he))
        adj = {}
        for a, b in edges:
            adj.setdefault(a, []).append(b)
        seen, stack = set(), set()

        def dfs(n):
            if n in stack:
                return True
            if n in seen:
                return False
            seen.add(n); stack.add(n)
            if any(dfs(x) for x in adj.get(n, [])):
                return True
            stack.discard(n)
            return False
        return any(dfs(n) for n in list(adj))

    def boundaries(self, he):
        """名 -> 據 -> 徑 -> 幅, stop at the first failure. Returns None or (boundary, reason)."""
        mem = self._members(he)
        for m in mem:
            if m["admission_state"] != "ADMITTED":
                return ("名界", "MEMBER_NOT_ADMITTED")
        s = self._support(he)
        if not s["supports"] and not s["contradicts"]:
            return ("據界", "UNSUPPORTED")
        if not s["sufficient"] or s["contradicts"]:
            return ("據界", "UNTRUSTED")
        r = self._one("SELECT relation_type, confidence_bound FROM hyperedges WHERE id=?", he)
        if r["relation_type"] == "CAUSAL" and self._causal_cycle(he):
            return ("徑界", "PATH_BREAK")
        if r["confidence_bound"] is None:
            return ("幅界", "NEEDS_REVISION")
        return None

    def admit_hyperedge(self, he, actor):
        with self.db:
            self._governance(actor)
            if self.state("hyperedges", he) != "PENDING":
                raise Refused("NOT_PENDING", self.state("hyperedges", he))
            fail = self.boundaries(he)
            if fail:
                boundary, reason = fail
                rtype = {"名界": "SEMANTIC_ADMIT", "據界": "EVIDENCE_ADMIT", "徑界": "PATH_VALIDATE", "幅界": "UNCERTAINTY_BOUND"}[boundary]  # decision 1 (F1): UNCERTAINTY_BOUND
                self._receipt(rtype, he, "PEND", {"boundary": boundary, "reason": reason}, actor)
                self._move("hyperedges", he, "UNDER_REVIEW" if boundary == "幅界" else "PENDING", actor)
                return {"admitted": False, "boundary": boundary, "reason": reason, "state": self.state("hyperedges", he)}
            notes = json.loads(self._one("SELECT uncertainty_notes FROM hyperedges WHERE id=?", he)["uncertainty_notes"])
            for b in self._all("SELECT * FROM hyperedge_evidence WHERE hyperedge_id=? AND allowance_receipt_id IS NOT NULL AND void_reason IS NULL", he):
                notes.append(f"bounded ambiguity: evidence {b['evidence_id']} holds only under {self._allowance_state(b['allowance_receipt_id'])[2]}")   # the envelope carries the ambiguity
            rid = self._receipt("HYPEREDGE_ADMIT", he, "ADMIT", {"boundaries": ["名界", "據界", "徑界", "幅界"]}, actor)
            self.db.execute("UPDATE hyperedges SET uncertainty_notes=?, receipt_id=? WHERE id=?", (json.dumps(notes, ensure_ascii=False), rid, he))
            self._move("hyperedges", he, "ADMITTED", actor)
            return {"admitted": True, "state": "ADMITTED", "receipt": rid}

    # ---------------------------------------------------------------- revision
    def _challenge(self, he, reason, actor):
        self._governance(actor)
        self._move("hyperedges", he, "CHALLENGED", actor)
        return self._receipt("REVISION_OPEN", he, "PEND", {"reason": reason}, actor)   # decision 1 (F1): REVISION_OPEN

    def challenge(self, he, reason, actor):
        with self.db:
            return self._challenge(he, reason, actor)

    def begin_review(self, he, actor):
        with self.db:
            self._governance(actor)
            self._move("hyperedges", he, "UNDER_REVIEW", actor)
            return self._receipt("REVISION_OPEN", he, "PEND", {"review": "begun"}, actor)

    def was_admitted(self, he):
        # FINDING F4: UNDER_REVIEW has two entry points; the state alone cannot say which, so it is read from the receipts.
        return bool(self._one("SELECT 1 FROM receipts WHERE subject_id=? AND receipt_type='HYPEREDGE_ADMIT'", he))

    def resolve_review(self, he, outcome, actor, note=""):
        with self.db:
            self._governance(actor)
            was = self.was_admitted(he)
            legal = {"reaffirm": was, "revise": was, "revoke": True, "rerun": not was, "reject": not was}
            if outcome not in legal or not legal[outcome]:
                raise Refused("OUTCOME_NOT_LEGAL_FOR_HISTORY", f"{outcome} (was admitted: {was})")
            if outcome == "reaffirm":
                fail = self.boundaries(he)
                if fail:   # a dismissed challenge must still satisfy the boundaries
                    raise Refused("CANNOT_REAFFIRM", f"{fail[0]} {fail[1]}: resolve it (for example void the contradicting binding) or revise")
            target = {"reaffirm": "ADMITTED", "revise": "REVISED", "revoke": "REVOKED", "rerun": "PENDING", "reject": "DENIED"}[outcome]
            decision = {"reaffirm": "ADMIT", "revise": "REVISE", "revoke": "REVOKE", "rerun": "PEND", "reject": "DENY"}[outcome]
            self._move("hyperedges", he, target, actor)
            return self._receipt("REVISION_CLOSE", he, decision, {"outcome": outcome, "note": note, "was_admitted": was}, actor)

    def close(self, he, actor):
        with self.db:
            self._governance(actor)
            self._move("hyperedges", he, "CLOSED", actor)
            return self._receipt("REVISION_CLOSE", he, "REVISE", {"closed": True}, actor)

    def reopen_hyperedge(self, old_id, actor):
        """L2: a terminal hyperedge is never resumed; raise a new candidate that names it."""
        o = self._one("SELECT * FROM hyperedges WHERE id=?", old_id)
        members = [(m["node_id"], m["role"]) for m in self._members(old_id)]
        # FINDING F7: evidence bindings are NOT carried over; the doctrine does not say whether they should be.
        return self.propose_hyperedge(o["relation_type"], members, o["scope"], o["valid_from"], o["valid_to"], o["confidence_bound"], actor,
                                      predecessor_ids=[old_id], uncertainty_notes=json.loads(o["uncertainty_notes"]))

    # ---------------------------------------------------------------- projection (D8: a derived, revocable view)
    def projection(self):
        # FINDING F10: AGENTS.md projection labels have no entry for UNDER_REVIEW, DENIED or CANDIDATE.
        label = {"ADMITTED": "Admitted", "PENDING": "Pending Evidence", "CHALLENGED": "Challenged", "UNDER_REVIEW": "Challenged",
                 "REVISED": "Revised", "REVOKED": "Revoked", "CLOSED": "Closed", "DENIED": "Not Projectable", "CANDIDATE": "Not Projectable"}
        out = []
        for e in self._all("SELECT id, relation_type, admission_state FROM hyperedges ORDER BY created_at"):
            lab = label[e["admission_state"]]
            if e["admission_state"] == "ADMITTED":
                for b in self._all("SELECT allowance_receipt_id FROM hyperedge_evidence WHERE hyperedge_id=? AND allowance_receipt_id IS NOT NULL AND void_reason IS NULL", e["id"]):
                    if self._allowance_state(b["allowance_receipt_id"])[0] == "ACTIVE":
                        lab = "Bounded Ambiguous"
            out.append({"id": e["id"], "type": e["relation_type"], "state": e["admission_state"], "label": lab, "assertable": e["admission_state"] == "ADMITTED"})
        return out

    def objects(self):
        return [dict(r) for r in self._all("SELECT id, label, dsn_state, admission_state, meanings FROM semantic_objects ORDER BY created_at")]
