"""
Hardware Security Module (HSM) Integration for OriginMark
Provides secure key storage and cryptographic operations using HSM devices.
"""

import os
import json
import base64
import hashlib
import secrets
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from abc import ABC, abstractmethod
import requests
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)

class HSMProvider(ABC):
    """Abstract base class for HSM providers"""
    
    @abstractmethod
    async def generate_key_pair(self, key_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a new key pair in the HSM"""
        pass
    
    @abstractmethod
    async def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data using the specified key"""
        pass
    
    @abstractmethod
    async def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify a signature using the specified key"""
        pass
    
    @abstractmethod
    async def get_public_key(self, key_id: str) -> bytes:
        """Get the public key for the specified key ID"""
        pass
    
    @abstractmethod
    async def list_keys(self) -> List[Dict[str, Any]]:
        """List all keys in the HSM"""
        pass
    
    @abstractmethod
    async def delete_key(self, key_id: str) -> bool:
        """Delete a key from the HSM"""
        pass

class AWSCloudHSMProvider(HSMProvider):
    """AWS CloudHSM provider implementation"""
    
    def __init__(self, cluster_id: str, user: str, password: str):
        self.cluster_id = cluster_id
        self.user = user
        self.password = password
        self.session = None
        
    async def _connect(self):
        """Establish connection to AWS CloudHSM"""
        try:
            # In production, use proper AWS CloudHSM SDK
            # This is a simplified implementation
            self.session = {
                'cluster_id': self.cluster_id,
                'user': self.user,
                'connected': True
            }
            return True
        except Exception as e:
            logger.error(f"Failed to connect to AWS CloudHSM: {e}")
            return False
    
    async def generate_key_pair(self, key_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Ed25519 key pair in AWS CloudHSM"""
        if not await self._connect():
            raise Exception("Failed to connect to HSM")
        
        try:
            # Generate key pair using CloudHSM API
            # This is a placeholder implementation
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Store in HSM (placeholder)
            hsm_key_id = f"aws_cloudhsm_{key_id}_{secrets.token_hex(8)}"
            
            # Get public key bytes
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            return {
                'hsm_key_id': hsm_key_id,
                'public_key': base64.b64encode(public_key_bytes).decode(),
                'key_type': 'Ed25519',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata,
                'provider': 'aws_cloudhsm'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate key pair in AWS CloudHSM: {e}")
            raise
    
    async def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data using AWS CloudHSM"""
        if not await self._connect():
            raise Exception("Failed to connect to HSM")
        
        try:
            # In production, use CloudHSM signing API
            # This is a placeholder that generates a signature
            private_key = ed25519.Ed25519PrivateKey.generate()  # Placeholder
            signature = private_key.sign(data)
            
            return signature
            
        except Exception as e:
            logger.error(f"Failed to sign data with AWS CloudHSM: {e}")
            raise
    
    async def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature using AWS CloudHSM"""
        try:
            public_key_bytes = await self.get_public_key(key_id)
            public_key = ed25519.Ed25519PublicKey.from_public_bytes(public_key_bytes)
            
            public_key.verify(signature, data)
            return True
            
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    async def get_public_key(self, key_id: str) -> bytes:
        """Get public key from AWS CloudHSM"""
        if not await self._connect():
            raise Exception("Failed to connect to HSM")
        
        try:
            # Retrieve public key from HSM
            # Placeholder implementation
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            return public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
        except Exception as e:
            logger.error(f"Failed to get public key from AWS CloudHSM: {e}")
            raise
    
    async def list_keys(self) -> List[Dict[str, Any]]:
        """List keys in AWS CloudHSM"""
        if not await self._connect():
            raise Exception("Failed to connect to HSM")
        
        try:
            # List keys from HSM
            # Placeholder implementation
            return [
                {
                    'key_id': 'aws_cloudhsm_key_1',
                    'key_type': 'Ed25519',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'label': 'OriginMark Signing Key 1'
                }
            ]
            
        except Exception as e:
            logger.error(f"Failed to list keys from AWS CloudHSM: {e}")
            raise
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete key from AWS CloudHSM"""
        if not await self._connect():
            raise Exception("Failed to connect to HSM")
        
        try:
            # Delete key from HSM
            # Placeholder implementation
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete key from AWS CloudHSM: {e}")
            return False

class AzureKeyVaultProvider(HSMProvider):
    """Azure Key Vault HSM provider implementation"""
    
    def __init__(self, vault_url: str, client_id: str, client_secret: str):
        self.vault_url = vault_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = None
        
    async def _get_access_token(self):
        """Get access token for Azure Key Vault"""
        try:
            token_url = f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID')}/oauth2/v2.0/token"
            
            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://vault.azure.net/.default',
                'grant_type': 'client_credentials'
            }
            
            response = requests.post(token_url, data=data)
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data['access_token']
                return True
            else:
                logger.error(f"Failed to get Azure access token: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Error getting Azure access token: {e}")
            return False
    
    async def generate_key_pair(self, key_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate key pair in Azure Key Vault HSM"""
        if not await self._get_access_token():
            raise Exception("Failed to authenticate with Azure Key Vault")
        
        try:
            # Create key in Azure Key Vault
            url = f"{self.vault_url}/keys/{key_id}/create"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            data = {
                'kty': 'OKP',
                'crv': 'Ed25519',
                'key_ops': ['sign', 'verify'],
                'attributes': {
                    'enabled': True
                },
                'tags': metadata
            }
            
            response = requests.post(f"{url}?api-version=7.3", headers=headers, json=data)
            
            if response.status_code == 200:
                key_data = response.json()
                
                return {
                    'hsm_key_id': key_data['key']['kid'],
                    'public_key': key_data['key']['key'],
                    'key_type': 'Ed25519',
                    'created_at': datetime.now(timezone.utc).isoformat(),
                    'metadata': metadata,
                    'provider': 'azure_keyvault'
                }
            else:
                raise Exception(f"Failed to create key: {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to generate key pair in Azure Key Vault: {e}")
            raise
    
    async def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data using Azure Key Vault"""
        if not await self._get_access_token():
            raise Exception("Failed to authenticate with Azure Key Vault")
        
        try:
            url = f"{self.vault_url}/keys/{key_id}/sign"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Hash the data first
            digest = hashlib.sha256(data).digest()
            
            payload = {
                'alg': 'EdDSA',
                'value': base64.b64encode(digest).decode()
            }
            
            response = requests.post(f"{url}?api-version=7.3", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return base64.b64decode(result['value'])
            else:
                raise Exception(f"Failed to sign data: {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to sign data with Azure Key Vault: {e}")
            raise
    
    async def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature using Azure Key Vault"""
        if not await self._get_access_token():
            raise Exception("Failed to authenticate with Azure Key Vault")
        
        try:
            url = f"{self.vault_url}/keys/{key_id}/verify"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            
            # Hash the data first
            digest = hashlib.sha256(data).digest()
            
            payload = {
                'alg': 'EdDSA',
                'digest': base64.b64encode(digest).decode(),
                'value': base64.b64encode(signature).decode()
            }
            
            response = requests.post(f"{url}?api-version=7.3", headers=headers, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                return result.get('value', False)
            else:
                logger.error(f"Failed to verify signature: {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to verify signature with Azure Key Vault: {e}")
            return False
    
    async def get_public_key(self, key_id: str) -> bytes:
        """Get public key from Azure Key Vault"""
        if not await self._get_access_token():
            raise Exception("Failed to authenticate with Azure Key Vault")
        
        try:
            url = f"{self.vault_url}/keys/{key_id}"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(f"{url}?api-version=7.3", headers=headers)
            
            if response.status_code == 200:
                key_data = response.json()
                # Extract public key from JWK format
                public_key_jwk = key_data['key']
                
                # Convert JWK to raw bytes (implementation depends on JWK format)
                # This is a placeholder
                return base64.b64decode(public_key_jwk.get('x', ''))
            else:
                raise Exception(f"Failed to get public key: {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to get public key from Azure Key Vault: {e}")
            raise
    
    async def list_keys(self) -> List[Dict[str, Any]]:
        """List keys in Azure Key Vault"""
        if not await self._get_access_token():
            raise Exception("Failed to authenticate with Azure Key Vault")
        
        try:
            url = f"{self.vault_url}/keys"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.get(f"{url}?api-version=7.3", headers=headers)
            
            if response.status_code == 200:
                keys_data = response.json()
                
                keys = []
                for key_info in keys_data.get('value', []):
                    keys.append({
                        'key_id': key_info.get('kid', '').split('/')[-1],
                        'key_type': 'Ed25519',
                        'created_at': key_info.get('attributes', {}).get('created'),
                        'enabled': key_info.get('attributes', {}).get('enabled')
                    })
                
                return keys
            else:
                raise Exception(f"Failed to list keys: {response.text}")
                
        except Exception as e:
            logger.error(f"Failed to list keys from Azure Key Vault: {e}")
            raise
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete key from Azure Key Vault"""
        if not await self._get_access_token():
            raise Exception("Failed to authenticate with Azure Key Vault")
        
        try:
            url = f"{self.vault_url}/keys/{key_id}"
            
            headers = {
                'Authorization': f'Bearer {self.access_token}'
            }
            
            response = requests.delete(f"{url}?api-version=7.3", headers=headers)
            
            return response.status_code == 200
            
        except Exception as e:
            logger.error(f"Failed to delete key from Azure Key Vault: {e}")
            return False

class SoftHSMProvider(HSMProvider):
    """SoftHSM provider for development and testing"""
    
    def __init__(self, token_label: str = "OriginMark", pin: str = "1234"):
        self.token_label = token_label
        self.pin = pin
        self.keys = {}  # In-memory key storage for testing
        
    async def generate_key_pair(self, key_id: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Generate key pair in SoftHSM"""
        try:
            # Generate Ed25519 key pair
            private_key = ed25519.Ed25519PrivateKey.generate()
            public_key = private_key.public_key()
            
            # Store in memory (in production, this would use SoftHSM PKCS#11)
            hsm_key_id = f"softhsm_{key_id}_{secrets.token_hex(8)}"
            
            self.keys[hsm_key_id] = {
                'private_key': private_key,
                'public_key': public_key,
                'metadata': metadata,
                'created_at': datetime.now(timezone.utc)
            }
            
            public_key_bytes = public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
            return {
                'hsm_key_id': hsm_key_id,
                'public_key': base64.b64encode(public_key_bytes).decode(),
                'key_type': 'Ed25519',
                'created_at': datetime.now(timezone.utc).isoformat(),
                'metadata': metadata,
                'provider': 'softhsm'
            }
            
        except Exception as e:
            logger.error(f"Failed to generate key pair in SoftHSM: {e}")
            raise
    
    async def sign_data(self, key_id: str, data: bytes) -> bytes:
        """Sign data using SoftHSM"""
        try:
            if key_id not in self.keys:
                raise Exception(f"Key {key_id} not found")
            
            private_key = self.keys[key_id]['private_key']
            signature = private_key.sign(data)
            
            return signature
            
        except Exception as e:
            logger.error(f"Failed to sign data with SoftHSM: {e}")
            raise
    
    async def verify_signature(self, key_id: str, data: bytes, signature: bytes) -> bool:
        """Verify signature using SoftHSM"""
        try:
            if key_id not in self.keys:
                raise Exception(f"Key {key_id} not found")
            
            public_key = self.keys[key_id]['public_key']
            public_key.verify(signature, data)
            return True
            
        except Exception as e:
            logger.error(f"Signature verification failed with SoftHSM: {e}")
            return False
    
    async def get_public_key(self, key_id: str) -> bytes:
        """Get public key from SoftHSM"""
        try:
            if key_id not in self.keys:
                raise Exception(f"Key {key_id} not found")
            
            public_key = self.keys[key_id]['public_key']
            return public_key.public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw
            )
            
        except Exception as e:
            logger.error(f"Failed to get public key from SoftHSM: {e}")
            raise
    
    async def list_keys(self) -> List[Dict[str, Any]]:
        """List keys in SoftHSM"""
        try:
            keys = []
            for key_id, key_data in self.keys.items():
                keys.append({
                    'key_id': key_id,
                    'key_type': 'Ed25519',
                    'created_at': key_data['created_at'].isoformat(),
                    'metadata': key_data['metadata']
                })
            
            return keys
            
        except Exception as e:
            logger.error(f"Failed to list keys from SoftHSM: {e}")
            raise
    
    async def delete_key(self, key_id: str) -> bool:
        """Delete key from SoftHSM"""
        try:
            if key_id in self.keys:
                del self.keys[key_id]
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete key from SoftHSM: {e}")
            return False

class HSMManager:
    """HSM Manager for handling multiple HSM providers"""
    
    def __init__(self):
        self.providers = {}
        self.default_provider = None
        
    def register_provider(self, name: str, provider: HSMProvider, is_default: bool = False):
        """Register an HSM provider"""
        self.providers[name] = provider
        
        if is_default or not self.default_provider:
            self.default_provider = name
    
    def get_provider(self, name: Optional[str] = None) -> HSMProvider:
        """Get HSM provider by name"""
        provider_name = name or self.default_provider
        
        if provider_name not in self.providers:
            raise Exception(f"HSM provider '{provider_name}' not found")
        
        return self.providers[provider_name]
    
    async def generate_key_pair(self, key_id: str, metadata: Dict[str, Any], provider: Optional[str] = None) -> Dict[str, Any]:
        """Generate key pair using specified or default HSM provider"""
        hsm = self.get_provider(provider)
        return await hsm.generate_key_pair(key_id, metadata)
    
    async def sign_data(self, key_id: str, data: bytes, provider: Optional[str] = None) -> bytes:
        """Sign data using specified or default HSM provider"""
        hsm = self.get_provider(provider)
        return await hsm.sign_data(key_id, data)
    
    async def verify_signature(self, key_id: str, data: bytes, signature: bytes, provider: Optional[str] = None) -> bool:
        """Verify signature using specified or default HSM provider"""
        hsm = self.get_provider(provider)
        return await hsm.verify_signature(key_id, data, signature)
    
    async def get_public_key(self, key_id: str, provider: Optional[str] = None) -> bytes:
        """Get public key using specified or default HSM provider"""
        hsm = self.get_provider(provider)
        return await hsm.get_public_key(key_id)
    
    async def list_keys(self, provider: Optional[str] = None) -> List[Dict[str, Any]]:
        """List keys using specified or default HSM provider"""
        hsm = self.get_provider(provider)
        return await hsm.list_keys()
    
    async def delete_key(self, key_id: str, provider: Optional[str] = None) -> bool:
        """Delete key using specified or default HSM provider"""
        hsm = self.get_provider(provider)
        return await hsm.delete_key(key_id)

# Global HSM manager instance
hsm_manager = HSMManager()

def initialize_hsm_providers():
    """Initialize HSM providers based on configuration"""
    
    # Initialize SoftHSM for development
    softhsm = SoftHSMProvider()
    hsm_manager.register_provider('softhsm', softhsm, is_default=True)
    
    # Initialize AWS CloudHSM if configured
    aws_cluster_id = os.getenv('AWS_CLOUDHSM_CLUSTER_ID')
    aws_user = os.getenv('AWS_CLOUDHSM_USER')
    aws_password = os.getenv('AWS_CLOUDHSM_PASSWORD')
    
    if aws_cluster_id and aws_user and aws_password:
        aws_hsm = AWSCloudHSMProvider(aws_cluster_id, aws_user, aws_password)
        hsm_manager.register_provider('aws_cloudhsm', aws_hsm)
    
    # Initialize Azure Key Vault if configured
    azure_vault_url = os.getenv('AZURE_KEYVAULT_URL')
    azure_client_id = os.getenv('AZURE_CLIENT_ID')
    azure_client_secret = os.getenv('AZURE_CLIENT_SECRET')
    
    if azure_vault_url and azure_client_id and azure_client_secret:
        azure_hsm = AzureKeyVaultProvider(azure_vault_url, azure_client_id, azure_client_secret)
        hsm_manager.register_provider('azure_keyvault', azure_hsm)

# Initialize providers on module load
initialize_hsm_providers() 