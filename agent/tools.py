"""
Tools for the ReAct Agent
Each tool is a Python function that returns a string observation.
"""

import requests
import json
from typing import Dict, Any


def calculator(expression: str) -> str:
    """
    Local calculator tool for arithmetic and percentage calculations.
    
    Args:
        expression: Mathematical expression to evaluate (e.g., "5 + 3", "100 * 0.15")
    
    Returns:
        String containing the calculation result
    """
    try:
        # Security note: eval is used here for educational purposes only
        # In production, use a proper math parser like ast.literal_eval or sympy
        result = eval(expression, {"__builtins__": {}}, {})
        return f"Calculation result: {expression} = {result}"
    except Exception as e:
        return f"Calculator error: {str(e)}"


def get_weather(location: str) -> str:
    """
    Weather API tool using Open-Meteo (free, no authentication required).
    
    Args:
        location: City name or coordinates (e.g., "Boise" or "43.6150,-116.2023")
    
    Returns:
        String containing current weather information
    """
    try:
        # First, geocode the location
        geocode_url = "https://geocoding-api.open-meteo.com/v1/search"
        geocode_params = {"name": location, "count": 1, "language": "en", "format": "json"}
        geocode_response = requests.get(geocode_url, params=geocode_params, timeout=10)
        geocode_data = geocode_response.json()
        
        if not geocode_data.get("results"):
            return f"Weather error: Could not find location '{location}'"
        
        lat = geocode_data["results"][0]["latitude"]
        lon = geocode_data["results"][0]["longitude"]
        place_name = geocode_data["results"][0]["name"]
        
        # Get weather data
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
    """
    Earthquake API tool using USGS Earthquake API (free, government data).
    
    Args:
        region: Geographic region (e.g., "California", "all")
        min_magnitude: Minimum earthquake magnitude to report
    
    Returns:
        String containing recent earthquake information
    """
    try:
        # USGS Earthquake API endpoint
        url = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        earthquakes = []
        for feature in data.get("features", []):
            props = feature.get("properties", {})
            mag = props.get("mag", 0)
            place = props.get("place", "Unknown")
            
            # Filter by magnitude
            if mag >= min_magnitude:
                # Filter by region if specified
                if region.lower() != "all" and region.lower() not in place.lower():
                    continue
                
                earthquakes.append({
                    "magnitude": mag,
                    "location": place,
                    "time": props.get("time")
                })
        
        if not earthquakes:
            return f"No earthquakes with magnitude >= {min_magnitude} found in the last 24 hours for region '{region}'"
        
        # Sort by magnitude (descending)
        earthquakes.sort(key=lambda x: x["magnitude"], reverse=True)
        
        # Format response
        result_lines = [f"Found {len(earthquakes)} earthquake(s) with magnitude >= {min_magnitude} in the last 24 hours:"]
        for eq in earthquakes[:5]:  # Limit to top 5
            result_lines.append(f"  - Magnitude {eq['magnitude']}: {eq['location']}")
        
        return "\n".join(result_lines)
    
    except Exception as e:
        return f"Earthquake API error: {str(e)}"


def search_arxiv(query: str, max_results: int = 3) -> str:
    """
    arXiv API tool for searching research papers.
    
    Args:
        query: Search query (e.g., "transformers", "neural networks")
        max_results: Maximum number of results to return
    
    Returns:
        String containing paper information
    """
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
        
        # Parse XML response (simplified parsing)
        content = response.text
        
        # Extract entries
        papers = []
        entries = content.split("<entry>")[1:]  # Skip first split (before first entry)
        
        for entry in entries[:max_results]:
            # Extract title
            title_start = entry.find("<title>") + 7
            title_end = entry.find("</title>")
            title = entry[title_start:title_end].strip().replace("\n", " ")
            
            # Extract summary
            summary_start = entry.find("<summary>") + 9
            summary_end = entry.find("</summary>")
            summary = entry[summary_start:summary_end].strip().replace("\n", " ")
            
            # Extract published date
            published_start = entry.find("<published>") + 11
            published_end = entry.find("</published>")
            published = entry[published_start:published_end][:10]  # Just the date
            
            papers.append({
                "title": title,
                "summary": summary[:200] + "..." if len(summary) > 200 else summary,
                "published": published
            })
        
        if not papers:
            return f"No papers found for query '{query}'"
        
        # Format response
        result_lines = [f"Found {len(papers)} recent paper(s) on '{query}':"]
        for i, paper in enumerate(papers, 1):
            result_lines.append(f"\n{i}. {paper['title']}")
            result_lines.append(f"   Published: {paper['published']}")
            result_lines.append(f"   Summary: {paper['summary']}")
        
        return "\n".join(result_lines)
    
    except Exception as e:
        return f"arXiv API error: {str(e)}"


def get_currency_exchange(from_currency: str, to_currency: str, amount: float = 1.0) -> str:
    """
    Currency exchange tool using Frankfurter API (free, no authentication required).
    
    Args:
        from_currency: Source currency code (e.g., "USD")
        to_currency: Target currency code (e.g., "EUR")
        amount: Amount to convert
    
    Returns:
        String containing exchange rate and converted amount
    """
    try:
        # Using Frankfurter API (free, no API key required, European Central Bank data)
        url = f"https://api.frankfurter.app/latest"
        params = {
            "from": from_currency.upper(),
            "to": to_currency.upper(),
            "amount": amount
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return f"Currency API error: HTTP {response.status_code}"
        
        data = response.json()
        
        # Extract the conversion result
        rates = data.get("rates", {})
        converted = rates.get(to_currency.upper())
        
        if converted is None:
            return f"Currency error: Could not find exchange rate for {from_currency} to {to_currency}"
        
        # Calculate the exchange rate
        rate = converted / amount
        
        return f"Exchange rate: 1 {from_currency.upper()} = {rate:.4f} {to_currency.upper()}. {amount} {from_currency.upper()} = {converted:.2f} {to_currency.upper()}"
    
    except Exception as e:
        return f"Currency API error: {str(e)}"


# Tool registry - maps tool names to functions
TOOLS = {
    "calculator": calculator,
    "get_weather": get_weather,
    "get_earthquake_data": get_earthquake_data,
    "search_arxiv": search_arxiv,
    "get_currency_exchange": get_currency_exchange
}


def get_tool_descriptions() -> str:
    """
    Returns a formatted string describing all available tools.
    This is used in the system prompt for the LLM.
    """
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
