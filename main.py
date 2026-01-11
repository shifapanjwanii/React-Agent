"""
Main CLI Interface for the Smart Utility ReAct Agent
"""

import sys
import os
from dotenv import load_dotenv
from agent.openrouter import OpenRouterClient
from agent.agent import ReActAgent

# Load environment variables from .env file
load_dotenv()


def print_banner():
    """Print a welcome banner."""
    banner = """
╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║           Smart Utility ReAct Agent                           ║
║           A from-scratch implementation of ReAct              ║
║           (Reason + Act + Observe)                            ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝

Available Tools:
  • Calculator - Arithmetic and percentage calculations
  • Weather API - Current weather information
  • Earthquake Data - Recent earthquake information from USGS
  • arXiv Search - Research paper search
  • Currency Exchange - Currency conversion rates

Type 'exit' or 'quit' to end the session.
Type 'examples' to see example questions.
"""
    print(banner)


def print_examples():
    """Print example questions."""
    examples = """
Example Questions:

1. "If it's 15% colder tomorrow than today in Boise, what will the temperature be?"
   
2. "Are there any recent earthquakes near California with magnitude above 4?"
   
3. "Find a recent paper on transformers and summarize it briefly"
   
4. "Convert 200 USD to EUR and tell me if it's enough for a weekend trip"

5. "What's the weather like in New York and Paris?"

6. "Calculate 15% tip on a $87.50 restaurant bill"

7. "Find papers on neural networks published recently"

8. "Check for earthquakes in Japan with magnitude over 5"
"""
    print(examples)


def main():
    """
    Main CLI loop.
    """
    print_banner()
    
    # Check for API key
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("\n❌ ERROR: OPENROUTER_API_KEY environment variable not set.")
        print("\nPlease set your OpenRouter API key:")
        print("  export OPENROUTER_API_KEY='your-api-key-here'")
        print("\nGet your API key at: https://openrouter.ai/keys")
        sys.exit(1)
    
    # Initialize the agent
    try:
        # You can override the default model with environment variable: OPENROUTER_MODEL
        # Or pass model parameter: OpenRouterClient(api_key=api_key, model="openai/gpt-4-turbo")
        model = os.environ.get("OPENROUTER_MODEL")
        if model:
            client = OpenRouterClient(api_key=api_key, model=model)
        else:
            client = OpenRouterClient(api_key=api_key)
        agent = ReActAgent(client, max_iterations=10, verbose=True)
        print(f"\n✓ Agent initialized successfully with model: {client.model}\n")
    except Exception as e:
        print(f"\n❌ ERROR: Failed to initialize agent: {str(e)}")
        sys.exit(1)
    
    # Main interaction loop
    while True:
        try:
            # Get user input
            user_input = input("\n🤔 Your question: ").strip()
            
            # Check for exit commands
            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye! Thank you for using Smart Utility ReAct Agent.")
                break
            
            # Check for examples command
            if user_input.lower() == 'examples':
                print_examples()
                continue
            
            # Skip empty input
            if not user_input:
                continue
            
            # Run the agent
            try:
                answer = agent.run(user_input)
                print(f"\n{'='*60}")
                print(f"💡 FINAL ANSWER:")
                print(f"{'='*60}")
                print(f"\n{answer}\n")
            except KeyboardInterrupt:
                print("\n\n⚠️  Interrupted by user.")
                continue
            except Exception as e:
                print(f"\n❌ ERROR: {str(e)}")
                continue
        
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye! Thank you for using Smart Utility ReAct Agent.")
            break
        except EOFError:
            print("\n\n👋 Goodbye! Thank you for using Smart Utility ReAct Agent.")
            break


if __name__ == "__main__":
    main()
