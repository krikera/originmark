#!/usr/bin/env python3
"""
OriginMark OpenAI Auto-Signing Demo
Shows how to automatically sign all OpenAI API responses
"""

import os
import sys

# For development - add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import openai
    from originmark import enable_openai_autosigning
except ImportError:
    print(" Please install required packages:")
    print("   pip install openai")
    print("   pip install -e sdk/py-cli/")
    sys.exit(1)

def demo_auto_signing():
    """Demonstrate automatic signing of OpenAI responses"""
    
    print(" OriginMark OpenAI Auto-Signing Demo")
    print("=" * 50)
    
    # Check for OpenAI API key
    openai_key = os.getenv("OPENAI_API_KEY")
    if not openai_key:
        print(" Please set OPENAI_API_KEY environment variable")
        print("   export OPENAI_API_KEY='your-key-here'")
        return
    
    openai.api_key = openai_key
    
    # Optional: OriginMark API key for authenticated signing
    originmark_key = os.getenv("ORIGINMARK_API_KEY")
    
    # Enable auto-signing
    print("\n📝 Enabling OriginMark auto-signing...")
    signer = enable_openai_autosigning(
        api_url="http://localhost:8000",  # Update this for production
        api_key=originmark_key,
        author="Demo Application"
    )
    
    try:
        # Example 1: Simple completion
        print("\n Example 1: Simple Chat Completion")
        print("-" * 40)
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Write a haiku about digital signatures"}
            ],
            temperature=0.7
        )
        
        # Get the AI response
        ai_text = response.choices[0].message.content
        print(f"AI Response:\n{ai_text}\n")
        
        # Get the signature
        signature = signer.get_signature_for_response(response)
        if signature:
            print(" Response was automatically signed!")
            print(f"   Signature ID: {signature['id']}")
            print(f"   Content Hash: {signature['content_hash'][:32]}...")
            print(f"   Timestamp: {signature['timestamp']}")
            print(f"   Verify at: http://localhost:8000/verify?id={signature['id']}")
        else:
            print(" Auto-signing failed")
        
        # Example 2: Multi-turn conversation
        print("\n\n Example 2: Multi-turn Conversation")
        print("-" * 40)
        
        messages = [
            {"role": "system", "content": "You are an expert on blockchain technology."},
            {"role": "user", "content": "What is proof of work?"},
        ]
        
        response2 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages,
            max_tokens=150
        )
        
        answer = response2.choices[0].message.content
        print(f"AI Response:\n{answer[:100]}...\n")
        
        # Each response is individually signed
        signature2 = signer.get_signature_for_response(response2)
        if signature2:
            print(" Second response also auto-signed!")
            print(f"   Signature ID: {signature2['id']}")
        
        # Example 3: Disable and re-enable
        print("\n\n Example 3: Toggling Auto-Signing")
        print("-" * 40)
        
        # Disable auto-signing
        print("Disabling auto-signing...")
        signer.disable()
        
        response3 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "This won't be signed"}],
            max_tokens=50
        )
        
        signature3 = signer.get_signature_for_response(response3)
        print(f"Signature after disabling: {signature3}")  # Should be None
        
        # Re-enable
        print("\nRe-enabling auto-signing...")
        signer.enable()
        
        response4 = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "This will be signed again"}],
            max_tokens=50
        )
        
        signature4 = signer.get_signature_for_response(response4)
        print(f" Auto-signing re-enabled: {signature4['id'] if signature4 else 'Failed'}")
        
    except openai.error.OpenAIError as e:
        print(f"\n OpenAI API Error: {e}")
        print("   Check your API key and network connection")
    except Exception as e:
        print(f"\n Error: {e}")
    
    print("\n\n Demo completed!")

def verify_signature(signature_id):
    """Verify a signature using the OriginMark API"""
    import requests
    
    print(f"\n🔍 Verifying signature {signature_id}...")
    
    try:
        response = requests.get(f"http://localhost:8000/signatures/{signature_id}")
        if response.status_code == 200:
            data = response.json()
            print(" Signature verified!")
            print(f"   Content Hash: {data['content_hash']}")
            print(f"   Timestamp: {data['timestamp']}")
            print(f"   Metadata: {data['metadata']}")
        else:
            print(f" Verification failed: {response.status_code}")
    except Exception as e:
        print(f" Error verifying: {e}")

if __name__ == "__main__":
    # Run the demo
    demo_auto_signing()
    
    # Optional: Verify a specific signature
    if len(sys.argv) > 1 and sys.argv[1] == "--verify":
        if len(sys.argv) > 2:
            verify_signature(sys.argv[2])
        else:
            print("Usage: python openai_autosign_demo.py --verify <signature_id>") 