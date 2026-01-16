#!/usr/bin/env python3
"""Check if Anthropic API key is configured."""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

api_key = os.getenv('ANTHROPIC_API_KEY')

if not api_key:
    print("❌ ANTHROPIC_API_KEY not set")
    print("\nPlease set it in .env file or as environment variable:")
    print("  export ANTHROPIC_API_KEY=your_key_here")
elif api_key == 'your_api_key_here':
    print("❌ ANTHROPIC_API_KEY still has default value")
    print("\nPlease edit .env file and replace with your actual API key")
else:
    print("✅ ANTHROPIC_API_KEY is configured")
    print(f"   Key starts with: {api_key[:15]}...")
