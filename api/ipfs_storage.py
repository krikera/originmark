"""
IPFS Integration for OriginMark
Provides decentralized content storage and retrieval
"""

import json
import hashlib
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
import aiohttp
import ipfshttpclient
from pathlib import Path
import tempfile
import os
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class IPFSMetadata:
    """Metadata for IPFS-stored content"""
    ipfs_hash: str
    content_hash: str
    file_name: str
    file_size: int
    content_type: str
    timestamp: str
    author: Optional[str] = None
    model_used: Optional[str] = None

class IPFSStorageManager:
    """Manages IPFS storage and retrieval for OriginMark"""
    
    def __init__(self, 
                 ipfs_api_url: str = "/ip4/127.0.0.1/tcp/5001",
                 pinata_api_key: Optional[str] = None,
                 pinata_secret: Optional[str] = None,
                 web3_storage_token: Optional[str] = None):
        """
        Initialize IPFS storage manager with multiple provider support
        
        Args:
            ipfs_api_url: Local IPFS node API URL
            pinata_api_key: Pinata API key for pinning service
            pinata_secret: Pinata secret key
            web3_storage_token: Web3.Storage token for backup storage
        """
        self.ipfs_api_url = ipfs_api_url
        self.pinata_api_key = pinata_api_key
        self.pinata_secret = pinata_secret
        self.web3_storage_token = web3_storage_token
        
        # Try to connect to local IPFS node
        self.ipfs_client = None
        try:
            self.ipfs_client = ipfshttpclient.connect(ipfs_api_url)
            logger.info(f"Connected to IPFS node at {ipfs_api_url}")
        except Exception as e:
            logger.warning(f"Could not connect to local IPFS node: {e}")
    
    async def store_content(self, 
                          content: bytes, 
                          metadata: Dict[str, Any],
                          pin_to_services: bool = True) -> IPFSMetadata:
        """
        Store content to IPFS with metadata
        
        Args:
            content: Content bytes to store
            metadata: Metadata dictionary
            pin_to_services: Whether to pin to external services
            
        Returns:
            IPFSMetadata object with storage information
        """
        # Create metadata with IPFS-specific fields
        content_hash = hashlib.sha256(content).hexdigest()
        timestamp = datetime.now(timezone.utc).isoformat()
        
        ipfs_metadata = {
            "originmark_version": "3.0.0",
            "content_hash": content_hash,
            "timestamp": timestamp,
            "file_name": metadata.get("file_name", "content"),
            "file_size": len(content),
            "content_type": metadata.get("content_type", "application/octet-stream"),
            "author": metadata.get("author"),
            "model_used": metadata.get("model_used"),
            "signature_id": metadata.get("signature_id"),
            "public_key": metadata.get("public_key"),
            "signature": metadata.get("signature")
        }
        
        # Create content package with metadata
        content_package = {
            "content": content.hex(),  # Store as hex string
            "metadata": ipfs_metadata
        }
        
        content_package_json = json.dumps(content_package).encode()
        
        # Store to IPFS
        ipfs_hash = await self._store_to_ipfs(content_package_json)
        
        # Pin to external services if enabled
        if pin_to_services:
            await self._pin_to_services(ipfs_hash, ipfs_metadata)
        
        return IPFSMetadata(
            ipfs_hash=ipfs_hash,
            content_hash=content_hash,
            file_name=ipfs_metadata["file_name"],
            file_size=ipfs_metadata["file_size"],
            content_type=ipfs_metadata["content_type"],
            timestamp=timestamp,
            author=ipfs_metadata.get("author"),
            model_used=ipfs_metadata.get("model_used")
        )
    
    async def retrieve_content(self, ipfs_hash: str) -> Tuple[bytes, Dict[str, Any]]:
        """
        Retrieve content and metadata from IPFS
        
        Args:
            ipfs_hash: IPFS hash of the content
            
        Returns:
            Tuple of (content_bytes, metadata_dict)
        """
        # Try local IPFS first
        try:
            if self.ipfs_client:
                content_package_json = self.ipfs_client.cat(ipfs_hash)
                content_package = json.loads(content_package_json)
                
                content = bytes.fromhex(content_package["content"])
                metadata = content_package["metadata"]
                
                return content, metadata
        except Exception as e:
            logger.warning(f"Local IPFS retrieval failed: {e}")
        
        # Try public gateways
        gateways = [
            "https://ipfs.io/ipfs/",
            "https://gateway.pinata.cloud/ipfs/",
            "https://dweb.link/ipfs/",
            "https://cloudflare-ipfs.com/ipfs/"
        ]
        
        for gateway in gateways:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"{gateway}{ipfs_hash}") as response:
                        if response.status == 200:
                            content_package_json = await response.read()
                            content_package = json.loads(content_package_json)
                            
                            content = bytes.fromhex(content_package["content"])
                            metadata = content_package["metadata"]
                            
                            return content, metadata
            except Exception as e:
                logger.warning(f"Gateway {gateway} failed: {e}")
                continue
        
        raise Exception(f"Could not retrieve content from IPFS hash: {ipfs_hash}")
    
    async def verify_content_integrity(self, ipfs_hash: str) -> bool:
        """
        Verify content integrity by checking hash consistency
        
        Args:
            ipfs_hash: IPFS hash to verify
            
        Returns:
            True if content is intact, False otherwise
        """
        try:
            content, metadata = await self.retrieve_content(ipfs_hash)
            
            # Verify content hash
            computed_hash = hashlib.sha256(content).hexdigest()
            stored_hash = metadata.get("content_hash")
            
            return computed_hash == stored_hash
        except Exception as e:
            logger.error(f"Content integrity verification failed: {e}")
            return False
    
    async def _store_to_ipfs(self, content: bytes) -> str:
        """Store content to IPFS and return hash"""
        if self.ipfs_client:
            try:
                # Store using local IPFS client
                result = self.ipfs_client.add_bytes(content)
                return result
            except Exception as e:
                logger.warning(f"Local IPFS storage failed: {e}")
        
        # Fallback to HTTP API
        return await self._store_via_http_api(content)
    
    async def _store_via_http_api(self, content: bytes) -> str:
        """Store content via IPFS HTTP API"""
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False) as temp_file:
                temp_file.write(content)
                temp_file_path = temp_file.name
            
            try:
                # Upload via HTTP API
                async with aiohttp.ClientSession() as session:
                    with open(temp_file_path, 'rb') as f:
                        data = aiohttp.FormData()
                        data.add_field('file', f, filename='content')
                        
                        async with session.post(
                            f"http://127.0.0.1:5001/api/v0/add",
                            data=data
                        ) as response:
                            if response.status == 200:
                                result = await response.json()
                                return result["Hash"]
                            else:
                                raise Exception(f"IPFS API error: {response.status}")
            finally:
                os.unlink(temp_file_path)
                
        except Exception as e:
            logger.error(f"IPFS HTTP API storage failed: {e}")
            # As last resort, use public upload service (not recommended for production)
            return await self._store_via_public_service(content)
    
    async def _store_via_public_service(self, content: bytes) -> str:
        """Store via public IPFS service (fallback only)"""
        logger.warning("Using public IPFS service - not recommended for production")
        
        try:
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', content, filename='content')
                
                async with session.post(
                    "https://ipfs.infura.io:5001/api/v0/add",
                    data=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return result["Hash"]
                    else:
                        raise Exception(f"Public IPFS service error: {response.status}")
        except Exception as e:
            raise Exception(f"All IPFS storage methods failed: {e}")
    
    async def _pin_to_services(self, ipfs_hash: str, metadata: Dict[str, Any]):
        """Pin content to external pinning services"""
        
        # Pin to Pinata
        if self.pinata_api_key and self.pinata_secret:
            await self._pin_to_pinata(ipfs_hash, metadata)
        
        # Pin to Web3.Storage
        if self.web3_storage_token:
            await self._pin_to_web3_storage(ipfs_hash, metadata)
    
    async def _pin_to_pinata(self, ipfs_hash: str, metadata: Dict[str, Any]):
        """Pin content to Pinata"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "pinata_api_key": self.pinata_api_key,
                    "pinata_secret_api_key": self.pinata_secret,
                    "Content-Type": "application/json"
                }
                
                pin_data = {
                    "hashToPin": ipfs_hash,
                    "pinataMetadata": {
                        "name": f"OriginMark-{metadata.get('signature_id', 'unknown')}",
                        "keyvalues": {
                            "originmark": "true",
                            "content_type": metadata.get("content_type", "unknown"),
                            "author": metadata.get("author", "unknown"),
                            "timestamp": metadata.get("timestamp")
                        }
                    }
                }
                
                async with session.post(
                    "https://api.pinata.cloud/pinning/pinByHash",
                    headers=headers,
                    json=pin_data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"Successfully pinned to Pinata: {result['ipfsHash']}")
                    else:
                        logger.warning(f"Pinata pinning failed: {response.status}")
        except Exception as e:
            logger.warning(f"Pinata pinning error: {e}")
    
    async def _pin_to_web3_storage(self, ipfs_hash: str, metadata: Dict[str, Any]):
        """Pin content to Web3.Storage"""
        try:
            async with aiohttp.ClientSession() as session:
                headers = {
                    "Authorization": f"Bearer {self.web3_storage_token}",
                    "Content-Type": "application/json"
                }
                
                # Web3.Storage uses different API - this is a simplified example
                logger.info(f"Would pin to Web3.Storage: {ipfs_hash}")
                
        except Exception as e:
            logger.warning(f"Web3.Storage pinning error: {e}")
    
    async def list_stored_content(self, limit: int = 100) -> List[IPFSMetadata]:
        """List content stored by this instance"""
        # This would require maintaining a local database of stored content
        # For now, return empty list
        return []
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        stats = {
            "local_ipfs_available": self.ipfs_client is not None,
            "pinata_configured": bool(self.pinata_api_key),
            "web3_storage_configured": bool(self.web3_storage_token),
            "total_stored": 0,  # Would track in database
            "total_size": 0     # Would track in database
        }
        
        # Get IPFS node stats if available
        if self.ipfs_client:
            try:
                node_stats = self.ipfs_client.stats.repo()
                stats.update({
                    "ipfs_repo_size": node_stats.get("RepoSize", 0),
                    "ipfs_num_objects": node_stats.get("NumObjects", 0)
                })
            except Exception as e:
                logger.warning(f"Could not get IPFS stats: {e}")
        
        return stats

# Global IPFS storage manager instance
ipfs_storage = None

def get_ipfs_storage() -> IPFSStorageManager:
    """Get global IPFS storage manager instance"""
    global ipfs_storage
    if ipfs_storage is None:
        ipfs_storage = IPFSStorageManager(
            pinata_api_key=os.getenv("PINATA_API_KEY"),
            pinata_secret=os.getenv("PINATA_SECRET"),
            web3_storage_token=os.getenv("WEB3_STORAGE_TOKEN")
        )
    return ipfs_storage

# Utility functions for easy integration
async def store_signature_to_ipfs(content: bytes, signature_data: Dict[str, Any]) -> str:
    """
    Store signed content to IPFS
    
    Args:
        content: Original content bytes
        signature_data: OriginMark signature data
        
    Returns:
        IPFS hash of stored content
    """
    storage = get_ipfs_storage()
    ipfs_metadata = await storage.store_content(content, signature_data)
    return ipfs_metadata.ipfs_hash

async def retrieve_signature_from_ipfs(ipfs_hash: str) -> Tuple[bytes, Dict[str, Any]]:
    """
    Retrieve signed content from IPFS
    
    Args:
        ipfs_hash: IPFS hash
        
    Returns:
        Tuple of (content, signature_data)
    """
    storage = get_ipfs_storage()
    return await storage.retrieve_content(ipfs_hash) 