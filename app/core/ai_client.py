"""
AI Client Setup - Modular function to create AI client instances.
This abstraction allows easy switching between different AI providers
(Groq, OpenAI, Anthropic, etc.) by changing one function call.
"""

import os
from dotenv import load_dotenv
from groq import Groq

# Load environment variables
load_dotenv()

def get_ai_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY not found in environment variables.")
    return Groq(api_key=api_key)

def get_ai_model():
    """
    Returns an active, verified model from your Groq account.
    """
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
    
    # Ensure it only uses models from your verified account list
    valid_models = [
        "openai/gpt-oss-120b",
        "openai/gpt-oss-20b",
        "qwen/qwen3.8-27b",
        "groq/compound"
    ]
    
    if model not in valid_models:
        return "openai/gpt-oss-120b"
        
    return model