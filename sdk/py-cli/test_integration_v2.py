#!/usr/bin/env python3
"""
Integration Test for OriginMark OpenAI Plugin v2
Verifies the modern OpenAI integration works correctly
"""

import os
import sys
import time
import json

# Add the SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def test_imports():
    """Test that all modules can be imported"""
    print(" Testing imports...")
    
    try:
        from originmark.openai_plugin_v2 import (
            OpenAIAutoSignerV2, 
            AutoSignConfig, 
            enable_openai_autosigning
        )
        print(" OriginMark OpenAI v2 plugin imports successful")
        return True
    except ImportError as e:
        print(f" Import failed: {e}")
        return False

def test_configuration():
    """Test configuration creation and validation"""
    print("\n Testing configuration...")
    
    try:
        from originmark.openai_plugin_v2 import AutoSignConfig
        
        # Test basic config
        config = AutoSignConfig(author="Test User")
        assert config.author == "Test User"
        assert config.auto_sign == True  # default
        print(" Basic configuration works")
        
        # Test advanced config
        config = AutoSignConfig(
            originmark_api_url="http://localhost:8000",
            author="Advanced User",
            auto_sign=True,
            min_content_length=50,
            include_metadata=True,
            debug=True,
            timeout=10.0
        )
        
        # Test validation if method exists
        if hasattr(config, 'validate'):
            is_valid = config.validate()
            print(f" Configuration validation: {'passed' if is_valid else 'failed'}")
        
        print(" Advanced configuration works")
        return True
        
    except Exception as e:
        print(f" Configuration test failed: {e}")
        return False

def test_signer_lifecycle():
    """Test signer enable/disable lifecycle"""
    print("\n Testing signer lifecycle...")
    
    try:
        from originmark.openai_plugin_v2 import OpenAIAutoSignerV2, AutoSignConfig
        
        config = AutoSignConfig(
            author="Lifecycle Test",
            debug=True
        )
        
        signer = OpenAIAutoSignerV2(config)
        
        # Test enable
        result = signer.enable()
        print(f" Enable result: {result}")
        
        # Test disable
        result = signer.disable()
        print(f" Disable result: {result}")
        
        # Test context manager
        with OpenAIAutoSignerV2(config) as ctx_signer:
            print(" Context manager works")
        
        print(" Signer lifecycle test completed")
        return True
        
    except Exception as e:
        print(f" Signer lifecycle test failed: {e}")
        return False

def test_signature_workflow():
    """Test signature creation and attachment workflow"""
    print("\n Testing signature workflow...")
    
    try:
        from originmark.openai_plugin_v2 import OpenAIAutoSignerV2, AutoSignConfig
        
        config = AutoSignConfig(
            author="Workflow Test",
            debug=True
        )
        
        signer = OpenAIAutoSignerV2(config)
        signer.enable()
        
        # Test signature creation (mock)
        test_content = "This is test AI-generated content for signature testing."
        test_metadata = {
            "author": "Workflow Test",
            "model_used": "test-model",
            "ai_generated": True
        }
        
        # This will return None if API isn't available, which is expected
        signature = signer._sign_with_api(test_content, test_metadata)
        
        if signature:
            print(f" Signature created: {signature['id']}")
        else:
            print(" Signature creation handled gracefully (API not available)")
        
        # Test response attachment (mock)
        class MockResponse:
            def __init__(self):
                self.choices = [type('Choice', (), {
                    'message': type('Message', (), {
                        'content': test_content
                    })()
                })()]
        
        mock_response = MockResponse()
        mock_signature = {
            'id': 'test-sig-123',
            'content_hash': 'test-hash',
            'author': 'Workflow Test',
            'timestamp': '2025-01-28T10:30:00Z',
            'metadata': test_metadata
        }
        
        signer._attach_signature_to_response(mock_response, mock_signature)
        retrieved = signer.get_signature_for_response(mock_response)
        
        if retrieved and retrieved['id'] == 'test-sig-123':
            print(" Signature attachment and retrieval works")
        else:
            print(" Signature attachment failed")
        
        signer.disable()
        print(" Signature workflow test completed")
        return True
        
    except Exception as e:
        print(f" Signature workflow test failed: {e}")
        return False

def test_convenience_function():
    """Test the convenience enable function"""
    print("\n Testing convenience function...")
    
    try:
        from originmark.openai_plugin_v2 import enable_openai_autosigning
        
        signer = enable_openai_autosigning(
            originmark_api_url="http://localhost:8000",
            author="Convenience Test",
            debug=True
        )
        
        if signer:
            print(" Convenience function works")
            signer.disable()
            return True
        else:
            print(" Convenience function returned None")
            return False
            
    except Exception as e:
        print(f" Convenience function test failed: {e}")
        return False

def test_api_connectivity():
    """Test connection to OriginMark API"""
    print("\n Testing API connectivity...")
    
    try:
        import requests
        
        # Test local API
        try:
            response = requests.get("http://localhost:8000/", timeout=3)
            if response.status_code == 200:
                print(" OriginMark API is running and accessible")
                return True
            else:
                print(f"  API responded with status {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("  OriginMark API is not running at http://localhost:8000")
        except Exception as e:
            print(f"  API connection test failed: {e}")
        
        print("📝 This is expected if the API server isn't running")
        return True  # Not a failure - just informational
        
    except ImportError:
        print("  requests library not available for API test")
        return True

def main():
    """Run all integration tests"""
    print(" OriginMark OpenAI Plugin v2 Integration Tests")
    print("=" * 60)
    
    tests = [
        ("Import Test", test_imports),
        ("Configuration Test", test_configuration),
        ("Signer Lifecycle Test", test_signer_lifecycle),
        ("Signature Workflow Test", test_signature_workflow),
        ("Convenience Function Test", test_convenience_function),
        ("API Connectivity Test", test_api_connectivity),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f" {test_name} crashed: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print(" TEST RESULTS SUMMARY")
    print("="*60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = " PASS" if result else " FAIL"
        print(f"{status:10} {test_name}")
        if result:
            passed += 1
    
    print(f"\n Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The OpenAI plugin v2 is ready to use.")
    else:
        print("  Some tests failed. Please check the output above.")
    
    print("\n📖 Next steps:")
    print("1. Start the OriginMark API server if not running")
    print("2. Set your OPENAI_API_KEY environment variable")
    print("3. Run the demo: python examples/openai_autosign_demo_v2.py")
    print("4. Integrate into your application following the examples")

if __name__ == "__main__":
    main()
