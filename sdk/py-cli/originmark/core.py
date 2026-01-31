"""Core OriginMark functionality for signing and verifying content."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import nacl.encoding
import nacl.exceptions
import nacl.signing
import requests


class OriginMarkClient:
    """Core OriginMark functionality for signing and verifying content.
    
    This class provides cryptographic signing and verification of content
    using Ed25519 signatures. It can operate locally or through the API.
    
    Example:
        >>> client = OriginMarkClient(api_url="https://api.originmark.dev")
        >>> result = client.sign_content(b"Hello, World!", {"author": "Alice"})
        >>> print(result["signature"])
    """
    
    def __init__(self, api_url: str | None = None) -> None:
        """Initialize the OriginMark client.
        
        Args:
            api_url: Optional API URL for remote operations.
        """
        self.api_url = api_url
    
    @staticmethod
    def compute_hash(content: bytes) -> str:
        """Compute SHA256 hash of content.
        
        Args:
            content: The bytes to hash.
            
        Returns:
            Hexadecimal hash string.
        """
        return hashlib.sha256(content).hexdigest()
    
    def generate_keypair(self) -> tuple[nacl.signing.SigningKey, nacl.signing.VerifyKey]:
        """Generate a new Ed25519 keypair.
        
        Returns:
            Tuple of (signing_key, verify_key).
        """
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        return signing_key, verify_key
    
    def sign_content(
        self,
        content: bytes,
        metadata: dict[str, Any] | None = None,
        private_key: str | None = None
    ) -> dict[str, Any]:
        """Sign content with Ed25519 signature.
        
        Args:
            content: The content bytes to sign.
            metadata: Optional metadata to include.
            private_key: Optional base64-encoded private key. If not provided,
                        a new keypair will be generated.
        
        Returns:
            Dictionary containing signature, public key, content hash, and metadata.
        """
        # Generate or load keypair
        if private_key:
            signing_key = nacl.signing.SigningKey(
                nacl.encoding.Base64Encoder.decode(private_key)
            )
        else:
            signing_key = nacl.signing.SigningKey.generate()
        
        verify_key = signing_key.verify_key
        
        # Compute content hash
        content_hash = self.compute_hash(content)
        
        # Sign the hash
        signed = signing_key.sign(content_hash.encode())
        
        # Prepare metadata with timezone-aware timestamp
        default_metadata: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "content_type": "text",
        }
        if metadata:
            default_metadata.update(metadata)
        
        # Create signature result
        result: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "content_hash": content_hash,
            "signature": nacl.encoding.Base64Encoder.encode(signed.signature).decode(),
            "public_key": nacl.encoding.Base64Encoder.encode(bytes(verify_key)).decode(),
            "timestamp": default_metadata["timestamp"],
            "metadata": default_metadata
        }
        
        # Include private key if generated
        if not private_key:
            result["private_key"] = nacl.encoding.Base64Encoder.encode(
                bytes(signing_key)
            ).decode()
        
        return result
    
    def verify_content(
        self,
        content: bytes,
        signature: str,
        public_key: str
    ) -> dict[str, Any]:
        """Verify content signature.
        
        Args:
            content: The content bytes to verify.
            signature: Base64-encoded signature.
            public_key: Base64-encoded public key.
        
        Returns:
            Dictionary with 'valid' boolean, 'message', and 'content_hash'.
        """
        try:
            # Decode public key and signature
            verify_key = nacl.signing.VerifyKey(
                nacl.encoding.Base64Encoder.decode(public_key)
            )
            signature_bytes = nacl.encoding.Base64Encoder.decode(signature)
            
            # Compute content hash
            content_hash = self.compute_hash(content)
            
            # Verify signature
            try:
                verify_key.verify(content_hash.encode(), signature_bytes)
                return {
                    "valid": True,
                    "message": "Signature verified successfully",
                    "content_hash": content_hash
                }
            except nacl.exceptions.BadSignatureError:
                return {
                    "valid": False,
                    "message": "Invalid signature",
                    "content_hash": content_hash
                }
        except Exception as e:
            return {
                "valid": False,
                "message": f"Verification failed: {e!s}",
                "content_hash": ""
            }
    
    def sign_file(
        self,
        file_path: Path,
        metadata: dict[str, Any] | None = None,
        private_key: str | None = None
    ) -> dict[str, Any]:
        """Sign a file and create sidecar JSON.
        
        Args:
            file_path: Path to the file to sign.
            metadata: Optional metadata to include.
            private_key: Optional base64-encoded private key.
        
        Returns:
            Dictionary containing signature details.
        """
        # Read file content
        content = file_path.read_bytes()
        
        # Determine content type
        image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
        content_type = "image" if file_path.suffix.lower() in image_extensions else "text"
        
        # Prepare metadata
        file_metadata: dict[str, Any] = {
            "file_name": file_path.name,
            "file_size": len(content),
            "content_type": content_type
        }
        if metadata:
            file_metadata.update(metadata)
        
        # Sign content
        result = self.sign_content(content, file_metadata, private_key)
        
        # Save sidecar JSON
        sidecar_path = file_path.with_suffix(file_path.suffix + ".originmark.json")
        sidecar_path.write_text(json.dumps(result, indent=2))
        
        return result
    
    def verify_file(
        self,
        file_path: Path,
        sidecar_path: Path | None = None
    ) -> dict[str, Any]:
        """Verify a file with its sidecar JSON.
        
        Args:
            file_path: Path to the file to verify.
            sidecar_path: Optional path to sidecar JSON. If not provided,
                         looks for <filename>.originmark.json
        
        Returns:
            Dictionary with verification result and metadata.
        """
        # Read file content
        content = file_path.read_bytes()
        
        # Load sidecar JSON
        if not sidecar_path:
            sidecar_path = file_path.with_suffix(file_path.suffix + ".originmark.json")
        
        if not sidecar_path.exists():
            return {
                "valid": False,
                "message": "Sidecar JSON file not found",
                "content_hash": ""
            }
        
        sidecar_data = json.loads(sidecar_path.read_text())
        
        # Verify signature
        result = self.verify_content(
            content,
            sidecar_data["signature"],
            sidecar_data["public_key"]
        )
        
        # Add metadata to result
        if result["valid"]:
            result["metadata"] = sidecar_data.get("metadata", {})
        
        return result
    
    def sign_with_api(
        self,
        file_path: Path,
        metadata: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Sign content using the API.
        
        Args:
            file_path: Path to the file to sign.
            metadata: Optional metadata to include.
        
        Returns:
            API response as dictionary.
        
        Raises:
            ValueError: If API URL is not configured.
            requests.HTTPError: If the API request fails.
        """
        if not self.api_url:
            raise ValueError("API URL not configured")
        
        with file_path.open("rb") as f:
            files = {"file": f}
            data: dict[str, str] = {}
            
            if metadata:
                if "author" in metadata:
                    data["author"] = metadata["author"]
                if "model_used" in metadata:
                    data["model_used"] = metadata["model_used"]
            
            response = requests.post(
                f"{self.api_url}/sign",
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()
    
    def verify_with_api(
        self,
        file_path: Path,
        signature_id: str | None = None,
        signature: str | None = None,
        public_key: str | None = None
    ) -> dict[str, Any]:
        """Verify content using the API.
        
        Args:
            file_path: Path to the file to verify.
            signature_id: Optional signature ID to verify against.
            signature: Optional signature string.
            public_key: Optional public key.
        
        Returns:
            API response as dictionary.
        
        Raises:
            ValueError: If API URL is not configured.
            requests.HTTPError: If the API request fails.
        """
        if not self.api_url:
            raise ValueError("API URL not configured")
        
        with file_path.open("rb") as f:
            files = {"file": f}
            data: dict[str, str] = {}
            
            if signature_id:
                data["signature_id"] = signature_id
            if signature:
                data["signature"] = signature
            if public_key:
                data["public_key"] = public_key
            
            response = requests.post(
                f"{self.api_url}/verify",
                files=files,
                data=data,
                timeout=30
            )
            response.raise_for_status()
            
            return response.json()


# Backwards compatibility alias
OriginMark = OriginMarkClient