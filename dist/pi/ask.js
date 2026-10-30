import { Type } from "typebox";
export const OTHER = "Other (type an answer)";
export const DONE = "Done";
const question = Type.Object({
    question: Type.String({ description: "The complete question to ask the user" }),
    header: Type.Optional(Type.String({ description: "Very short label for the question (max 12 chars)" })),
    options: Type.Array(Type.Object({ label: Type.String(), description: Type.Optional(Type.String()) }), { minItems: 2, maxItems: 4 }),
    multiSelect: Type.Optional(Type.Boolean({ description: "Allow more than one answer" })),
});
const questionParams = Type.Object({ questions: Type.Array(question, { minItems: 1, maxItems: 4 }) });
// undefined means the user dismissed the dialog.
async function ask(ui, q, signal) {
    const title = q.header ? `${q.header}: ${q.question}` : q.question;
    // Pi returns the displayed string, so number choices to distinguish them
    // from controls and from other choices with the same rendered text.
    const labels = new Map(q.options.map((o, i) => [`${i + 1}. ${o.label}${o.description ? ` - ${o.description}` : ""}`, o.label]));
    // The label of a listed pick, or what the user types for OTHER.
    const answer = (pick) => (pick === OTHER ? ui.input(title, "Your answer", { signal }) : labels.get(pick));
    if (!q.multiSelect) {
        const pick = await ui.select(title, [...labels.keys(), OTHER], { signal });
        return pick === undefined ? undefined : answer(pick);
    }
    const picked = new Set();
    const chosen = [];
    for (;;) {
        const remaining = [...labels.keys()].filter((text) => !picked.has(text));
        const pick = await ui.select(`${title} (one at a time; ${DONE} when finished)`, [...remaining, OTHER, DONE], { signal });
        if (pick === undefined)
            return undefined;
        if (pick === DONE)
            return chosen.join(", ");
        const text = await answer(pick);
        if (text === undefined)
            return undefined;
        picked.add(pick);
        chosen.push(text);
    }
}
// model-only exposure keeps the tool declared under codemode.mode "only".
export function registerAsk(pi, oneShot) {
    pi.registerTool({
        name: "ask_user_question",
        label: "Ask user",
        exposure: "model-only",
        description: "Ask the user 1-4 structured questions, each with 2-4 options; the user can also type their own answer. Use it for genuine preference calls the user must make.",
        parameters: questionParams,
        executionMode: "sequential",
        async execute(_id, params, signal, _onUpdate, ctx) {
            // An rpc child reports a UI, but its parent cancels every dialog, so asking
            // could only report a dismissal.
            if (!ctx.hasUI || oneShot.exits(ctx)) {
                throw new Error("ask_user_question needs an interactive UI, and this session has none. Ask the user in plain text instead and wait for the reply.");
            }
            const answers = [];
            for (const q of params.questions) {
                const answer = await ask(ctx.ui, q, signal);
                if (answer === undefined)
                    break;
                answers.push({ question: q.question, answer });
            }
            const dismissed = answers.length < params.questions.length;
            const text = answers.map((a) => `"${a.question}"="${a.answer}"`).join(", ");
            // Pi sends content to the model; details alone cannot preserve earlier answers.
            const answered = answers.length ? `User has answered your questions: ${text}. ` : "";
            const status = !dismissed
                ? "You can now continue with the user's answers in mind."
                : answers.length
                    ? "The user dismissed the remaining questions without answering."
                    : "The user dismissed the question without answering.";
            return {
                content: [{ type: "text", text: answered + status }],
                details: { answers, dismissed },
            };
        },
    });
}
