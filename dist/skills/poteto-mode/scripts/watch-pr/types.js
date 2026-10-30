export function nonEmpty(items) {
    return items.length === 0 ? null : [items[0], ...items.slice(1)];
}
export function parsePrNumber(value, label = "PR number") {
    if (typeof value !== "number" || !Number.isInteger(value) || value <= 0)
        throw new Error(`${label} must be a positive integer`);
    return value;
}
