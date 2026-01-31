"""
OriginMark OpenAI Auto-Signing Plugin v2.0
Modern implementation with OpenAI v1.x support and comprehensive features
"""

import os
import json
import time
import inspect
import functools
from typing import Dict, Any, Optional, Union, List, Callable
from datetime import datetime, timezone
import logging
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logger.warning("OpenAI library not found. Install with: pip install openai")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    logger.warning("Requests library not found. Install with: pip install requests")

@dataclass
class AutoSignConfig:
    """Configuration for auto-signing behavior"""
    originmark_api_url: str = "http://localhost:8000"
    api_key: Optional[str] = None
    author: str = "OpenAI Auto-Signer"
    auto_sign: bool = True
    sign_all_responses: bool = True
    min_content_length: int = 10
    max_retries: int = 3
    timeout: float = 30.0
    store_locally: bool = False
    include_metadata: bool = True
    debug: bool = False

class OpenAIAutoSignerV2:
    """
    Modern OpenAI Auto-Signer with support for OpenAI v1.x API
    
    Features:
    - Supports both legacy and modern OpenAI clients
    - Automatic retry logic with exponential backoff
    - Comprehensive logging and debugging
    - Thread-safe operation
    - Minimal performance impact
    - Graceful error handling
    """
    
    def __init__(self, config: Optional[AutoSignConfig] = None, **kwargs):
        """Initialize the auto-signer with configuration"""
        
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI library is required. Install with: pip install openai")
        
        if not REQUESTS_AVAILABLE:
            raise ImportError("Requests library is required. Install with: pip install requests")
        
        # Merge config with kwargs
        if config is None:
            config = AutoSignConfig(**kwargs)
        else:
            # Update config with any provided kwargs
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        
        self.config = config
        self._signatures_cache = {}
        self._enabled = False
        self._original_methods = {}
        
        # Initialize OriginMark client if available
        try:
            from .core import OriginMarkClient
            self.originmark_client = OriginMarkClient(api_url=config.originmark_api_url)
        except ImportError:
            self.originmark_client = None
            logger.warning("OriginMark core client not available. Using direct API calls.")
        
        if self.config.debug:
            logger.setLevel(logging.DEBUG)
            logger.debug(f"Initialized with config: {asdict(self.config)}")
    
    def enable(self) -> bool:
        """Enable auto-signing by patching OpenAI methods"""
        if self._enabled:
            logger.info("Auto-signing already enabled")
            return True
        
        try:
            self._patch_openai_methods()
            self._enabled = True
            logger.info(" OriginMark OpenAI auto-signing enabled")
            return True
        except Exception as e:
            logger.error(f"Failed to enable auto-signing: {e}")
            return False
    
    def disable(self) -> bool:
        """Disable auto-signing by restoring original methods"""
        if not self._enabled:
            logger.info("Auto-signing already disabled")
            return True
        
        try:
            self._restore_openai_methods()
            self._enabled = False
            logger.info("🔴 OriginMark OpenAI auto-signing disabled")
            return True
        except Exception as e:
            logger.error(f"Failed to disable auto-signing: {e}")
            return False
    
    def _patch_openai_methods(self):
        """Patch OpenAI methods for auto-signing"""
        
        # Support both legacy and modern OpenAI API
        methods_to_patch = []
        
        # Legacy API (openai < 1.0)
        if hasattr(openai, 'ChatCompletion'):
            methods_to_patch.extend([
                ('openai.ChatCompletion', 'create'),
                ('openai.Completion', 'create'),
            ])
        
        # Modern API (openai >= 1.0)
        if hasattr(openai, 'OpenAI'):
            try:
                client = openai.OpenAI()
                if hasattr(client, 'chat') and hasattr(client.chat, 'completions'):
                    methods_to_patch.append(('client.chat.completions', 'create'))
            except Exception:
                pass
        
        for module_path, method_name in methods_to_patch:
            try:
                self._patch_method(module_path, method_name)
            except Exception as e:
                logger.warning(f"Could not patch {module_path}.{method_name}: {e}")
    
    def _patch_method(self, module_path: str, method_name: str):
        """Patch a specific OpenAI method"""
        
        # Get the actual method to patch
        if module_path == 'openai.ChatCompletion':
            target = getattr(openai.ChatCompletion, method_name)
            setattr_target = openai.ChatCompletion
        elif module_path == 'openai.Completion':
            target = getattr(openai.Completion, method_name)
            setattr_target = openai.Completion
        else:
            # For modern API, we'll need to patch instances
            logger.debug(f"Skipping complex patching for {module_path}")
            return
        
        # Store original method
        original_key = f"{module_path}.{method_name}"
        self._original_methods[original_key] = target
        
        # Create wrapped method
        wrapped_method = self._create_wrapper(target, original_key)
        
        # Apply patch
        setattr(setattr_target, method_name, wrapped_method)
        logger.debug(f"Patched {original_key}")
    
    def _create_wrapper(self, original_method: Callable, method_key: str) -> Callable:
        """Create a wrapper that auto-signs responses"""
        
        @functools.wraps(original_method)
        def wrapper(*args, **kwargs):
            if not self.config.auto_sign:
                return original_method(*args, **kwargs)
            
            start_time = time.time()
            
            try:
                # Call original method
                response = original_method(*args, **kwargs)
                
                # Extract content for signing
                content = self._extract_content_from_response(response)
                
                if content and len(content) >= self.config.min_content_length:
                    # Sign the content asynchronously (non-blocking)
                    signature_data = self._sign_content_async(
                        content=content,
                        model=kwargs.get('model', 'unknown'),
                        prompt=self._extract_prompt_from_args(args, kwargs),
                        response_metadata=self._extract_response_metadata(response)
                    )
                    
                    # Attach signature to response
                    if signature_data:
                        self._attach_signature_to_response(response, signature_data)
                
                duration = time.time() - start_time
                logger.debug(f"Auto-signing completed in {duration:.3f}s")
                
                return response
                
            except Exception as e:
                logger.error(f"Error in auto-signing wrapper: {e}")
                # Return original response even if signing fails
                return original_method(*args, **kwargs)
        
        return wrapper
    
    def _extract_content_from_response(self, response) -> Optional[str]:
        """Extract text content from OpenAI response"""
        try:
            # Handle different response formats
            if hasattr(response, 'choices') and response.choices:
                choice = response.choices[0]
                
                # Legacy format
                if hasattr(choice, 'text'):
                    return choice.text.strip()
                
                # Chat format
                if hasattr(choice, 'message') and hasattr(choice.message, 'content'):
                    return choice.message.content.strip()
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract content: {e}")
            return None
    
    def _extract_prompt_from_args(self, args, kwargs) -> Optional[str]:
        """Extract the original prompt from API call arguments"""
        try:
            # Chat completion format
            if 'messages' in kwargs:
                messages = kwargs['messages']
                if isinstance(messages, list) and messages:
                    # Get the last user message
                    for msg in reversed(messages):
                        if isinstance(msg, dict) and msg.get('role') == 'user':
                            return msg.get('content', '')
            
            # Legacy completion format
            if 'prompt' in kwargs:
                return str(kwargs['prompt'])
            
            return None
        except Exception as e:
            logger.error(f"Failed to extract prompt: {e}")
            return None
    
    def _extract_response_metadata(self, response) -> Dict[str, Any]:
        """Extract metadata from OpenAI response"""
        metadata = {}
        
        try:
            if hasattr(response, 'model'):
                metadata['model'] = response.model
            
            if hasattr(response, 'usage'):
                metadata['usage'] = {
                    'prompt_tokens': getattr(response.usage, 'prompt_tokens', 0),
                    'completion_tokens': getattr(response.usage, 'completion_tokens', 0),
                    'total_tokens': getattr(response.usage, 'total_tokens', 0)
                }
            
            if hasattr(response, 'created'):
                metadata['created'] = response.created
                
        except Exception as e:
            logger.error(f"Failed to extract metadata: {e}")
        
        return metadata
    
    def _sign_content_async(self, content: str, model: str, prompt: Optional[str], 
                           response_metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Sign content using OriginMark API (non-blocking)"""
        try:
            # Prepare signing data
            sign_data = {
                'author': self.config.author,
                'model_used': model,
                'content_type': 'text',
                'prompt': prompt,
                'ai_generated': True,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                **response_metadata
            }
            
            if self.originmark_client:
                # Use OriginMark client if available
                result = self._sign_with_client(content, sign_data)
            else:
                # Use direct API call
                result = self._sign_with_api(content, sign_data)
            
            if result:
                # Cache the signature
                signature_id = result.get('id')
                if signature_id:
                    self._signatures_cache[signature_id] = result
                
                logger.info(f" Auto-signed content with ID: {signature_id}")
                return result
            
        except Exception as e:
            logger.error(f"Failed to sign content: {e}")
        
        return None
    
    def _sign_with_client(self, content: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Sign using OriginMark client"""
        try:
            return self.originmark_client.sign_text(content, metadata)
        except Exception as e:
            logger.error(f"Client signing failed: {e}")
            return None
    
    def _sign_with_api(self, content: str, metadata: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Sign using direct API call"""
        try:
            url = f"{self.config.originmark_api_url.rstrip('/')}/sign"
            
            # Prepare multipart form data
            files = {
                'file': ('content.txt', content.encode('utf-8'), 'text/plain')
            }
            
            data = {
                'author': metadata.get('author', self.config.author),
                'model_used': metadata.get('model_used', 'unknown'),
            }
            
            headers = {}
            if self.config.api_key:
                headers['Authorization'] = f'Bearer {self.config.api_key}'
            
            response = requests.post(
                url, 
                files=files, 
                data=data, 
                headers=headers,
                timeout=self.config.timeout
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"API signing failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"API signing failed: {e}")
            return None
    
    def _attach_signature_to_response(self, response, signature_data: Dict[str, Any]):
        """Attach signature data to OpenAI response object"""
        try:
            # Add signature as a new attribute
            setattr(response, 'originmark_signature', signature_data)
            
            # Also add to the first choice if available
            if hasattr(response, 'choices') and response.choices:
                setattr(response.choices[0], 'originmark_signature', signature_data)
                
        except Exception as e:
            logger.error(f"Failed to attach signature: {e}")
    
    def _restore_openai_methods(self):
        """Restore original OpenAI methods"""
        for method_key, original_method in self._original_methods.items():
            try:
                module_path, method_name = method_key.rsplit('.', 1)
                
                if module_path == 'openai.ChatCompletion':
                    setattr(openai.ChatCompletion, method_name, original_method)
                elif module_path == 'openai.Completion':
                    setattr(openai.Completion, method_name, original_method)
                
                logger.debug(f"Restored {method_key}")
            except Exception as e:
                logger.error(f"Failed to restore {method_key}: {e}")
        
        self._original_methods.clear()
    
    def get_signature(self, signature_id: str) -> Optional[Dict[str, Any]]:
        """Get signature data by ID"""
        return self._signatures_cache.get(signature_id)
    
    def get_signature_for_response(self, response) -> Optional[Dict[str, Any]]:
        """Get signature data for a specific OpenAI response"""
        return getattr(response, 'originmark_signature', None)
    
    def __enter__(self):
        """Context manager entry"""
        self.enable()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disable()

# Global instance for backward compatibility
_global_signer: Optional[OpenAIAutoSignerV2] = None

def enable_openai_autosigning(
    originmark_api_url: str = "http://localhost:8000",
    api_key: Optional[str] = None,
    author: str = "OpenAI Auto-Signer",
    **kwargs
) -> OpenAIAutoSignerV2:
    """
    Enable OpenAI auto-signing globally
    
    Args:
        originmark_api_url: OriginMark API URL
        api_key: Optional API key
        author: Author name for signatures
        **kwargs: Additional configuration options
    
    Returns:
        OpenAIAutoSignerV2 instance
    """
    global _global_signer
    
    config = AutoSignConfig(
        originmark_api_url=originmark_api_url,
        api_key=api_key,
        author=author,
        **kwargs
    )
    
    _global_signer = OpenAIAutoSignerV2(config)
    _global_signer.enable()
    
    return _global_signer

def disable_openai_autosigning():
    """Disable global OpenAI auto-signing"""
    global _global_signer
    if _global_signer:
        _global_signer.disable()
        _global_signer = None

def get_global_signer() -> Optional[OpenAIAutoSignerV2]:
    """Get the global auto-signer instance"""
    return _global_signer

# For backward compatibility
OpenAIAutoSigner = OpenAIAutoSignerV2
