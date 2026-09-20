import json
import re
import logging
from typing import Dict, Any
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import httpx
import asyncio

app = FastAPI(title="CHI Proxy - PTGM + Dynamic Tools")

# ==================== CONFIG ====================
VLLM_BASE_URL = "http://127.0.0.1:8000"
PROXY_PORT = 8001

logger = logging.getLogger(__name__)

# ==================== TOOL SELECTOR + PTGM (Compact) ====================
TOOL_REGISTRY = {
    "read_file": {"name": "read_file", "category": "file", "keywords": ["read", "open", "view", "content", "file"], "description": "Read file contents."},
    "edit_file": {"name": "edit_file", "category": "file", "keywords": ["edit", "replace", "modify", "fix"], "description": "Edit existing file."},
    "write_file": {"name": "write_file", "category": "file", "keywords": ["write", "create", "new file"], "description": "Create or overwrite file."},
    "bash": {"name": "bash", "category": "system", "keywords": ["command", "run", "terminal", "bash"], "description": "Run shell commands."},
    "web_search": {"name": "web_search", "category": "search", "keywords": ["search", "google", "info"], "description": "Search the web."},
    "gmail_search": {"name": "gmail_search", "category": "email", "keywords": ["gmail", "email", "delete", "remove", "newsletter"], "description": "Manage Gmail."},
}

# Narrowed to avoid false positives on queries like "what's 2+2"
CONVERSATIONAL_PATTERNS = re.compile(
    r'\b(why|what did|how come|explain|clarify|mistake|wrong|sorry|thanks|okay|ok|sure|got it|my bad|my apologies)\b',
    re.IGNORECASE,
)

def select_tools(user_query: str, max_tools: int = 6):
    if CONVERSATIONAL_PATTERNS.search(user_query.lower()):
        return []

    scores = {}
    q = user_query.lower()
    for name, tool in TOOL_REGISTRY.items():
        score = sum(1 for kw in tool["keywords"] if kw in q)
        if score > 0:
            scores[name] = score

    selected = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)[:max_tools]

    # No fallback — if nothing matches, send no tools and let the model decide
    if not selected:
        return []

    return [
        {"type": "function", "function": {"name": TOOL_REGISTRY[n]["name"], "description": TOOL_REGISTRY[n]["description"]}}
        for n in selected
    ]

# ==================== SHARED HTTPX CLIENT ====================
client = httpx.AsyncClient(timeout=300.0)

@app.on_event("shutdown")
async def shutdown():
    await client.aclose()

# ==================== PROXY LOGIC ====================
async def forward_request(request: Request):
    body = await request.json()

    # Extract user message for tool selection
    messages = body.get("messages", [])
    user_query = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content")
            if isinstance(content, str):
                user_query = content
            elif isinstance(content, list):
                user_query = " ".join(c.get("text", "") for c in content if isinstance(c, dict))
            break

    # Apply PTGM + Dynamic Tool Selection
    if messages:
        selected_tools = select_tools(user_query, max_tools=6)
    else:
        selected_tools = []

    body["tools"] = selected_tools

    logger.info("CHI Proxy | Query: %s... | Tools: %d", user_query[:80], len(selected_tools))

    async with client.stream(
        method=request.method,
        url=f"{VLLM_BASE_URL}{request.url.path}",
        headers=dict(request.headers),
        json=body,
    ) as resp:
        async def stream_generator():
            async for chunk in resp.aiter_bytes():
                yield chunk

        # Strip headers invalid on streaming responses
        resp_headers = {
            k: v for k, v in resp.headers.items()
            if k.lower() not in ("transfer-encoding", "content-length", "connection")
        }

        return StreamingResponse(
            stream_generator(),
            status_code=resp.status_code,
            headers=resp_headers,
        )

@app.post("/v1/messages")
async def proxy_messages(request: Request):
    return await forward_request(request)

@app.get("/v1/models")
async def proxy_models(request: Request):
    resp = await client.get(f"{VLLM_BASE_URL}/v1/models")
    return resp.json()

@app.get("/health")
async def health():
    try:
        resp = await client.get(f"{VLLM_BASE_URL}/v1/models")
        return {"status": "healthy" if resp.is_success else "unhealthy"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/")
async def root():
    return {"status": "CHI Proxy with PTGM is running", "target": VLLM_BASE_URL}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=PROXY_PORT)