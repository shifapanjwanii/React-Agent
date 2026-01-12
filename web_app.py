"""
FastAPI + Modal web interface for the Smart Utility ReAct Agent.
Serves a lightweight chat UI and exposes an API endpoint for responses.
"""

import os
import sys
from functools import lru_cache

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import modal

# Load local environment variables for dev runs (only if dotenv is available).
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


def _build_agent():
    """Create a ReActAgent instance with environment-driven config."""
    # Try importing from agent module (local dev), fall back to sys.path (Modal)
    try:
        from agent.agent import ReActAgent
        from agent.openrouter import OpenRouterClient
    except ImportError:
        import sys
        sys.path.insert(0, "/workspace")
        from agent.agent import ReActAgent
        from agent.openrouter import OpenRouterClient
    
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set. Add it to your env or Modal secret.")

    model = os.environ.get("OPENROUTER_MODEL")
    max_iterations = int(os.environ.get("AGENT_MAX_ITERATIONS", "10"))

    client = OpenRouterClient(api_key=api_key, model=model) if model else OpenRouterClient(api_key=api_key)
    return ReActAgent(client, max_iterations=max_iterations, verbose=False)


@lru_cache(maxsize=1)
def get_agent():
    """Return a cached agent to avoid re-initializing per request."""
    return _build_agent()


class ChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=4000)


class ChatResponse(BaseModel):
    reply: str


app = FastAPI(title="Smart Utility Web")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return HTML_TEMPLATE


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    agent = get_agent()
    try:
        reply = agent.run(request.prompt.strip())
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ChatResponse(reply=reply)


# Modal setup for deployment.
stub = modal.App("smart-utility-web")

image = (
    modal.Image.debian_slim()
    .pip_install(
        "requests>=2.31.0",
        "python-dotenv>=1.0.0",
        "fastapi>=0.110.0",
        "uvicorn>=0.23.0",
        "pydantic>=2.7.0"
    )
)


@stub.function(image=image, secrets=[modal.Secret.from_name("smart-utility-secrets")], allow_concurrent_inputs=10)
@modal.asgi_app()
def fastapi_app():
    """Entrypoint for Modal; returns the FastAPI app."""
    import sys
    sys.path.insert(0, "/workspace")
    return app


# Local development entrypoint.
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


# Minimal inline UI (HTML + CSS + JS) for a split-bubble chat layout.
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang=\"en\">
<head>
  <meta charset=\"UTF-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\" />
  <title>Smart Utility Agent</title>
  <link href=\"https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600&display=swap\" rel=\"stylesheet\" />
  <style>
    :root {
      --bg: #0f172a;
      --panel: #111827;
      --accent: #7c3aed;
      --accent-2: #22c55e;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --border: #1f2937;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: 'Space Grotesk', system-ui, -apple-system, sans-serif;
      background: radial-gradient(circle at 20% 20%, rgba(124, 58, 237, 0.08), transparent 30%),
                  radial-gradient(circle at 80% 0%, rgba(34, 197, 94, 0.1), transparent 25%),
                  linear-gradient(135deg, #0b1220 0%, #0f172a 50%, #0b1220 100%);
      color: var(--text);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 32px 14px;
    }
    .frame {
      width: min(1100px, 100%);
      background: rgba(17, 24, 39, 0.9);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 25px 70px rgba(0,0,0,0.4);
      overflow: hidden;
      display: grid;
      grid-template-rows: auto 1fr auto;
      backdrop-filter: blur(4px);
    }
    header {
      padding: 18px 20px;
      border-bottom: 1px solid var(--border);
      display: flex;
      gap: 10px;
      align-items: center;
    }
    .logo {
      width: 38px;
      height: 38px;
      border-radius: 12px;
      background: linear-gradient(135deg, #7c3aed, #22c55e);
      display: grid;
      place-items: center;
      color: #0b1220;
      font-weight: 700;
      letter-spacing: -0.5px;
      box-shadow: 0 10px 25px rgba(124, 58, 237, 0.35);
    }
    h1 { margin: 0; font-size: 20px; letter-spacing: -0.02em; }
    .sub { color: var(--muted); font-size: 14px; }
    #chat {
      padding: 20px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 12px;
      background: radial-gradient(circle at 60% 40%, rgba(124, 58, 237, 0.05), transparent 40%);
    }
    .row { display: flex; }
    .row.user { justify-content: flex-end; }
    .row.assistant { justify-content: flex-start; }
    .bubble {
      max-width: 72%;
      padding: 14px 16px;
      border-radius: 14px;
      border: 1px solid var(--border);
      line-height: 1.5;
      font-size: 15px;
      white-space: pre-wrap;
      box-shadow: 0 12px 30px rgba(0,0,0,0.25);
    }
    .user .bubble {
      background: linear-gradient(135deg, #22c55e, #16a34a);
      color: #082f1f;
      font-weight: 600;
      border: none;
    }
    .assistant .bubble {
      background: #0c1424;
      color: var(--text);
    }
    form {
      display: flex;
      gap: 10px;
      padding: 16px 18px 18px;
      border-top: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(12,20,36,0.9), rgba(12,20,36,0.8));
    }
    textarea {
      flex: 1;
      background: #0c1424;
      color: var(--text);
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 12px;
      resize: none;
      min-height: 48px;
      font-family: inherit;
      font-size: 15px;
      outline: none;
      transition: border-color 0.2s ease, box-shadow 0.2s ease;
    }
    textarea:focus {
      border-color: var(--accent);
      box-shadow: 0 0 0 3px rgba(124, 58, 237, 0.25);
    }
    button {
      padding: 12px 16px;
      background: linear-gradient(135deg, #7c3aed, #6d28d9);
      color: #f8fafc;
      border: none;
      border-radius: 12px;
      cursor: pointer;
      font-weight: 600;
      letter-spacing: -0.01em;
      box-shadow: 0 12px 30px rgba(124, 58, 237, 0.35);
      transition: transform 0.1s ease, filter 0.2s ease;
      min-width: 96px;
    }
    button:active { transform: translateY(1px); }
    button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
      box-shadow: none;
    }
    .notice { color: var(--muted); font-size: 13px; padding: 0 18px 12px; }
    @media (max-width: 640px) {
      .frame { grid-template-rows: auto 1fr auto; }
      .bubble { max-width: 90%; }
      form { flex-direction: column; }
      button { width: 100%; }
    }
  </style>
</head>
<body>
  <div class=\"frame\">
    <header>
      <div class=\"logo\">SU</div>
      <div>
        <h1>Smart Utility Agent</h1>
        <div class=\"sub\">Chat-style UI backed by the ReAct tools</div>
      </div>
    </header>
    <div id=\"chat\"></div>
    <div class=\"notice\">Capabilities: weather, currency, calculator, research papers, recent earthquakes.</div>
    <form id=\"form\">
      <textarea id=\"prompt\" placeholder=\"Ask anything...\" required></textarea>
      <button id=\"send\" type=\"submit\">Send</button>
    </form>
  </div>
  <script>
    const chat = document.getElementById('chat');
    const form = document.getElementById('form');
    const promptEl = document.getElementById('prompt');
    const sendBtn = document.getElementById('send');

    const addBubble = (role, text) => {
      const row = document.createElement('div');
      row.className = `row ${role}`;
      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      bubble.textContent = text;
      row.appendChild(bubble);
      chat.appendChild(row);
      chat.scrollTop = chat.scrollHeight;
    };

    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const prompt = promptEl.value.trim();
      if (!prompt) return;
      addBubble('user', prompt);
      promptEl.value = '';
      promptEl.focus();
      sendBtn.disabled = true;
      const loading = document.createElement('div');
      loading.className = 'row assistant';
      const bubble = document.createElement('div');
      bubble.className = 'bubble';
      bubble.textContent = 'Thinking...';
      loading.appendChild(bubble);
      chat.appendChild(loading);
      chat.scrollTop = chat.scrollHeight;

      try {
        const res = await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ prompt })
        });
        const data = await res.json();
        loading.remove();
        if (!res.ok) {
          addBubble('assistant', data.detail || 'Something went wrong.');
        } else {
          addBubble('assistant', data.reply);
        }
      } catch (err) {
        loading.remove();
        addBubble('assistant', 'Network error.');
      } finally {
        sendBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""