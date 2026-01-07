import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai


def verify_simple():
    print("Testing simple Google Gemini API connection...")

    # Load API key from ~/.env
    env_path = Path.home() / ".env"
    load_dotenv(dotenv_path=env_path)
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("Error: GOOGLE_API_KEY not found in ~/.env")
        return

    client = genai.Client(api_key=api_key)
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite", contents="Say 'Hello, I am connected!'"
        )
        print(f"Response: {response.text}")
        print("API connection successful!")
    except Exception as e:
        print(f"API connection failed: {e}")


if __name__ == "__main__":
    verify_simple()
