"""PROTOTYPE, THROWAWAY: replay the CCGF doctrine's hard cases against hypergraph.py.

    python3 scenarios.py            # run every scenario
    python3 scenarios.py fund       # run one (see SCENARIOS at the bottom)

Each step prints what happened and the state that resulted. A line starting with [ok] met its
expectation; [FAIL] means either the prototype has a bug or the doctrine has a gap (both are findings).
"""
import json
import sys

from hypergraph import Refused, Store

GEN, SYS, ME, OTHER = "gen:model-x", "sys:adjudicator", "human:robert", "human:reviewer"
RESULTS = []


def check(cond, msg):
    RESULTS.append(bool(cond))
    print(f"    [{'ok' if cond else 'FAIL'}] {msg}")


def refused(code, fn, *a, **k):
    try:
        fn(*a, **k)
    except Refused as e:
        check(e.code == code, f"refused with {e.code}" + ("" if e.code == code else f" (expected {code})"))
        return
    check(False, f"expected refusal {code}, but it was accepted")


def title(t):
    print(f"\n=== {t}")


def snapshot(s, hes=()):
    for o in s.objects():
        print(f"      object {o['id']:<14} {str(o['label'] or '-'):<22} dsn={str(o['dsn_state']):<18} state={o['admission_state']}")
    for he in hes:
        print(f"      hyperedge {he} state={s.state('hyperedges', he)}")


def obj(s, text, label, typ, scope="demo"):
    """Propose (generation), narrow with a recorded basis (DSN), admit (governance)."""
    o = s.propose_candidate(text, scope, "prototype", GEN)
    s.narrow(o, "NARROWED", GEN, {"kind": "context", "detail": f"{text} means {label}", "alternatives": [label, "other reading"]}, semantic_type=typ, label=label)
    s.admit_semantic_object(o, SYS)
    return o


def bounded(s, text, meanings, typ="Fund"):
    o = s.propose_candidate(text, "demo", "prototype", GEN)
    s.narrow(o, "BOUNDED_AMBIGUOUS", GEN, {"kind": "context", "detail": "two funds fit the text", "alternatives": list(meanings)}, meanings=meanings)
    s.admit_semantic_object(o, SYS)
    return o


def obligation(s, subject, beneficiary, thing, scope="demo", conf=0.8):
    return s.propose_hyperedge("OBLIGATION", [(subject, "SUBJECT"), (beneficiary, "BENEFICIARY"), (thing, "OBJECT")], scope, 1, None, conf, GEN)


def fund_world(s):
    party, pay = obj(s, "Party A", "Party A", "Party"), obj(s, "the payment", "Payment", "Asset")
    fund = bounded(s, "the Fund", ["Alpha Fund", "Beta Fund"])
    he = obligation(s, party, fund, pay)
    ev = s.add_evidence("bank-statement-1", "Document", "TIER_1_CANONICAL", "Payment received by Alpha Fund", SYS)
    return party, pay, fund, he, ev


# ------------------------------------------------------------------------------------------------
def happy():
    title("1. Happy path: an obligation admitted through all four boundaries (the white paper's example)")
    s = Store()
    a, b = obj(s, "Party A", "Party A", "Party"), obj(s, "Party B", "Party B", "Party")
    clause, pool = obj(s, "Clause 4.2", "Clause 4.2", "Clause"), obj(s, "Asset Pool", "Asset Pool", "Asset")
    he = s.propose_hyperedge("OBLIGATION", [(a, "SUBJECT"), (b, "BENEFICIARY"), (pool, "OBJECT"), (clause, "CONDITION")], "Financial/Q3", 1, 100, 0.9, GEN)
    check(s.state("hyperedges", he) == "PENDING", "a generated proposal is only PENDING (a hyperedge candidate)")
    refused("GENERATION_CANNOT_ADMIT", s.admit_hyperedge, he, GEN)
    r = s.admit_hyperedge(he, SYS)
    check(not r["admitted"] and r["reason"] == "UNSUPPORTED", "no evidence bound: 據界 stops it, reason UNSUPPORTED, state stays PENDING")
    ev = s.add_evidence("contract-2026", "Document", "TIER_1_CANONICAL", "Party A owes Party B under Clause 4.2", SYS)
    s.bind_evidence(he, ev, "SUPPORTS", SYS)
    r = s.admit_hyperedge(he, SYS)
    check(r["admitted"], "with tier-1 supporting evidence bound, all four boundaries pass: ADMITTED")
    check(s.projection()[0]["label"] == "Admitted" and s.projection()[0]["assertable"], "projection shows Admitted, assertable")
    ok, at = s.verify_chain()
    check(ok, f"receipt chain verifies ({len(s.trail(he))} receipts on this hyperedge)")
    print("      trail:", [(t[1], t[2]) for t in s.trail(he)])
    print("    -- signature and closed-vocabulary refusals")
    refused("SIGNATURE_MISSING_ROLES", s.propose_hyperedge, "OBLIGATION", [(a, "SUBJECT"), (pool, "OBJECT")], "x", 1, None, 0.5, GEN)
    refused("UNKNOWN_ROLE", s.propose_hyperedge, "CLAIM", [(a, "DEBTOR")], "x", 1, None, 0.5, GEN)
    refused("UNKNOWN_RELATION_TYPE", s.propose_hyperedge, "CONTRACTUAL_OBLIGATION", [(a, "SUBJECT")], "x", 1, None, 0.5, GEN)
    refused("SIGNATURE_ROLE_NOT_ALLOWED", s.propose_hyperedge, "CLAIM", [(a, "SUBJECT"), (b, "BENEFICIARY")], "x", 1, None, 0.5, GEN)
    cand = s.propose_candidate("Party C", "demo", "prototype", GEN)
    refused("MEMBER_NOT_ADMITTED", s.propose_hyperedge, "CLAIM", [(cand, "SUBJECT")], "x", 1, None, 0.5, GEN)


def fund():
    title("2. 'The Fund': evidence on a bounded-ambiguous term needs an ambiguity allowance")
    s = Store()
    party, pay, fund, he, ev = fund_world(s)
    check(s.objects()[2]["dsn_state"] == "BOUNDED_AMBIGUOUS", "the term 'the Fund' is BOUNDED_AMBIGUOUS {Alpha Fund, Beta Fund} and was admitted with its ambiguity")
    refused("AMBIGUITY_ALLOWANCE_REQUIRED", s.bind_evidence, he, ev, "SUPPORTS", GEN, proposed_by=GEN)
    refused("ALLOWANCE_NEEDS_A_HUMAN", s.grant_allowance, he, ev, [{fund: "Alpha Fund"}], "statement names Alpha", SYS, GEN)
    refused("ALLOWANCE_SELF_GRANT", s.grant_allowance, he, ev, [{fund: "Alpha Fund"}], "statement names Alpha", ME, ME)
    refused("ALLOWANCE_MUST_NAME_COMBINATIONS", s.grant_allowance, he, ev, [], "ok", ME, GEN)
    refused("ALLOWANCE_MUST_NAME_COMBINATIONS", s.grant_allowance, he, ev, [{fund: "Gamma Fund"}], "ok", ME, GEN)
    refused("ALLOWANCE_NEEDS_A_REASON", s.grant_allowance, he, ev, [{fund: "Alpha Fund"}], "  ", ME, GEN)
    al = s.grant_allowance(he, ev, [{fund: "Alpha Fund"}], "statement names Alpha", ME, GEN)
    check(True, "a human (not the proposer) granted an allowance naming the combination {the Fund = Alpha Fund}")
    s.bind_evidence(he, ev, "SUPPORTS", SYS, allowance=al, proposed_by=GEN)
    ev2 = s.add_evidence("bank-statement-2", "Document", "TIER_1_CANONICAL", "Second statement", SYS)
    refused("ALLOWANCE_COVERS_ONE_BINDING", s.bind_evidence, he, ev2, "SUPPORTS", SYS, allowance=al)
    r = s.admit_hyperedge(he, SYS)
    check(r["admitted"], "admitted, with the allowance-bound evidence")
    notes = json.loads(s._one("SELECT uncertainty_notes FROM hyperedges WHERE id=?", he)["uncertainty_notes"])
    check(any("Alpha Fund" in n for n in notes), f"the uncertainty envelope carries the ambiguity: {notes}")
    check(s.projection()[0]["label"] == "Bounded Ambiguous", "projected as Bounded Ambiguous, never plain Admitted")
    print("    -- the term is later narrowed to Alpha Fund")
    s.narrow(fund, "NARROWED", SYS, {"kind": "source", "detail": "engagement letter names Alpha", "alternatives": ["Alpha Fund", "Beta Fund"]}, semantic_type="Fund", label="Alpha Fund")
    check(s._allowance_state(al)[0] == "STANDS", "the allowance lapsed and the binding stands as an ordinary one (a granted combination still matches)")
    check(s.state("hyperedges", he) == "ADMITTED", "the binding stands as an ordinary one (Alpha is covered): hyperedge stays ADMITTED")
    check(s.projection()[0]["label"] == "Admitted", "and is now projected as plain Admitted")
    check(s.verify_chain()[0], "receipt chain still verifies")
    print("      fund trail:", [(t[1], t[2]) for t in s.trail(fund)])


def narrowed_to_beta():
    title("3. The allowance covered Alpha only; the term is narrowed to Beta")
    for admitted_first in (False, True):
        s = Store()
        party, pay, fund, he, ev = fund_world(s)
        al = s.grant_allowance(he, ev, [{fund: "Alpha Fund"}], "statement names Alpha", ME, GEN)
        s.bind_evidence(he, ev, "SUPPORTS", SYS, allowance=al, proposed_by=GEN)
        if admitted_first:
            s.admit_hyperedge(he, SYS)
        s.narrow(fund, "NARROWED", SYS, {"kind": "source", "detail": "engagement letter names Beta", "alternatives": ["Alpha Fund", "Beta Fund"]}, semantic_type="Fund", label="Beta Fund")
        st = s.state("hyperedges", he)
        if admitted_first:
            check(st == "CHALLENGED", f"hyperedge was ADMITTED: support is gone so it becomes CHALLENGED, not 'PENDING' (got {st})")
            print("      (the allowance draft said 'returns to PENDING'; from ADMITTED that transition is illegal: see FINDINGS F6)")
        else:
            check(st == "PENDING", f"hyperedge was still PENDING: it stays PENDING with UNSUPPORTED recorded (got {st})")
        check(any(t[3].get("reason") == "UNSUPPORTED" for t in s.trail(he)) or st == "CHALLENGED", "the loss of support is on the receipt trail")


def tier4():
    title("4. Tier 4 (generative hypotheses) are tracked but never sufficient")
    s = Store()
    a, b, pool = obj(s, "Party A", "Party A", "Party"), obj(s, "Party B", "Party B", "Party"), obj(s, "Asset Pool", "Asset Pool", "Asset")
    he = obligation(s, a, b, pool)
    guess = s.add_evidence("model-summary", "Generated", "TIER_4_GENERATIVE", "The model believes A owes B", SYS)
    check(s.trail(guess)[0][2] == "PEND", "a tier-4 record gets a PEND receipt: tracked, not admitted")
    s.bind_evidence(he, guess, "SUPPORTS", SYS)
    r = s.admit_hyperedge(he, SYS)
    check(not r["admitted"] and r["reason"] == "UNTRUSTED", f"tier-4 evidence alone: 據界 UNTRUSTED (bound but insufficient), stays {r['state']}")
    good = s.add_evidence("contract", "Document", "TIER_1_CANONICAL", "A owes B", SYS)
    s.bind_evidence(he, good, "SUPPORTS", SYS)
    check(s.admit_hyperedge(he, SYS)["admitted"], "adding tier-1 evidence lets it through")


def lifecycle():
    title("5. Challenge, review, reaffirm, revise, revoke, and 'never resumed'")
    s = Store()
    a, b, pool = obj(s, "Party A", "Party A", "Party"), obj(s, "Party B", "Party B", "Party"), obj(s, "Asset Pool", "Asset Pool", "Asset")
    he = obligation(s, a, b, pool)
    ev = s.add_evidence("contract", "Document", "TIER_1_CANONICAL", "A owes B", SYS)
    s.bind_evidence(he, ev, "SUPPORTS", SYS)
    s.admit_hyperedge(he, SYS)
    print("    -- (a) contradicting evidence arrives; the challenge is dismissed (the L1 edge)")
    bad = s.add_evidence("email", "Document", "TIER_2_ADMITTED", "A says nothing is owed", SYS)
    s.bind_evidence(he, bad, "CONTRADICTS", SYS)
    check(s.state("hyperedges", he) == "CHALLENGED", "contradicting evidence on an ADMITTED hyperedge challenges it")
    check(not s.projection()[0]["assertable"], "and withdraws it from projection at once (D8)")
    s.begin_review(he, SYS)
    refused("OUTCOME_NOT_LEGAL_FOR_HISTORY", s.resolve_review, he, "rerun", ME)
    refused("CANNOT_REAFFIRM", s.resolve_review, he, "reaffirm", ME)
    refused("DISMISSING_A_CONTRADICTION_NEEDS_A_HUMAN", s.void_binding, he, bad, "not a real contradiction", SYS)
    s.void_binding(he, bad, "email was superseded", ME)
    row = s._one("SELECT void_reason, voided_receipt_id FROM hyperedge_evidence WHERE hyperedge_id=? AND evidence_id=?", he, bad)
    check(row["void_reason"] and row["voided_receipt_id"], "the contradicting binding is VOIDED with a reason and a receipt, not deleted: the record of it stays")
    refused("ALREADY_VOIDED", s.void_binding, he, bad, "again", ME)
    s.resolve_review(he, "reaffirm", ME, "challenge dismissed")
    check(s.state("hyperedges", he) == "ADMITTED", "after the contradiction is voided, UNDER_REVIEW -> ADMITTED (reaffirmed under a new receipt)")
    print("      trail:", [(t[1], t[2]) for t in s.trail(he)][-5:])
    print("    -- (b) upheld: revise, then close")
    s.challenge(he, "terms amended", SYS); s.begin_review(he, SYS)
    s.resolve_review(he, "revise", ME); s.close(he, ME)
    check(s.state("hyperedges", he) == "CLOSED", "REVISED -> CLOSED")
    print("    -- (c) terminal states are never resumed")
    refused("ILLEGAL_TRANSITION", s._move, "hyperedges", he, "ADMITTED", SYS)
    try:
        s.db.execute("UPDATE hyperedges SET admission_state='ADMITTED' WHERE id=?", (he,))
        check(False, "the database allowed a terminal hyperedge to be resumed")
    except Exception as e:
        check("never resumed" in str(e), f"even raw SQL cannot resume it: {e}")
    new = s.reopen_hyperedge(he, SYS)
    check(new != he and s.state("hyperedges", new) == "PENDING", "reopening raises a NEW candidate with a new id, identical content")
    row = s._one("SELECT predecessor_ids, lineage_hash FROM hyperedges WHERE id=?", new)
    check(json.loads(row["predecessor_ids"]) == [he] and row["lineage_hash"], "it names its predecessor and carries a lineage hash")
    check(not s._all("SELECT 1 FROM hyperedge_evidence WHERE hyperedge_id=?", new), "evidence is NOT carried over: it must be bound afresh (FINDINGS F7)")
    refused("PREDECESSOR_NOT_TERMINAL", s.propose_hyperedge, "OBLIGATION", [(a, "SUBJECT"), (b, "BENEFICIARY"), (pool, "OBJECT")], "demo", 1, None, 0.8, GEN, predecessor_ids=[new])
    refused("DUPLICATE_CANDIDATE", s.propose_hyperedge, "OBLIGATION", [(a, "SUBJECT"), (b, "BENEFICIARY"), (pool, "OBJECT")], "demo", 1, None, 0.8, GEN, predecessor_ids=[])
    print("    -- (d) revoking a member cascades (section 8.3)")
    s2 = Store()
    a, b, pool = obj(s2, "Party A", "Party A", "Party"), obj(s2, "Party B", "Party B", "Party"), obj(s2, "Asset Pool", "Asset Pool", "Asset")
    he2 = obligation(s2, a, b, pool)
    s2.bind_evidence(he2, s2.add_evidence("c", "Document", "TIER_1_CANONICAL", "A owes B", SYS), "SUPPORTS", SYS)
    s2.admit_hyperedge(he2, SYS)
    s2.revoke_object(b, ME, "Party B was a duplicate record")
    check(s2.state("hyperedges", he2) == "CHALLENGED", "the hyperedge that used the revoked object is CHALLENGED")
    check(s2.projection()[0]["label"] == "Challenged", "and shows as Challenged")


def dsn():
    title("6. DSN: recorded basis, bounded vs unresolved, retries")
    s = Store()
    o = s.propose_candidate("control", "demo", "prototype", GEN)
    refused("NO_RECORDED_BASIS", s.narrow, o, "NARROWED", GEN, {"kind": "model_reading", "detail": "most probable meaning", "alternatives": ["x"]}, semantic_type="Control", label="NIST control")
    refused("BOUNDED_NEEDS_A_FINITE_SET", s.narrow, o, "BOUNDED_AMBIGUOUS", GEN, {"kind": "context", "alternatives": ["a"]}, meanings=["a"])
    refused("UNRESOLVED_HAS_NO_SET", s.narrow, o, "UNRESOLVED", GEN, {"kind": "context"}, meanings=["a", "b"])
    refused("ALTERNATIVES_NOT_RECORDED", s.narrow, o, "NARROWED", GEN, {"kind": "context"}, semantic_type="Control", label="NIST control")
    s.narrow(o, "UNRESOLVED", GEN, {"kind": "context", "detail": "no domain given"})
    refused("DSN_NOT_ADMISSIBLE", s.admit_semantic_object, o, SYS)
    s.narrow(o, "NARROWED", GEN, {"kind": "context", "detail": "RMF context, control ID present", "alternatives": ["access control", "control loop"]}, semantic_type="Control", label="NIST SP 800-53 control")
    dsn_receipts = [t for t in s.trail(o) if t[1] == "DSN_COMMIT"]
    check(len(dsn_receipts) == 2 and dsn_receipts[0][2] == "PEND", "the UNRESOLVED attempt left a receipt on the SAME object; the retry is a second receipt (B5) with no predecessor needed")
    check(dsn_receipts[1][2] == "CLEAR", "a narrowed term's receipt says CLEAR (cleared for admission), not ADMIT (decision 1)")
    s.admit_semantic_object(o, SYS)
    check(s.state("semantic_objects", o) == "ADMITTED", "then admitted by semantic admission alone (ADR 0002)")
    check(s.trail(o)[-1][1:3] == ("SEMANTIC_ADMIT", "ADMIT"), "and the admission is its own receipt type, SEMANTIC_ADMIT with ADMIT (decision 1)")
    print("    -- conflict and denial")
    c = s.propose_candidate("Apple", "demo", "prototype", GEN)
    s.narrow(c, "CONFLICT", GEN, {"kind": "source", "detail": "two sources disagree", "alternatives": ["Apple Inc", "the fruit"]})
    check(s.state("semantic_objects", c) == "UNDER_REVIEW", "a DSN CONFLICT sends the candidate to UNDER_REVIEW")
    d = s.propose_candidate("the moon", "demo", "prototype", GEN)
    s.narrow(d, "DENIED", GEN, {"kind": "policy", "detail": "outside the ontology"})
    check(s.state("semantic_objects", d) == "DENIED", "a DSN DENIED is DENIED")
    d2 = s.reopen_object(d, SYS)
    row = s._one("SELECT predecessor_ids FROM semantic_objects WHERE id=?", d)
    check(d2 != d and json.loads(s._one("SELECT predecessor_ids FROM semantic_objects WHERE id=?", d2)["predecessor_ids"]) == [d], "a retry after denial is a NEW candidate naming the denied one")
    print("      NOTE: no operation resolves a semantic object that is UNDER_REVIEW; only hyperedges have resolve_review here (FINDINGS F12)")


def path():
    title("7. Path and uncertainty boundaries")
    s = Store()
    x, y, z = obj(s, "X", "X", "Thing"), obj(s, "Y", "Y", "Thing"), obj(s, "Z", "Z", "Thing")

    def causal(c, e):
        he = s.propose_hyperedge("CAUSAL", [(c, "SUBJECT"), (e, "OBJECT")], "demo", 1, None, 0.7, GEN)
        s.bind_evidence(he, s.add_evidence(f"e-{he}", "Document", "TIER_1_CANONICAL", f"{c} causes {e}", SYS), "SUPPORTS", SYS)
        return he
    h1, h2 = causal(x, y), causal(y, z)
    check(s.admit_hyperedge(h1, SYS)["admitted"] and s.admit_hyperedge(h2, SYS)["admitted"], "X causes Y and Y causes Z are admitted")
    h3 = causal(z, x)
    r = s.admit_hyperedge(h3, SYS)
    check(not r["admitted"] and r["boundary"] == "徑界" and r["reason"] == "PATH_BREAK" and r["state"] == "PENDING", "Z causes X would close a causal loop: 徑界 PATH_BREAK, stays PENDING (rolls back to 名界)")
    print("    -- 幅界: no uncertainty envelope")
    he = s.propose_hyperedge("CLAIM", [(x, "SUBJECT")], "demo", 1, None, None, GEN)
    s.bind_evidence(he, s.add_evidence("e-claim", "Document", "TIER_1_CANONICAL", "X exists", SYS), "SUPPORTS", SYS)
    r = s.admit_hyperedge(he, SYS)
    check(not r["admitted"] and r["boundary"] == "幅界" and r["state"] == "UNDER_REVIEW", "no confidence bound: 幅界 NEEDS_REVISION, the candidate goes UNDER_REVIEW")
    refused("OUTCOME_NOT_LEGAL_FOR_HISTORY", s.resolve_review, he, "reaffirm", ME)
    s.resolve_review(he, "rerun", ME)
    check(s.state("hyperedges", he) == "PENDING", "never admitted, so the review could only re-run it (PENDING) or reject it, never reaffirm")
    s.set_uncertainty(he, 0.6, ["one source"], SYS)
    check(s.admit_hyperedge(he, SYS)["admitted"], "with an uncertainty envelope bound it passes")


def ledger():
    title("8. Receipt chain and append-only enforcement")
    s = Store()
    a = obj(s, "Party A", "Party A", "Party")
    ok, at = s.verify_chain()
    check(ok, "chain verifies")
    try:
        s.db.execute("UPDATE receipts SET decision='DENY' WHERE seq=1")
        check(False, "receipt UPDATE was allowed")
    except Exception as e:
        check("append-only" in str(e), f"UPDATE on a receipt is blocked: {e}")
    try:
        s.db.execute("DELETE FROM receipts WHERE seq=1")
        check(False, "receipt DELETE was allowed")
    except Exception as e:
        check("append-only" in str(e), f"DELETE on a receipt is blocked: {e}")
    try:
        s.db.execute("INSERT INTO receipts VALUES ('x', 99, 'INVENTED_TYPE', 's', 'ADMIT', '{}', 'a', 1, NULL)")
        check(False, "an invented receipt type was accepted")
    except Exception as e:
        check("CHECK" in str(e), "the receipt vocabulary is closed: an invented receipt type is rejected by the database (decision 1)")
    s.db.execute("DROP TRIGGER receipts_append_only_u")   # a privileged attacker removes the guard, then tampers
    s.db.execute("UPDATE receipts SET basis='{\"forged\":true}' WHERE seq=2")
    ok, at = s.verify_chain()
    check(not ok and at == 2, f"tampering with receipt #2 after removing the trigger is caught by the chain at seq {at}")
    print("      the chain is GLOBAL (one sequence for every subject): it serialises all writers (FINDINGS F13)")


def combinations():
    title("9. Two bounded terms in one claim: one allowance names the COMBINATIONS it holds under (decision 6)")

    def world():
        s = Store()
        party, pay = obj(s, "Party A", "Party A", "Party"), obj(s, "the payment", "Payment", "Asset")
        fund = bounded(s, "the Fund", ["Alpha Fund", "Beta Fund"], "Fund")
        trust = bounded(s, "the Trust", ["North Trust", "South Trust"], "Trust")
        he = s.propose_hyperedge("OBLIGATION", [(party, "SUBJECT"), (fund, "BENEFICIARY"), (trust, "OBJECT")], "demo", 1, None, 0.7, GEN)
        ev = s.add_evidence("statement", "Document", "TIER_1_CANONICAL", "Alpha Fund paid into the North Trust", SYS)
        return s, fund, trust, he, ev

    s, fund, trust, he, ev = world()
    refused("AMBIGUITY_ALLOWANCE_REQUIRED", s.bind_evidence, he, ev, "SUPPORTS", GEN, proposed_by=GEN)
    refused("ALLOWANCE_MUST_NAME_COMBINATIONS", s.grant_allowance, he, ev, [{fund: "Alpha Fund"}], "names Alpha", ME, GEN)   # a combination must cover every bounded member
    refused("ALLOWANCE_MUST_NAME_COMBINATIONS", s.grant_allowance, he, ev, [{fund: "Alpha Fund", trust: "East Trust"}], "names Alpha", ME, GEN)
    al = s.grant_allowance(he, ev, [{fund: "Alpha Fund", trust: "North Trust"}], "statement names Alpha and the North Trust", ME, GEN)
    s.bind_evidence(he, ev, "SUPPORTS", SYS, allowance=al, proposed_by=GEN)
    check(s.admit_hyperedge(he, SYS)["admitted"], "one allowance covers both bounded members; the hyperedge is admitted")
    check(s.projection()[0]["label"] == "Bounded Ambiguous", "projected as Bounded Ambiguous")
    print("    -- the evidence holds for (Alpha, North) only. Approving each term separately would also have approved (Alpha, South) and (Beta, North).")
    for label, first, second in (("(a) the Trust is narrowed to North, then the Fund to Alpha", (1, "North Trust"), (0, "Alpha Fund")),):
        s, fund, trust, he, ev = world()
        al = s.grant_allowance(he, ev, [{fund: "Alpha Fund", trust: "North Trust"}], "names both", ME, GEN)
        s.bind_evidence(he, ev, "SUPPORTS", SYS, allowance=al, proposed_by=GEN)
        s.admit_hyperedge(he, SYS)
        ids = (fund, trust)
        s.narrow(ids[first[0]], "NARROWED", SYS, {"kind": "source", "detail": "letter", "alternatives": ["a", "b"]}, semantic_type="T", label=first[1])
        check(s._allowance_state(al)[0] == "ACTIVE" and s.state("hyperedges", he) == "ADMITTED", f"{label}: after the first narrowing the Fund is still bounded, so the allowance stays ACTIVE")
        s.narrow(ids[second[0]], "NARROWED", SYS, {"kind": "source", "detail": "letter", "alternatives": ["a", "b"]}, semantic_type="T", label=second[1])
        check(s._allowance_state(al)[0] == "STANDS" and s.state("hyperedges", he) == "ADMITTED", "then the granted combination is all that is left: the binding stands as an ordinary one")
        check(s.projection()[0]["label"] == "Admitted", "and is projected as plain Admitted")
    for label, term, meaning in (("(b) the Fund is narrowed to Beta", 0, "Beta Fund"), ("(c) the Trust is narrowed to South", 1, "South Trust")):
        s, fund, trust, he, ev = world()
        al = s.grant_allowance(he, ev, [{fund: "Alpha Fund", trust: "North Trust"}], "names both", ME, GEN)
        s.bind_evidence(he, ev, "SUPPORTS", SYS, allowance=al, proposed_by=GEN)
        s.admit_hyperedge(he, SYS)
        s.narrow((fund, trust)[term], "NARROWED", SYS, {"kind": "source", "detail": "letter", "alternatives": ["a", "b"]}, semantic_type="T", label=meaning)
        check(s.state("hyperedges", he) == "CHALLENGED", f"{label}: no granted combination remains, so the binding is voided and the ADMITTED hyperedge is CHALLENGED (decision 4)")
        row = s._one("SELECT void_reason, voided_receipt_id FROM hyperedge_evidence WHERE hyperedge_id=?", he)
        check(row["void_reason"] and row["voided_receipt_id"], f"the binding is voided with a receipt, by the system: {row['void_reason']}")


SCENARIOS = {"happy": happy, "fund": fund, "beta": narrowed_to_beta, "tier4": tier4, "lifecycle": lifecycle, "dsn": dsn, "path": path, "ledger": ledger, "combos": combinations}

if __name__ == "__main__":
    names = sys.argv[1:] or list(SCENARIOS)
    for n in names:
        SCENARIOS[n]()
    print(f"\n{sum(RESULTS)} of {len(RESULTS)} checks met their expectation")
    sys.exit(0 if all(RESULTS) else 1)
