# C2PA Integration for OriginMark

## Overview

C2PA (Coalition for Content Provenance and Authenticity) is an open technical standard that enables content creators to embed cryptographically verifiable metadata about content origin and editing history. This document outlines how to integrate C2PA compatibility into OriginMark.

## What is C2PA?

C2PA provides:
- **Content Credentials**: Cryptographically secure metadata that travels with digital assets
- **Tamper-evident signatures**: Any modification to content or metadata is detectable
- **Provenance chain**: Complete history from creation through all modifications
- **Industry standard**: Backed by Adobe, Microsoft, Intel, BBC, and others

## Why C2PA Matters for OriginMark

1. **Industry Adoption**: Major platforms and tools are adopting C2PA
2. **Complementary Technology**: C2PA and OriginMark can work together
3. **Enhanced Trust**: Dual verification through both systems
4. **Future-proofing**: Ensures compatibility with emerging standards

## Technical Integration Plan

### Phase 1: C2PA Manifest Export (Minimal MVP)

Create basic C2PA manifest export functionality:

```python
# api/c2pa_export.py
from typing import Dict, Any, Optional, List
import json
import base64
from datetime import datetime
import cbor2
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

class C2PAManifestExporter:
    """Export OriginMark signatures as C2PA manifests"""
    
    def __init__(self):
        self.version = "1.0"
        
    def create_c2pa_manifest(self, 
                            originmark_signature: Dict[str, Any],
                            asset_content: bytes,
                            additional_assertions: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """
        Create a C2PA manifest from OriginMark signature data
        """
        # Create assertions
        assertions = []
        
        # Add creation assertion
        assertions.append({
            "label": "c2pa.actions",
            "data": {
                "actions": [{
                    "action": "c2pa.created",
                    "when": originmark_signature["timestamp"],
                    "softwareAgent": {
                        "name": "OriginMark",
                        "version": "1.0"
                    }
                }]
            }
        })
        
        # Add data hash assertion
        assertions.append({
            "label": "c2pa.hash.data",
            "data": {
                "exclusions": [],
                "alg": "sha256",
                "hash": originmark_signature["content_hash"]
            }
        })
        
        # Add OriginMark signature as custom assertion
        assertions.append({
            "label": "org.originmark.signature",
            "data": {
                "signature_id": originmark_signature["id"],
                "signature": originmark_signature["signature"],
                "public_key": originmark_signature["public_key"],
                "author": originmark_signature.get("metadata", {}).get("author"),
                "model_used": originmark_signature.get("metadata", {}).get("model_used")
            }
        })
        
        # Add any additional assertions
        if additional_assertions:
            assertions.extend(additional_assertions)
        
        # Create claim
        claim = {
            "claim_generator": "OriginMark/1.0",
            "title": f"OriginMark Signature {originmark_signature['id']}",
            "thumbnail": None,
            "assertions": assertions,
            "alg": "es256",
            "signature": None  # Will be filled when signing
        }
        
        # Create manifest structure
        manifest = {
            "claim": claim,
            "validation_status": "valid",
            "signature": originmark_signature["signature"],  # Reuse OriginMark signature temporarily
        }
        
        return manifest
    
    def export_to_c2pa_sidecar(self, 
                              originmark_signature: Dict[str, Any],
                              output_path: str):
        """Export as C2PA sidecar file (.c2pa)"""
        manifest = self.create_c2pa_manifest(originmark_signature, b"")
        
        # JUMBF packaging would go here
        # For MVP, we'll export as JSON
        with open(output_path, 'w') as f:
            json.dump(manifest, f, indent=2)
```

### Phase 2: C2PA Manifest Import

```python
# api/c2pa_import.py
class C2PAManifestImporter:
    """Import and verify C2PA manifests"""
    
    def import_c2pa_manifest(self, manifest_data: bytes) -> Dict[str, Any]:
        """Import a C2PA manifest and extract relevant data"""
        # Parse JUMBF structure
        # Extract assertions
        # Verify signatures
        # Return normalized data
        pass
    
    def verify_c2pa_signature(self, manifest: Dict[str, Any]) -> bool:
        """Verify C2PA claim signature"""
        # Implement C2PA signature verification
        pass
```

### Phase 3: Full C2PA Compliance

1. **JUMBF Packaging**: Implement full JUMBF box structure
2. **Embedding**: Embed C2PA manifests in supported file formats
3. **Trust List**: Connect to C2PA trust list for certificate validation
4. **Conformance**: Apply for C2PA conformance certification

## API Endpoints

Add new endpoints for C2PA functionality:

```python
@app.get("/c2pa/export/{signature_id}")
async def export_c2pa_manifest(
    signature_id: str,
    format: str = "json",  # json, jumbf, sidecar
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Export OriginMark signature as C2PA manifest"""
    # Get signature from database
    signature = db.query(SignatureMetadata).filter(
        SignatureMetadata.id == signature_id
    ).first()
    
    if not signature:
        raise HTTPException(status_code=404, detail="Signature not found")
    
    # Create C2PA exporter
    exporter = C2PAManifestExporter()
    
    # Convert to C2PA manifest
    manifest = exporter.create_c2pa_manifest({
        "id": signature.id,
        "content_hash": signature.content_hash,
        "signature": signature.signature,
        "public_key": signature.public_key,
        "timestamp": signature.timestamp.isoformat(),
        "metadata": json.loads(signature.metadata_json)
    }, b"")
    
    if format == "json":
        return manifest
    else:
        # Return binary JUMBF format
        raise HTTPException(status_code=501, detail="JUMBF format not yet implemented")

@app.post("/c2pa/import")
async def import_c2pa_manifest(
    file: UploadFile = File(...),
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Import and verify a C2PA manifest"""
    # Read manifest
    content = await file.read()
    
    # Import and verify
    importer = C2PAManifestImporter()
    result = importer.import_c2pa_manifest(content)
    
    return {
        "valid": result.get("valid", False),
        "claims": result.get("claims", []),
        "originmark_compatible": result.get("has_originmark_assertion", False)
    }
```

## Implementation Roadmap

### Week 1-2: Basic Export
- [ ] Implement C2PA manifest structure
- [ ] Add export endpoint
- [ ] Create JSON export format
- [ ] Add to test suite

### Week 3-4: Standards Compliance
- [ ] Study C2PA specification v1.4
- [ ] Implement assertion types
- [ ] Add proper claim structure
- [ ] Certificate handling

### Week 5-6: Integration Testing
- [ ] Test with C2PA reference implementation
- [ ] Validate manifest structure
- [ ] Ensure cryptographic compatibility
- [ ] Document limitations

### Future: Full Compliance
- [ ] JUMBF box implementation
- [ ] File embedding for JPEG, PNG, MP4
- [ ] C2PA trust list integration
- [ ] Conformance testing

## Key C2PA Concepts for OriginMark

### Assertions
C2PA uses "assertions" to store different types of metadata:
- `c2pa.actions`: What was done to the content
- `c2pa.hash.data`: Cryptographic binding to content
- `c2pa.created`: Creation information
- Custom assertions: Can include OriginMark data

### Claims
A claim is a signed collection of assertions. OriginMark signatures can be:
1. Converted to C2PA claims
2. Included as custom assertions
3. Referenced as ingredients

### Manifest Store
C2PA manifests are stored in JUMBF format and can be:
- Embedded in files
- Stored as sidecar files
- Retrieved from manifest repositories

## Benefits of Integration

1. **Interoperability**: Work with Adobe, Microsoft tools
2. **Standards Compliance**: Follow industry best practices  
3. **Enhanced Metadata**: Richer provenance information
4. **Broader Adoption**: Tap into C2PA ecosystem
5. **Future Readiness**: Prepared for regulatory requirements

## Security Considerations

- C2PA uses similar cryptographic principles as OriginMark
- Both use digital signatures and hash chains
- C2PA adds certificate-based trust model
- Can leverage existing OriginMark security infrastructure

## Next Steps

1. **Review C2PA Specification**: Deep dive into v1.4 spec
2. **Prototype Export**: Build basic manifest export
3. **Test Interoperability**: Validate with C2PA tools
4. **Plan Certification**: Prepare for conformance program
5. **Update Documentation**: Add C2PA to user guides

## Resources

- [C2PA Specification v1.4](https://c2pa.org/specifications/)
- [C2PA Implementation Guide](https://c2pa.org/specifications/specifications/1.4/guidance/Guidance.html)
- [JUMBF Specification](https://www.iso.org/standard/81634.html)
- [C2PA SDK (Rust)](https://github.com/contentauth/c2pa-rs)
- [C2PA Conformance Program](https://c2pa.org/conformance/)

## Conclusion

Integrating C2PA into OriginMark will:
- Maintain OriginMark's unique features (blockchain, IPFS, OpenAI integration)
- Add industry-standard provenance format
- Enable interoperability with major platforms
- Position OriginMark as a comprehensive solution

The phased approach allows for quick MVP delivery while building toward full compliance. 