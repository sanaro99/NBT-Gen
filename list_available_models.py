import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("Error: No API key found. Set GEMINI_API_KEY or GOOGLE_API_KEY in your .env file")
    exit(1)

# Try multiple approaches to list models
print("Attempting to list available Gemini models...\n")

# Method 1: Using google-generativeai (if available)
try:
    import google.generativeai as genai
    genai.configure(api_key=api_key)
    
    print("Available Gemini models:")
    print("-" * 80)
    
    for model in genai.list_models():
        if 'generateContent' in model.supported_generation_methods:
            print(f"\nModel: {model.name}")
            print(f"  Display Name: {model.display_name}")
            print(f"  Supported Methods: {', '.join(model.supported_generation_methods)}")
    print("\n" + "-" * 80)
except ImportError:
    print("google-generativeai not installed. Trying alternative method...\n")
    
    # Method 2: Direct API call
    try:
        import requests
        
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        params = {"key": api_key}
        
        response = requests.get(url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            print("Available models:")
            print("-" * 80)
            
            for model in data.get('models', []):
                if 'generateContent' in model.get('supportedGenerationMethods', []):
                    print(f"\nModel: {model['name']}")
                    print(f"  Display Name: {model.get('displayName', 'N/A')}")
                    print(f"  Supported Methods: {', '.join(model.get('supportedGenerationMethods', []))}")
            print("\n" + "-" * 80)
        else:
            print(f"API Error: {response.status_code}")
            print(f"Response: {response.text}")
    except ImportError:
        print("requests not installed either.")
        print("\nInstall one of these packages:")
        print("  pip install google-generativeai")
        print("  pip install requests")

print("\nCommon working model names (use these if API call fails):")
print("  - models/gemini-1.5-pro")
print("  - models/gemini-1.5-flash")  
print("  - models/gemini-pro")
print("  - models/gemini-1.0-pro")
print("\nNote: Remove '-latest' suffix from model names!")
