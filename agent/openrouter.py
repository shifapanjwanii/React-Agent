"""
OpenRouter API Client
Handles communication with OpenRouter for LLM inference.
"""

import os
import requests
import json
from typing import List, Dict, Any


class OpenRouterClient:
    """
    Simple client for OpenRouter API.
    """
    
    def __init__(self, api_key: str = None, model: str = "xiaomi/mimo-v2-flash:free"):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key (reads from OPENROUTER_API_KEY env var if not provided)
            model: Model to use (default: Claude 3.5 Sonnet)
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Set OPENROUTER_API_KEY environment variable.")
        
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7, max_tokens: int = 2000) -> str:
        """
        Send a chat request to OpenRouter.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
        
        Returns:
            The assistant's response content as a string
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",  # Optional, for rankings
            "X-Title": "Smart Utility ReAct Agent"  # Optional, for rankings
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
            
            # Extract the assistant's message
            assistant_message = data["choices"][0]["message"]["content"]
            return assistant_message
        
        except requests.exceptions.RequestException as e:
            raise Exception(f"OpenRouter API error: {str(e)}")
        except (KeyError, IndexError) as e:
            raise Exception(f"Unexpected API response format: {str(e)}")
