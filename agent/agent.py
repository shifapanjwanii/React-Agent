"""
ReAct Agent Implementation
This is the core ReAct (Reason + Act + Observe) loop.
"""

import re
import json
from typing import List, Dict, Tuple, Optional
from .openrouter import OpenRouterClient
from .tools import TOOLS, get_tool_descriptions


class ReActAgent:
    """
    A ReAct agent that reasons about tasks, takes actions using tools,
    and observes the results until it reaches a final answer.
    """
    
    def __init__(self, client: OpenRouterClient, max_iterations: int = 10, verbose: bool = True):
        """
        Initialize the ReAct agent.
        
        Args:
            client: OpenRouter client for LLM inference
            max_iterations: Maximum number of reasoning iterations
            verbose: Whether to print reasoning steps
        """
        self.client = client
        self.max_iterations = max_iterations
        self.verbose = verbose
        self.system_prompt = self._create_system_prompt()
    
    def _create_system_prompt(self) -> str:
        """
        Creates the system prompt that instructs the LLM how to behave as a ReAct agent.
        """
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
    
    def _parse_response(self, response: str) -> Tuple[Optional[str], Optional[Dict], Optional[str]]:
        """
        Parse the LLM response to extract tool calls or final answers.
        
        Returns:
            (tool_name, tool_args, final_answer) tuple
            - If tool call: (tool_name, args_dict, None)
            - If final answer: (None, None, answer_string)
            - If neither: (None, None, None)
        """
        # Check for final answer
        final_answer_match = re.search(r'FINAL ANSWER:\s*(.+?)(?:\n|$)', response, re.DOTALL | re.IGNORECASE)
        if final_answer_match:
            return None, None, final_answer_match.group(1).strip()
        
        # Check for tool call
        tool_match = re.search(r'TOOL:\s*(\w+)', response, re.IGNORECASE)
        args_match = re.search(r'ARGS:\s*(\{.+?\})', response, re.DOTALL)
        
        if tool_match:
            tool_name = tool_match.group(1).strip()
            
            # Parse arguments
            args = {}
            if args_match:
                try:
                    args = json.loads(args_match.group(1))
                except json.JSONDecodeError:
                    # If JSON parsing fails, return empty args
                    pass
            
            return tool_name, args, None
        
        return None, None, None
    
    def _execute_tool(self, tool_name: str, args: Dict) -> str:
        """
        Execute a tool and return the observation.
        
        Args:
            tool_name: Name of the tool to execute
            args: Dictionary of arguments for the tool
        
        Returns:
            Observation string from tool execution
        """
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
        """
        Run the ReAct loop to answer the user's query.
        
        This is the core loop:
        1. Initialize messages with system prompt and user query
        2. Loop:
            a. Call LLM with message history
            b. Parse response for tool call or final answer
            c. If tool call: execute tool, add observation to messages
            d. If final answer: break and return answer
        3. Return final answer or timeout message
        
        Args:
            user_query: The user's question
        
        Returns:
            The final answer string
        """
        # Initialize message history
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_query}
        ]
        
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Starting ReAct Agent")
            print(f"{'='*60}")
            print(f"\nUser Query: {user_query}\n")
        
        # Main ReAct loop
        iteration = 0
        while iteration < self.max_iterations:
            iteration += 1
            
            if self.verbose:
                print(f"\n--- Iteration {iteration} ---")
            
            # Step 1: Call LLM with current message history
            try:
                response = self.client.chat(messages)
            except Exception as e:
                return f"Error communicating with LLM: {str(e)}"
            
            if self.verbose:
                print(f"\nLLM Response:\n{response}")
            
            # Step 2: Parse the response
            tool_name, tool_args, final_answer = self._parse_response(response)
            
            # Step 3: Check if we have a final answer
            if final_answer:
                if self.verbose:
                    print(f"\n{'='*60}")
                    print(f"Final Answer Reached (Iteration {iteration})")
                    print(f"{'='*60}")
                return final_answer
            
            # Step 4: Check if we have a tool call
            if tool_name:
                if self.verbose:
                    print(f"\nTool Call: {tool_name}")
                    print(f"Arguments: {json.dumps(tool_args, indent=2)}")
                
                # Execute the tool
                observation = self._execute_tool(tool_name, tool_args)
                
                if self.verbose:
                    print(f"\nObservation:\n{observation}")
                
                # Add assistant response and observation to message history
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"OBSERVATION: {observation}"})
                
                # Continue to next iteration
                continue
            
            # Step 5: If no tool call and no final answer, the LLM might be confused
            # Add the response and prompt it to continue
            messages.append({"role": "assistant", "content": response})
            messages.append({
                "role": "user", 
                "content": "Please either use a tool (TOOL: ... ARGS: ...) or provide a FINAL ANSWER."
            })
        
        # Max iterations reached
        if self.verbose:
            print(f"\n{'='*60}")
            print(f"Max Iterations Reached ({self.max_iterations})")
            print(f"{'='*60}")
        
        return f"I apologize, but I couldn't complete the task within {self.max_iterations} steps. Please try rephrasing your question or breaking it into smaller parts."
