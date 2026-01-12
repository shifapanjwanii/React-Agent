"""
FastAPI + Modal web interface for the Smart Utility ReAct Agent (Standalone).
Self-contained agent logic for easy Modal deployment.
"""

import os
import sys
import re
import json
import requests
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


# ============================================================================
# INLINE TOOLS (from agent/tools.py)
# ============================================================================

def calculator(expression: str) -> str:
    """Local calculator tool."""
    try:
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Calculation result: {expression} = {result}"
    except Exception as e:
        return f"Calculator error: {str(e)}"


def get_weather(location: str) -> str:
    """Weather API tool using Open-Meteo."""
    try:
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        geocode_params = {"name": location, "count": 1, "language": "en", "format": "json"}
        geocode_response = requests.get(geocode_url, params=geocode_params, timeout=10)
        geocode_data = geocode_response.json()
        
        if not geocode_data.get("results"):
            return f"Weather error: Could not find location '{location}'"
        
        lat = geocode_data["results"][0]["latitude"]
        lon = geocode_data["results"][0]["longitude"]
        place_name = geocode_data["results"][0]["name"]
        
        weather_url = "https://api.open-meteo.com/v1/forecast"
        weather_params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,relative_humidity_2m,weather_code",
            "temperature_unit": "fahrenheit",
            "timezone": "auto"
        }
        weather_response = requests.get(weather_url, params=weather_params, timeout=10)
        weather_data = weather_response.json()
        
        current = weather_data.get("current", {})
        temp = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")
        
        return f"Weather in {place_name}: Temperature: {temp}°F, Humidity: {humidity}%"
    except Exception as e:
        return f"Weather API error: {str(e)}"


def get_earthquake_data(region: str = "all", min_magnitude: float = 4.5) -> str:
    """Earthquake API tool using USGS."""
    try:
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        earthquakes = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            mag = props.get("mag", 0)
            place = props.get("place", "Unknown")
            
            if mag >= min_magnitude:
                if region.lower() != "all" and region.lower() not in place.lower():
                    continue
                
                earthquakes.append({
                    "magnitude": mag,
                    "location": place,
                    "time": props.get("time")
                })
        
        if not earthquakes:
            return f"No earthquakes with magnitude >= {min_magnitude} found in the last 24 hours for region '{region}'"
        
        earthquakes.sort(key=lambda x: x["magnitude"], reverse=True)
        
        result_lines = [f"Found {len(earthquakes)} earthquake(s) with magnitude >= {min_magnitude} in the last 24 hours:"]
        for eq in earthquakes[:5]:
            result_lines.append(f"  - Magnitude {eq['magnitude']}: {eq['location']}")
        
        return "\n".join(result_lines)
    except Exception as e:
        return f"Earthquake API error: {str(e)}"


def search_arxiv(query: str, max_results: int = 3) -> str:
    """arXiv API tool for research papers."""
    try:
        url = "http://export.arxiv.org/api/query"
        params = {
            "search_query": f"all:{query}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return f"arXiv API error: HTTP {response.status_code}"
        
        content = response.text
        papers = []
        entries = content.split("<entry>")[1:]
        
        for entry in entries[:max_results]:
            title_start = entry.find("<title>") + 7
            title_end = entry.find("</title>")
            title = entry[title_start:title_end].strip().replace("\n", " ")
            
            summary_start = entry.find("<summary>") + 9
            summary_end = entry.find("</summary>")
            summary = entry[summary_start:summary_end].strip().replace("\n", " ")
            
            published_start = entry.find("<published>") + 11
            published_end = entry.find("</published>")
            published = entry[published_start:published_end][:10]
            
            papers.append({
                "title": title,
                "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                "published": published
            })
        
        if not papers:
            return f"No papers found for query '{query}'"
        
        result_lines = [f"Found {len(papers)} recent paper(s) on '{query}':"]
        for i, paper in enumerate(papers, 1):
            result_lines.append(f"\n{i}. {paper['title']}")
            result_lines.append(f"   Published: {paper['published']}")
            result_lines.append(f"   Summary: {paper['summary']}")
        
        return "\n".join(result_lines)
    except Exception as e:
        return f"arXiv API error: {str(e)}"


def get_currency_exchange(from_currency: str, to_currency: str, amount: float = 1.0) -> str:
    """Currency exchange tool using exchangerate-api.com."""
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency.upper()}"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code != 200:
            return f"Currency API error: HTTP {response.status_code}"
        
        data = response.json()
        rates = data.get("rates", {})
        target_rate = rates.get(to_currency.upper())
        
        if target_rate is None:
            return f"Currency error: Could not find exchange rate for {from_currency} to {to_currency}"
        
        converted = amount * target_rate
        
        return f"Exchange rate: 1 {from_currency.upper()} = {target_rate:.4f} {to_currency.upper()}. {amount} {from_currency.upper()} = {converted:.2f} {to_currency.upper()}"
    except Exception as e:
        return f"Currency API error: {str(e)}"


TOOLS = {
    "calculator": calculator,
    "get_weather": get_weather,
    "get_earthquake_data": get_earthquake_data,
    "search_arxiv": search_arxiv,
    "get_currency_exchange": get_currency_exchange
}


def get_tool_descriptions() -> str:
    """Returns formatted tool descriptions."""
    return """
Available Tools:

1. calculator(expression: str) -> str
   - Performs arithmetic calculations and percentage operations
   - Example: calculator("100 * 0.15") or calculator("50 + 25")

2. get_weather(location: str) -> str
   - Gets current weather for a location
   - Example: get_weather("Boise") or get_weather("New York")

3. get_earthquake_data(region: str = "all", min_magnitude: float = 4.5) -> str
   - Gets recent earthquake data from USGS
   - Example: get_earthquake_data("California", 4.0)

4. search_arxiv(query: str, max_results: int = 3) -> str
   - Searches for research papers on arXiv
   - Example: search_arxiv("transformers", 3)

5. get_currency_exchange(from_currency: str, to_currency: str, amount: float = 1.0) -> str
   - Converts currency amounts
   - Example: get_currency_exchange("USD", "EUR", 200)

To use a tool, respond with:
TOOL: tool_name
ARGS: {"arg1": "value1", "arg2": value2}

When you have the final answer, respond with:
FINAL ANSWER: [your answer here]
"""


# ============================================================================
# INLINE OPENROUTER CLIENT (from agent/openrouter.py)
# ============================================================================

class OpenRouterClient:
    """Simple client for OpenRouter API."""
    
    def __init__(self, api_key: str = None, model: str = "xiaomi/mimo-v2-flash:free"):
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not found.")
        
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def chat(self, messages, temperature: float = 0.7, max_tokens: int = 2000) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "Smart Utility ReAct Agent"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            response.raise_for_status()
            data = response.json()
            
            assistant_message = data["choices"][0]["message"]["content"]
            return assistant_message
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter API error: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected API response format: {str(e)}")


# ============================================================================
# INLINE REACT AGENT (from agent/agent.py)
# ============================================================================

class ReActAgent:
    """ReAct agent implementation."""
    
    def __init__(self, client: OpenRouterClient, max_iterations: int = 10, verbose: bool = True):
        self.client = client
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        return f"""You are a helpful assistant that uses a ReAct (Reason + Act + Observe) approach to answer questions.

{get_tool_descriptions()}

Instructions:
1. REASON about the user's question and what information you need
2. If you need to use a tool, respond with:
   TOOL: tool_name
   ARGS: {{"arg1": "value1", "arg2": value2}}
   
3. After using a tool, you will receive an OBSERVATION
4. Continue reasoning and using tools as needed
5. When you have enough information, provide the FINAL ANSWER:
   FINAL ANSWER: [your complete answer here]

Important:
- Use tools ONE AT A TIME
- Think step by step
- Show your reasoning before each action
- Be precise with tool arguments (use correct types: strings in quotes, numbers without quotes)
- When doing calculations with percentages, use the calculator tool
- Always provide a FINAL ANSWER when you're done

Example flow:
User: What is 15% of 200?
Assistant: I need to calculate 15% of 200. I'll use the calculator.
TOOL: calculator
ARGS: {{"expression": "200 * 0.15"}}
[You receive observation]
FINAL ANSWER: 15% of 200 is 30.
"""
    
    def _parse_response(self, response: str):
        """Parse LLM response to extract tool calls or final answers."""
        final_answer_match = re.search(r'FINAL ANSWER:\s*(.+?)(?:\n|$)', response, re.DOTALL | re.IGNORECASE)
        if final_answer_match:
            return None, None, final_answer_match.group(1).strip()
        
        tool_match = re.search(r'TOOL:\s*(\w+)', response, re.IGNORECASE)
        args_match = re.search(r'ARGS:\s*(\{.+?\})', response, re.DOTALL)
        
        if tool_match:
            tool_name = tool_match.group(1).strip()
            
            args = {}
            if args_match:
                try:
                    args = json.loads(args_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            return tool_name, args, None
        
        return None, None, None
    
    def _execute_tool(self, tool_name: str, args):
        """Execute a tool and return the observation."""
        if tool_name not in TOOLS:
            return f"ERROR: Unknown tool '{tool_name}'. Available tools: {', '.join(TOOLS.keys())}"
        
        tool_func = TOOLS[tool_name]
        
        try:
            observation = tool_func(**args)
            return observation
        except TypeError as e:
            return f"ERROR: Invalid arguments for tool '{tool_name}': {str(e)}"
        except Exception as e:
            return f"ERROR: Tool execution failed: {str(e)}"
    
    def run(self, user_query: str) -> str:
        """Run the ReAct loop."""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            try:
                response = self.client.chat(messages)
            except Exception as e:
                return f"Error communicating with LLM: {str(e)}"
            
            tool_name, tool_args, final_answer = self._parse_response(response)
            
            if final_answer:
                return final_answer
            
            if tool_name:
                observation = self._execute_tool(tool_name, tool_args)
                
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"OBSERVATION: {observation}"})
                
                continue
            
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user", 
                "content": "Please either use a tool (TOOL: ... ARGS: ...) or provide a FINAL ANSWER."
            })
        
        return f"I apologize, but I couldn't complete the task within {self.max_iterations} steps. Please try rephrasing your question."


# ============================================================================
# FASTAPI APP
# ============================================================================

def _build_agent() -> ReActAgent:
    """Create a ReActAgent instance."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set.")

    model = os.environ.get("OPENROUTER_MODEL")
    max_iterations = int(os.environ.get("AGENT_MAX_ITERATIONS", "10"))

    client = OpenRouterClient(api_key=api_key, model=model) if model else OpenRouterClient(api_key=api_key)
    return ReActAgent(client, max_iterations=max_iterations, verbose=False)


@lru_cache(maxsize=1)
def get_agent() -> ReActAgent:
    """Return a cached agent."""
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


# ============================================================================
# MODAL SETUP
# ============================================================================

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


@stub.function(image=image, secrets=[modal.Secret.from_name("smart-utility-secrets")])
@modal.asgi_app()
def fastapi_app():
    """Entrypoint for Modal."""
    import os
    # Verify API key is available
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable not set in Modal secret")
    return app


# ============================================================================
# LOCAL DEVELOPMENT
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))


# Minimal inline UI
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
    <div class=\"notice\">Capabilities: weather, currency, calculator, arXiv search, recent earthquakes. Each turn runs the ReAct loop to answer your single question.</div>
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
