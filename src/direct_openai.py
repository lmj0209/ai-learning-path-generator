"""
Direct OpenAI API handler to bypass any potential middleware issues.
"""
import os
import json
import requests
from typing import Dict, Any, List, Optional
from langsmith import traceable as langsmith_traceable

@langsmith_traceable(name="OpenAI_Direct_Call")
def generate_completion(
    prompt: str,
    system_message: str = "You are an expert educational AI assistant that specializes in creating personalized learning paths.",
    model: str = "gpt-3.5-turbo",
    temperature: float = 0.7,
    max_tokens: int = 1000,
    timeout: int = 120
) -> str:
    """
    Generate a completion using direct HTTP requests to OpenAI-compatible API.
    Supports both OpenAI and DeepSeek endpoints.

    Args:
        prompt: The user prompt
        system_message: Optional system message
        model: The model to use (e.g. gpt-4o-mini, deepseek-chat)
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate

    Returns:
        The generated text
    """
    # Determine provider based on available API keys
    deepseek_key = os.environ.get("DEEPSEEK_API_KEY")
    openai_key = os.environ.get("OPENAI_API_KEY")

    if deepseek_key:
        api_key = deepseek_key
        url = "https://api.deepseek.com/v1/chat/completions"
        provider_name = "DeepSeek"
        # Override model to deepseek-chat if caller passed an OpenAI model name
        if "gpt" in model.lower():
            model = os.environ.get("DEEPSEEK_MODEL", "deepseek-chat")
    else:
        api_key = openai_key
        url = "https://api.openai.com/v1/chat/completions"
        provider_name = "OpenAI"

    # Fallback to direct read from .env file if needed
    if not api_key or len(api_key) < 20:
        try:
            with open('.env', 'r') as f:
                for line in f:
                    if line.startswith('DEEPSEEK_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        url = "https://api.deepseek.com/v1/chat/completions"
                        provider_name = "DeepSeek"
                        break
                    elif line.startswith('OPENAI_API_KEY='):
                        api_key = line.strip().split('=', 1)[1]
                        url = "https://api.openai.com/v1/chat/completions"
                        provider_name = "OpenAI"
                        break
        except Exception as e:
            print(f"Error reading API key from file: {e}")

    if not api_key:
        raise ValueError("No API key found. Set DEEPSEEK_API_KEY or OPENAI_API_KEY in environment variables or .env file")

    print(f"Using {provider_name} API with key starting with: {api_key[:10]}..., model: {model}")
    
    # Request headers
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    # Request payload
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_message},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    print(f"Making direct API request to {provider_name}...")
    
    # Make the request
    try:
        response = requests.post(
            url, 
            headers=headers,
            json=payload,
            timeout=timeout
        )
        
        # Check if request was successful
        response.raise_for_status()
        
        # Parse response
        result = response.json()
        print(f"Received response from {provider_name} API")
        
        # Extract and return the generated text
        if "choices" in result and len(result["choices"]) > 0:
            return result["choices"][0]["message"]["content"]
        else:
            raise ValueError(f"Unexpected API response: {json.dumps(result)}")
            
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            status_code = e.response.status_code
            try:
                error_data = e.response.json()
                error_message = f"Error code: {status_code} - {json.dumps(error_data)}"
            except:
                error_message = f"Error code: {status_code} - {e.response.text}"
        else:
            error_message = str(e)
            
        raise ValueError(f"{provider_name} API request failed: {error_message}")
