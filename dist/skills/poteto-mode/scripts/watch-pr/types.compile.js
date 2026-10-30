import { parsePrNumber } from "./types.ts";
const context = {
    owner: "octocat",
    repo: "hello-world",
    number: parsePrNumber(123),
};
const cleanCi = {
    kind: "ci-clean",
    source: "gh-pr-checks",
    all: [
        {
            kind: "passed",
            name: "ci",
            reportedState: "SUCCESS",
            description: "",
            link: "",
            workflow: "",
        },
    ],
    failed: [],
    pending: [],
    hadPreviousPassingCi: false,
    github: {
        kind: "allowed",
        basis: "merge-state",
        mergeStateStatus: "CLEAN",
        headRollupState: "SUCCESS",
    },
};
const readyPr = {
    kind: "ready-pr",
    context,
    proof: {
        revision: { context, headRefOid: "head", baseRefName: "main", baseRefOid: "base" },
        mergeability: "clear",
        threads: [],
        ci: cleanCi,
        gate: {
            state: "OPEN",
            reviewDecision: "APPROVED",
            draft: "not-draft",
        },
    },
};
const ready = {
    schemaVersion: 1,
    sequence: 1,
    observedAt: "2026-07-26T00:00:00.000Z",
    mode: "single",
    kind: "READY",
    terminal: true,
    exitCode: 0,
    scope: { kind: "single", pr: readyPr },
};
void ready;
// PR 179929's shape. Each assertion below stays a single short statement so a
// reformat cannot drift the directive away from the line that actually errors.
const refused = {
    kind: "allowed",
    basis: "rollup",
    mergeStateStatus: "BLOCKED",
    headRollupState: "FAILURE",
};
// @ts-expect-error BLOCKED with a failing rollup is a refusal, not an allowance.
const refusalIsNotAllowed = refused;
// @ts-expect-error CI cannot be clean while GitHub refuses the merge.
const refusalIsNotClean = { ...cleanCi, github: refused };
// @ts-expect-error READY cannot carry the failing-checks exit code.
const readyWithBlockerExit = { ...ready, exitCode: 4 };
const unprovenPr = { kind: "ready-pr", context };
// @ts-expect-error An open READY row must carry positive readiness proof.
const readyWithoutProof = unprovenPr;
const unreportedProof = {
    ...readyPr.proof,
    ci: {
        kind: "ci-unreported",
        failed: [],
        pending: [],
        hadPreviousPassingCi: false,
    },
};
// @ts-expect-error A first sighting of no checks is not readiness proof.
const readyBeforeConfirmation = { ...readyPr, proof: unreportedProof };
void refusalIsNotAllowed;
void refusalIsNotClean;
void readyWithBlockerExit;
void readyWithoutProof;
void readyBeforeConfirmation;
