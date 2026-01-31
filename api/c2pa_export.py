"""
C2PA (Coalition for Content Provenance and Authenticity) Export Module
Converts OriginMark signatures to C2PA-compatible manifests
"""

from typing import Dict, Any, Optional, List
import json
import base64
from datetime import datetime, timezone
import hashlib
import uuid
from dataclasses import dataclass, asdict

@dataclass
class C2PAAssertion:
    """Represents a C2PA assertion"""
    label: str
    data: Dict[str, Any]
    
@dataclass
class C2PAClaim:
    """Represents a C2PA claim"""
    claim_generator: str = "OriginMark/2.0"
    title: str = ""
    assertions: List[Dict[str, Any]] = None
    alg: str = "es256"
    signature: Optional[str] = None
    
    def __post_init__(self):
        if self.assertions is None:
            self.assertions = []

class C2PAManifestExporter:
    """Export OriginMark signatures as C2PA manifests"""
    
    def __init__(self):
        self.version = "1.0"
        self.supported_formats = ["json", "sidecar"]
        
    def create_c2pa_manifest(self, 
                            originmark_signature: Dict[str, Any],
                            asset_content: Optional[bytes] = None,
                            additional_assertions: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Create a C2PA manifest from OriginMark signature data
        
        Args:
            originmark_signature: OriginMark signature data
            asset_content: Optional asset content for hash verification
            additional_assertions: Optional additional C2PA assertions
            
        Returns:
            C2PA manifest as dictionary
        """
        # Create assertions list
        assertions = []
        
        # Add creation assertion (c2pa.actions)
        creation_assertion = self._create_actions_assertion(originmark_signature)
        assertions.append(asdict(creation_assertion))
        
        # Add data hash assertion (c2pa.hash.data)
        hash_assertion = self._create_hash_assertion(originmark_signature)
        assertions.append(asdict(hash_assertion))
        
        # Add OriginMark signature as custom assertion
        originmark_assertion = self._create_originmark_assertion(originmark_signature)
        assertions.append(asdict(originmark_assertion))
        
        # Add any additional assertions
        if additional_assertions:
            assertions.extend(additional_assertions)
        
        # Create claim
        claim = C2PAClaim(
            title=f"OriginMark Signature {originmark_signature.get('id', 'Unknown')}",
            assertions=assertions
        )
        
        # Create manifest structure
        manifest = {
            "@context": "https://c2pa.org/specifications/1.4/context.json",
            "format": "application/c2pa",
            "version": "1.4",
            "claim_generator": "OriginMark/2.0.0",
            "claim_generator_info": [
                {
                    "name": "OriginMark",
                    "version": "2.0.0",
                    "icon": "https://originmark.dev/icon.png",
                    "description": "Digital provenance and authenticity verification"
                }
            ],
            "title": f"OriginMark Signature {originmark_signature.get('id', 'Unknown')[:8]}...",
            "description": "Content verified with OriginMark digital signatures for AI content authenticity",
            "claim": asdict(claim),
            "validation_status": [{
                "code": "claimSignature.verified",
                "url": f"https://originmark.dev/verify/{originmark_signature.get('id')}",
                "explanation": "OriginMark cryptographic signature verified"
            }],
            "signature_info": {
                "algorithm": "Ed25519",
                "issuer": "OriginMark Certificate Authority"
            },
            "originmark_metadata": {
                "signature_id": originmark_signature.get("id"),
                "export_version": self.version,
                "export_timestamp": datetime.now(timezone.utc).isoformat(),
                "verification_url": f"https://originmark.dev/verify/{originmark_signature.get('id')}",
                "standard_compatibility": ["C2PA v1.4", "Adobe CAI"],
                "blockchain_anchored": originmark_signature.get("metadata", {}).get("blockchain_enabled", False)
            }
        }
        
        return manifest
    
    def _create_actions_assertion(self, signature: Dict[str, Any]) -> C2PAAssertion:
        """Create c2pa.actions assertion"""
        timestamp = signature.get("timestamp", datetime.now(timezone.utc).isoformat())
        metadata = signature.get("metadata", {})
        
        actions = [{
            "action": "c2pa.created",
            "when": timestamp,
            "softwareAgent": {
                "name": "OriginMark",
                "version": "2.0.0",
                "description": "Digital provenance and authenticity verification platform"
            },
            "digitalSourceType": "algorithmicMedia" if metadata.get("model_used") else "other"
        }]
        
        # Add AI model information if available
        if metadata.get("model_used"):
            actions.append({
                "action": "c2pa.ai.generative",
                "when": timestamp,
                "digitalSourceType": "trainedAlgorithmicMedia",
                "softwareAgent": {
                    "name": metadata["model_used"],
                    "version": "unknown",
                    "description": f"AI model used for content generation"
                },
                "reason": "Content generated using AI model with OriginMark signature verification"
            })
        
        return C2PAAssertion(
            label="c2pa.actions",
            data={"actions": actions}
        )
    
    def _create_hash_assertion(self, signature: Dict[str, Any]) -> C2PAAssertion:
        """Create c2pa.hash.data assertion"""
        return C2PAAssertion(
            label="c2pa.hash.data",
            data={
                "exclusions": [],
                "alg": "sha256",
                "hash": signature.get("content_hash", ""),
                "name": "jumbf manifest"
            }
        )
    
    def _create_originmark_assertion(self, signature: Dict[str, Any]) -> C2PAAssertion:
        """Create custom OriginMark assertion"""
        metadata = signature.get("metadata", {})
        
        return C2PAAssertion(
            label="org.originmark.signature",
            data={
                "signature_id": signature.get("id"),
                "signature": signature.get("signature"),
                "public_key": signature.get("public_key"),
                "author": metadata.get("author", "Unknown"),
                "model_used": metadata.get("model_used"),
                "content_type": metadata.get("content_type"),
                "timestamp": signature.get("timestamp"),
                "blockchain_anchored": metadata.get("blockchain_enabled", False),
                "ipfs_hash": metadata.get("ipfs_hash")
            }
        )
    
    def export_to_json(self, 
                      originmark_signature: Dict[str, Any],
                      output_path: Optional[str] = None) -> str:
        """
        Export as JSON format
        
        Args:
            originmark_signature: OriginMark signature data
            output_path: Optional path to save JSON file
            
        Returns:
            JSON string of manifest
        """
        manifest = self.create_c2pa_manifest(originmark_signature)
        json_str = json.dumps(manifest, indent=2, sort_keys=True)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(json_str)
                
        return json_str
    
    def export_to_sidecar(self, 
                         originmark_signature: Dict[str, Any],
                         asset_path: str,
                         output_path: Optional[str] = None) -> str:
        """
        Export as C2PA sidecar file
        
        Args:
            originmark_signature: OriginMark signature data
            asset_path: Path to the asset file
            output_path: Optional output path (defaults to asset_path + .c2pa)
            
        Returns:
            Path to sidecar file
        """
        if not output_path:
            output_path = f"{asset_path}.c2pa"
            
        manifest = self.create_c2pa_manifest(originmark_signature)
        
        # Add asset reference
        manifest["asset_reference"] = {
            "path": asset_path,
            "hash": originmark_signature.get("content_hash")
        }
        
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
        return output_path
    
    def validate_export(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate exported manifest meets C2PA requirements
        
        Args:
            manifest: C2PA manifest to validate
            
        Returns:
            Validation result with status and messages
        """
        errors = []
        warnings = []
        
        # Check required fields
        if "claim" not in manifest:
            errors.append("Missing required 'claim' field")
            
        claim = manifest.get("claim", {})
        
        if "assertions" not in claim:
            errors.append("Missing required 'assertions' field in claim")
            
        # Check for required assertions
        assertions = claim.get("assertions", [])
        has_actions = any(a.get("label") == "c2pa.actions" for a in assertions)
        has_hash = any(a.get("label") == "c2pa.hash.data" for a in assertions)
        
        if not has_actions:
            warnings.append("Missing recommended 'c2pa.actions' assertion")
            
        if not has_hash:
            errors.append("Missing required 'c2pa.hash.data' assertion")
            
        # Validate assertion structure
        for i, assertion in enumerate(assertions):
            if "label" not in assertion:
                errors.append(f"Assertion {i} missing 'label' field")
            if "data" not in assertion:
                errors.append(f"Assertion {i} missing 'data' field")
                
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# Utility functions for C2PA compatibility

def convert_originmark_to_c2pa_hash(originmark_hash: str) -> str:
    """Convert OriginMark hash format to C2PA format if needed"""
    # Both use base64-encoded SHA256, so usually no conversion needed
    return originmark_hash

def create_c2pa_timestamp(dt: datetime) -> str:
    """Create C2PA-compliant timestamp"""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

def generate_c2pa_uuid() -> str:
    """Generate C2PA-compliant UUID"""
    return f"urn:uuid:{str(uuid.uuid4())}"


# Example usage
if __name__ == "__main__":
    # Example OriginMark signature
    example_signature = {
        "id": "test-123",
        "content_hash": "abc123...",
        "signature": "signature_data",
        "public_key": "public_key_data",
        "timestamp": "2023-12-20T10:00:00Z",
        "metadata": {
            "author": "Test User",
            "model_used": "GPT-4",
            "content_type": "text",
            "blockchain_enabled": True,
            "ipfs_hash": "QmX..."
        }
    }
    
    # Create exporter
    exporter = C2PAManifestExporter()
    
    # Export to JSON
    json_manifest = exporter.export_to_json(example_signature)
    print("C2PA Manifest (JSON):")
    print(json_manifest)
    
    # Validate
    manifest = json.loads(json_manifest)
    validation = exporter.validate_export(manifest)
    print(f"\nValidation: {validation}") 