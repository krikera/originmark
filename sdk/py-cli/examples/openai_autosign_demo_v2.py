#!/usr/bin/env python3
"""
OriginMark OpenAI Modern Auto-Signing Demo
Demonstrates the latest OpenAI integration with automatic content signing
"""

import os
import sys
import time
from typing import List, Dict, Any

# Add the SDK to path for demo
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    import openai
    from originmark.openai_plugin_v2 import (
        OpenAIAutoSignerV2, 
        AutoSignConfig, 
        enable_openai_autosigning
    )
    print(" OriginMark OpenAI v2 plugin loaded successfully")
except ImportError as e:
    print(f" Import error: {e}")
    print("Make sure to install: pip install openai requests")
    sys.exit(1)

def demo_basic_usage():
    """Demo 1: Basic auto-signing usage"""
    print("\n" + "="*60)
    print(" DEMO 1: Basic Auto-Signing with Modern OpenAI API")
    print("="*60)
    
    # Configure OpenAI (you'll need to set your API key)
    openai.api_key = os.getenv("OPENAI_API_KEY")
    if not openai.api_key:
        print("  OPENAI_API_KEY not set. Showing mock demo...")
        # Create mock signer for demo
        signer = OpenAIAutoSignerV2(AutoSignConfig(
            author="Demo User",
            debug=True
        ))
        print(" Mock signer created for demonstration")
        return signer
    
    # Enable auto-signing with simple configuration
    signer = enable_openai_autosigning(
        originmark_api_url="http://localhost:8000",
        author="Demo User",
        debug=True
    )
    
    try:
        print("📝 Making OpenAI API call...")
        
        # Try both legacy and modern API patterns
        try:
            # Modern OpenAI v1.x client
            from openai import OpenAI
            client = OpenAI()
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Write a short poem about AI and creativity."}
                ],
                max_tokens=100
            )
            content = response.choices[0].message.content
            
        except ImportError:
            # Fallback to legacy API
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": "Write a short poem about AI and creativity."}
                ],
                max_tokens=100
            )
            content = response.choices[0].message.content
        
        print(f"\n Generated Content:")
        print(f"'{content[:100]}...'")
        
        # Get signature (works with both API styles)
        signature = signer.get_signature_for_response(response)
        
        if signature:
            print(f"\n Automatic Signature:")
            print(f"   ID: {signature['id']}")
            print(f"   Hash: {signature['content_hash'][:16]}...")
            print(f"   Author: {signature['metadata']['author']}")
            print(f"   Model: {signature['metadata']['model_used']}")
        else:
            print(" No signature found")
            
    except Exception as e:
        print(f" Error: {e}")
    finally:
        signer.disable()
    
    return signer

def demo_advanced_configuration():
    """Demo 2: Advanced configuration and context manager"""
    print("\n" + "="*60)
    print(" DEMO 2: Advanced Configuration & Context Manager")
    print("="*60)
    
    # Create advanced configuration
    config = AutoSignConfig(
        originmark_api_url="http://localhost:8000",
        author="Advanced Demo User",
        auto_sign=True,
        min_content_length=20,
        include_metadata=True,
        debug=True,
        timeout=10.0
    )
    
    # Use as context manager for automatic cleanup
    with OpenAIAutoSignerV2(config) as signer:
        print(" Auto-signer enabled with advanced config")
        print(f"   Min content length: {config.min_content_length}")
        print(f"   Timeout: {config.timeout}s")
        print(f"   Debug mode: {config.debug}")
        
        # Simulate signing without OpenAI call
        test_content = "This is a test AI-generated content for demonstration purposes."
        print(f"\n📝 Test content: '{test_content}'")
        
        # Manual signing for demo (simulates what happens automatically)
        test_metadata = {
            "author": config.author,
            "model_used": "gpt-3.5-turbo",
            "ai_generated": True
        }
        
        signature = signer._sign_with_api(test_content, test_metadata)
        
        if signature:
            print(f"\n Manual Signature Demo:")
            print(f"   ID: {signature['id']}")
            print(f"   Content Hash: {signature['content_hash'][:16]}...")
            print(f"   Timestamp: {signature['timestamp']}")
        else:
            print("📝 Signature would be created when API is available")
    
    print(" Auto-signer automatically disabled (context manager)")

def demo_error_handling():
    """Demo 3: Error handling and resilience"""
    print("\n" + "="*60)
    print(" DEMO 3: Error Handling & Resilience")  
    print("="*60)
    
    # Test with invalid API URL
    config = AutoSignConfig(
        originmark_api_url="http://invalid-url:9999",
        author="Error Test User",
        debug=True,
        timeout=2.0  # Short timeout for demo
    )
    
    signer = OpenAIAutoSignerV2(config)
    
    try:
        print(" Testing with invalid API URL...")
        signer.enable()
        
        # This should handle errors gracefully
        test_result = signer._sign_with_api(
            content="Test content for error handling",
            metadata={"author": "Test", "model_used": "test-model"}
        )
        
        if test_result is None:
            print(" Error handled gracefully - no signature returned")
        else:
            print(f" Unexpected success: {test_result}")
            
    except Exception as e:
        print(f" Exception caught and handled: {e}")
    finally:
        signer.disable()

def demo_signature_verification():
    """Demo 4: Signature verification workflow"""
    print("\n" + "="*60)
    print(" DEMO 4: Signature Verification Workflow")
    print("="*60)
    
    signer = OpenAIAutoSignerV2(AutoSignConfig(
        author="Verification Demo",
        debug=True
    ))
    
    try:
        signer.enable()
        
        # Simulate a signed response
        class MockResponse:
            def __init__(self):
                self.choices = [type('Choice', (), {
                    'message': type('Message', (), {
                        'content': 'This is AI-generated content about machine learning.'
                    })()
                })()]
        
        mock_response = MockResponse()
        
        # Simulate attaching signature
        signature_data = {
            'id': 'demo-signature-123',
            'content_hash': 'abc123def456...',
            'author': 'Verification Demo',
            'timestamp': '2025-01-28T10:30:00Z',
            'metadata': {
                'model_used': 'gpt-3.5-turbo',
                'ai_generated': True
            }
        }
        
        signer._attach_signature_to_response(mock_response, signature_data)
        
        # Verify signature is attached
        retrieved_sig = signer.get_signature_for_response(mock_response)
        
        if retrieved_sig:
            print(" Signature verification workflow:")
            print(f"   Content: '{mock_response.choices[0].message.content[:50]}...'")
            print(f"   Signature ID: {retrieved_sig['id']}")
            print(f"   Author: {retrieved_sig['author']}")
            print(f"   Model: {retrieved_sig['metadata']['model_used']}")
            print(f"   AI Generated: {retrieved_sig['metadata']['ai_generated']}")
        else:
            print(" Signature not found")
            
    finally:
        signer.disable()

def demo_production_patterns():
    """Demo 5: Production-ready patterns"""
    print("\n" + "="*60)
    print(" DEMO 5: Production-Ready Patterns")
    print("="*60)
    
    # Configuration for different environments
    environments = {
        'development': {
            'url': 'http://localhost:8000',
            'debug': True,
            'timeout': 5.0
        },
        'staging': {
            'url': 'https://staging-api.originmark.com',
            'debug': False,
            'timeout': 10.0
        },
        'production': {
            'url': 'https://api.originmark.com',
            'debug': False,
            'timeout': 15.0
        }
    }
    
    env = os.getenv('ENVIRONMENT', 'development')
    env_config = environments.get(env, environments['development'])
    
    print(f" Environment: {env}")
    print(f"   API URL: {env_config['url']}")
    print(f"   Debug: {env_config['debug']}")
    print(f"   Timeout: {env_config['timeout']}s")
    
    # Production configuration
    config = AutoSignConfig(
        originmark_api_url=env_config['url'],
        author=os.getenv('ORIGINMARK_AUTHOR', 'Production App'),
        debug=env_config['debug'],
        timeout=env_config['timeout'],
        min_content_length=50,  # Only sign substantial content
        include_metadata=True
    )
    
    # Show configuration validation
    if config.validate():
        print(" Configuration is valid")
    else:
        print(" Configuration validation failed")
    
    # Thread safety demo
    import threading
    import time
    
    def worker_thread(thread_id):
        """Simulate multiple threads using the signer"""
        with OpenAIAutoSignerV2(config) as thread_signer:
            time.sleep(0.1)  # Simulate work
            print(f"   Thread {thread_id}: Signer enabled")
    
    print("\n🧵 Testing thread safety...")
    threads = []
    for i in range(3):
        t = threading.Thread(target=worker_thread, args=(i,))
        threads.append(t)
        t.start()
    
    for t in threads:
        t.join()
    
    print(" Thread safety test completed")

def main():
    """Run all demos"""
    print(" OriginMark OpenAI Auto-Signing Demo Suite v2.0")
    print("=" * 60)
    print("This demo shows the modern OpenAI integration with automatic")
    print("content signing for provenance and authenticity verification.")
    
    # Check if OriginMark API is running
    try:
        import requests
        response = requests.get("http://localhost:8000/", timeout=5)
        if response.status_code == 200:
            print(" OriginMark API is running")
        else:
            print("  OriginMark API responded with non-200 status")
    except Exception:
        print("  OriginMark API is not running at http://localhost:8000")
        print("   Start it with: cd api && python -m uvicorn main:app --reload")
    
    # Run demos
    try:
        demo_basic_usage()
        demo_advanced_configuration()
        demo_error_handling()
        demo_signature_verification()
        demo_production_patterns()
        
        print("\n" + "="*60)
        print("🎉 All demos completed successfully!")
        print("="*60)
        print("\n📖 Next Steps:")
        print("1. Set your OPENAI_API_KEY environment variable")
        print("2. Start the OriginMark API server")
        print("3. Try the basic usage example in your own code")
        print("4. Explore advanced configurations for production use")
        print("5. Check out the production patterns for deployment")
        
    except KeyboardInterrupt:
        print("\n Demo interrupted by user")
    except Exception as e:
        print(f"\n Demo failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
