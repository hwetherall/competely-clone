"""
Quick API Connection Test.

Run with: python tests/test_api_connection.py

Tests the OpenRouter API connection and shows what responses look like.
"""

import sys
import asyncio
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config import settings


async def test_api_connection():
    """Test API connection and print diagnostic info."""
    print("\n" + "=" * 70)
    print("  API Connection Test")
    print("=" * 70)
    
    # Print config info
    config_info = settings.get_config_info()
    print("\n  Configuration:")
    for key, value in config_info.items():
        print(f"    {key}: {value}")
    
    # Validate config
    errors = settings.validate_config(require_llm=True)
    if errors:
        print("\n  Configuration Errors:")
        for error in errors:
            print(f"    ERROR: {error}")
        return False
    
    print("\n  Configuration: OK")
    
    # Test API call
    print("\n" + "-" * 70)
    print("  Testing API Call...")
    print("-" * 70)
    
    import httpx
    
    url = f"{settings.OPENROUTER_BASE_URL}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/competely-clone",
        "X-Title": "CompetelyClone API Test",
    }
    
    # Test with the research model first
    for model_name, model_id in [
        ("Research Model", settings.RESEARCH_MODEL),
        ("Summarize Model", settings.SUMMARIZE_MODEL),
    ]:
        print(f"\n  Testing {model_name}: {model_id}")
        
        payload = {
            "model": model_id,
            "messages": [
                {"role": "user", "content": "Say 'API test successful' in exactly 3 words."}
            ],
            "temperature": 0.3,
            "max_tokens": 50,
        }
        
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(url, headers=headers, json=payload)
                
                print(f"    Status Code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"    Response Keys: {list(data.keys())}")
                    
                    if "error" in data:
                        print(f"    ERROR in response: {data['error']}")
                    elif "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0].get("message", {}).get("content", "")
                        print(f"    Response Content: {content[:100]}...")
                        print(f"    SUCCESS!")
                    else:
                        print(f"    Unexpected response structure:")
                        print(f"    {str(data)[:500]}")
                else:
                    print(f"    Error Response: {response.text[:200]}")
                    
        except Exception as e:
            print(f"    Exception: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 70)
    print("  API Test Complete")
    print("=" * 70)
    return True


if __name__ == "__main__":
    asyncio.run(test_api_connection())
