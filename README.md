# Smart Utility ReAct Agent

A **from-scratch implementation** of a ReAct (Reason + Act + Observe) agent for a course assignment. This project demonstrates the core ReAct loop without using any agent frameworks like LangChain, CrewAI, or AutoGen.

## 📚 What is a ReAct Agent?

**ReAct** stands for **Reason + Act + Observe**. It's a paradigm for building AI agents that:

1. **Reason** - The agent thinks about the task and decides what action to take
2. **Act** - The agent executes an action (typically calling a tool or function)
3. **Observe** - The agent observes the result of the action
4. **Repeat** - The cycle continues until the agent has enough information to provide a final answer

This approach allows language models to interact with external tools and APIs to gather information, perform calculations, and complete complex tasks that require multiple steps.

### Why ReAct?

Traditional language models can only work with information they were trained on. ReAct agents extend their capabilities by:
- Breaking down complex problems into smaller steps
- Using external tools to access real-time data
- Showing their reasoning process (making them more transparent and debuggable)
- Iteratively refining their approach based on observations

## 🎯 Project Overview

This project implements a ReAct agent that can answer user questions by:
- Analyzing the question and planning which tools to use
- Calling tools one at a time (weather APIs, calculators, research databases, etc.)
- Combining information from multiple sources
- Providing a comprehensive final answer

### Key Features

- ✅ **No frameworks** - Built from scratch using only basic libraries
- ✅ **Explicit ReAct loop** - Clear, readable implementation of the reason-act-observe cycle
- ✅ **Multiple tools** - 5 different tools for various tasks
- ✅ **OpenRouter integration** - Uses OpenRouter API for LLM inference
- ✅ **CLI interface** - Simple command-line interface for interaction
- ✅ **Transparent reasoning** - Shows the agent's thought process at each step

## 🏗️ Architecture

### Project Structure

```
Smart Utility/
├── agent/
│   ├── __init__.py        # Package initialization
│   ├── agent.py           # Core ReAct loop implementation
│   ├── tools.py           # Tool definitions and implementations
│   └── openrouter.py      # OpenRouter API client
├── main.py                # CLI entry point
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

### How It Works

#### 1. The ReAct Loop (`agent/agent.py`)

```python
messages = [system_prompt, user_query]

while iteration < max_iterations:
    # Step 1: Call LLM with message history
    response = llm.chat(messages)
    
    # Step 2: Parse response (tool call or final answer?)
    tool_name, args, final_answer = parse_response(response)
    
    # Step 3: If final answer, we're done!
    if final_answer:
        return final_answer
    
    # Step 4: If tool call, execute it
    if tool_name:
        observation = execute_tool(tool_name, args)
        
        # Step 5: Add observation to messages and continue
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": f"OBSERVATION: {observation}"})
```

This loop continues until:
- The agent provides a `FINAL ANSWER`, or
- Maximum iterations are reached

#### 2. Tools (`agent/tools.py`)

Each tool is a simple Python function that:
- Takes specific arguments
- Performs an action (calculation, API call, etc.)
- Returns a string observation

Example:
```python
def calculator(expression: str) -> str:
    result = eval(expression)
    return f"Calculation result: {expression} = {result}"
```

#### 3. OpenRouter Client (`agent/openrouter.py`)

Handles communication with the OpenRouter API:
- Sends message history
- Receives LLM responses
- Manages API authentication

## 🛠️ Available Tools

### 1. **Calculator** (Local)
- Performs arithmetic calculations and percentage operations
- Example: `calculator("100 * 0.15")` → `"Calculation result: 100 * 0.15 = 15.0"`

### 2. **Weather API** (HTTP - Open-Meteo)
- Gets current weather information for any location
- Free API, no authentication required
- Example: `get_weather("Boise")` → `"Weather in Boise: Temperature: 42°F, Humidity: 65%"`

### 3. **Earthquake Data API** (HTTP - USGS)
- Retrieves recent earthquake information from the US Geological Survey
- Government data, free and reliable
- Example: `get_earthquake_data("California", 4.5)` → Returns earthquakes above magnitude 4.5

### 4. **arXiv Search API** (HTTP - arXiv.org)
- Searches academic papers on arXiv
- Returns paper titles, summaries, and publication dates
- Example: `search_arxiv("transformers", 3)` → Returns 3 recent papers on transformers

### 5. **Currency Exchange API** (HTTP - exchangerate.host)
- Converts between currencies using real-time exchange rates
- Example: `get_currency_exchange("USD", "EUR", 200)` → Returns conversion result

## 🚀 Setup and Installation

### Prerequisites

- Python 3.8 or higher
- OpenRouter API key (get one at [openrouter.ai/keys](https://openrouter.ai/keys))

### Installation Steps

1. **Clone or download the project**
   ```bash
   cd "/Users/shifapanjwani/Documents/Smart Utility"
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up your OpenRouter API key**
   ```bash
   export OPENROUTER_API_KEY='your-api-key-here'
   ```
   
   Or add it to your shell profile (~/.zshrc, ~/.bashrc):
   ```bash
   echo 'export OPENROUTER_API_KEY="your-api-key-here"' >> ~/.zshrc
   source ~/.zshrc
   ```

4. **Run the agent**
   ```bash
   python main.py
   ```

## 💡 Usage Examples

### Example 1: Multi-step Calculation with Weather

**Question:** "If it's 15% colder tomorrow than today in Boise, what will the temperature be?"

**Agent Process:**
1. **Reason:** Need to get current temperature in Boise
2. **Act:** Call `get_weather("Boise")`
3. **Observe:** Current temperature is 42°F
4. **Reason:** Need to calculate 15% decrease
5. **Act:** Call `calculator("42 * 0.15")`
6. **Observe:** 15% of 42 is 6.3
7. **Act:** Call `calculator("42 - 6.3")`
8. **Observe:** Result is 35.7
9. **Final Answer:** "If it's 15% colder tomorrow, the temperature in Boise will be approximately 35.7°F"

### Example 2: Research Query

**Question:** "Find a recent paper on transformers and summarize it briefly"

**Agent Process:**
1. **Reason:** Need to search arXiv for papers on transformers
2. **Act:** Call `search_arxiv("transformers", 3)`
3. **Observe:** [Returns 3 recent papers with titles and summaries]
4. **Final Answer:** [Provides summary of the most relevant paper]

### Example 3: Earthquake Information

**Question:** "Are there any recent earthquakes near California with magnitude above 4?"

**Agent Process:**
1. **Reason:** Need earthquake data for California
2. **Act:** Call `get_earthquake_data("California", 4.0)`
3. **Observe:** [Returns list of earthquakes]
4. **Final Answer:** [Provides information about recent earthquakes]

## 🧪 Testing the Agent

Try these questions to test different capabilities:

### Basic Calculations
- "What's 15% tip on a $87.50 bill?"
- "Calculate the square root of 144"

### Weather Queries
- "What's the weather in New York?"
- "Compare temperatures in London and Tokyo"

### Research
- "Find recent papers on neural networks"
- "Search for articles about climate change on arXiv"

### Earthquakes
- "Are there any strong earthquakes today?"
- "Check for earthquakes in Japan"

### Currency
- "Convert 500 USD to EUR"
- "How much is 1000 GBP in JPY?"

### Complex Multi-step Queries
- "If a paper costs 20 EUR and I have 25 USD, can I afford it?"
- "Calculate 20% of the current temperature in Seattle"

## 🎓 Educational Value

This project demonstrates:

### 1. **Core AI Agent Concepts**
- Message-based conversation history
- Tool/function calling paradigm
- Iterative problem solving
- State management across multiple steps

### 2. **LLM Integration**
- API communication with language models
- Prompt engineering for specific behaviors
- Response parsing and structured output

### 3. **Software Engineering**
- Clean code architecture
- Separation of concerns (tools, agent logic, API client)
- Error handling and edge cases
- Modular, extensible design

### 4. **Practical Skills**
- Working with REST APIs
- HTTP requests and JSON parsing
- Environment variables and configuration
- CLI development

## 🔧 Customization

### Adding New Tools

To add a new tool:

1. **Define the function in `agent/tools.py`:**
   ```python
   def my_new_tool(param1: str, param2: int) -> str:
       # Tool implementation
       result = do_something(param1, param2)
       return f"Result: {result}"
   ```

2. **Add it to the TOOLS registry:**
   ```python
   TOOLS = {
       # ... existing tools
       "my_new_tool": my_new_tool
   }
   ```

3. **Update the tool descriptions in `get_tool_descriptions()`:**
   ```python
   def get_tool_descriptions() -> str:
       return """
       ...existing tools...
       
       6. my_new_tool(param1: str, param2: int) -> str
          - Description of what it does
          - Example: my_new_tool("example", 42)
       """
   ```

### Changing the LLM Model

Edit the model in `main.py`:
```python
client = OpenRouterClient(api_key=api_key, model="anthropic/claude-3-opus")
```

Available models on OpenRouter:
- `anthropic/claude-3.5-sonnet` (default, balanced)
- `anthropic/claude-3-opus` (most capable)
- `openai/gpt-4-turbo` (OpenAI's latest)
- See [openrouter.ai/docs](https://openrouter.ai/docs) for more options

### Adjusting Agent Behavior

In `main.py`, modify agent parameters:
```python
agent = ReActAgent(
    client, 
    max_iterations=15,  # Increase for more complex tasks
    verbose=True        # Set to False to hide reasoning steps
)
```

## 📝 Implementation Notes

### Why No Frameworks?

This is an educational project designed to teach the fundamentals of agent design. By implementing everything from scratch:
- You understand exactly how each component works
- There's no "magic" or abstraction hiding the core logic
- The code is simple, readable, and instructional
- You can easily modify and extend it

### Design Decisions

1. **Simple tool protocol** - Tools return strings, not complex objects
2. **Explicit loop** - The while loop is clearly visible and understandable
3. **Message-based** - Uses the standard chat message format
4. **One tool at a time** - Simpler to debug and understand
5. **Verbose mode** - Shows reasoning process for learning purposes

### Limitations

This is a teaching implementation. Production agents would need:
- Better error recovery and retry logic
- Parallel tool execution for efficiency
- More sophisticated prompt engineering
- Tool result caching
- User authentication and rate limiting
- Streaming responses for better UX

## 🐛 Troubleshooting

### "OpenRouter API key not found"
- Make sure you've set the `OPENROUTER_API_KEY` environment variable
- Check that it's set in the current terminal session: `echo $OPENROUTER_API_KEY`

### "Max iterations reached"
- The agent couldn't complete the task in the allowed iterations
- Try rephrasing your question to be more specific
- Check if the required tools are available

### API Errors
- Check your internet connection
- Verify the API is accessible (try visiting the API URL in a browser)
- Some APIs may have rate limits

### Tool Execution Errors
- Check the error message in the OBSERVATION
- Verify tool arguments are correct
- Some tools (like calculator) have security restrictions

## 📚 Further Learning

### Recommended Resources

- **ReAct Paper**: "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022)
- **OpenRouter Docs**: [openrouter.ai/docs](https://openrouter.ai/docs)
- **Prompt Engineering Guide**: [promptingguide.ai](https://www.promptingguide.ai)

### Next Steps

To extend this project:
1. Add more tools (database queries, file operations, etc.)
2. Implement parallel tool execution
3. Add memory/context management for longer conversations
4. Build a web UI with streaming responses
5. Add multi-agent collaboration
6. Implement tool result validation and retry logic

## 📄 License

This is an educational project for course assignments. Feel free to use and modify for learning purposes.

## 🙏 Acknowledgments

- OpenRouter for accessible LLM API access
- Open-Meteo for free weather data
- USGS for earthquake data
- arXiv for academic paper access
- All the open-source APIs that make projects like this possible

---

**Built with ❤️ for learning AI agent fundamentals**
