from fastapi import FastAPI, UploadFile, File, HTTPException, Depends, Header, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import Optional, List
import nacl.signing
import nacl.encoding
import nacl.hash
import hashlib
import base64
import json
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from db import (get_db, SignatureMetadata, User, APIKey, generate_api_key, hash_api_key,
                MultiSignatureDocument, SignatureChain, SignatureRequest, UserKeyPair, 
                KeyRotationHistory, UserWhitelist, UserBlacklist, CloudStorageIntegration,
                UsageMetrics, DailyMetricsSummary, UserFeedback)
from webhooks import webhook_manager, notify_signature_created, WebhookConfig, WebhookType, WebhookEvent
from ipfs_storage import get_ipfs_storage, store_signature_to_ipfs
from reputation_system import get_user_reputation, get_reputation_leaderboard
from c2pa_export import C2PAManifestExporter
import os
import bcrypt
from telemetry import telemetry
from fastapi import Request
import time

app = FastAPI(title="OriginMark API", version="2.0.0")
security = HTTPBearer(auto_error=False)

# CORS Configuration - configurable via environment variable
# In production, set CORS_ORIGINS to comma-separated list of allowed origins
# Example: CORS_ORIGINS="https://originmark.dev,https://app.originmark.dev"
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")
if CORS_ORIGINS == ["*"]:
    # Development mode - allow all origins
    cors_origins = ["*"]
else:
    # Production mode - use specified origins
    cors_origins = [origin.strip() for origin in CORS_ORIGINS]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add middleware to track request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    # Store for telemetry use
    request.state.process_time_ms = int(process_time * 1000)
    return response

# Pydantic models
class SignRequest(BaseModel):
    content: str
    author: Optional[str] = None
    model_used: Optional[str] = None
    content_type: str = "text"
    private_key: Optional[str] = None

class VerifyRequest(BaseModel):
    content: str
    signature: str
    public_key: str

class SignatureResponse(BaseModel):
    id: str
    content_hash: str
    signature: str
    public_key: str
    timestamp: str
    metadata: dict

class CreateAPIKeyRequest(BaseModel):
    name: str
    description: Optional[str] = None
    rate_limit: Optional[int] = 1000

class CreateUserRequest(BaseModel):
    email: str
    username: str
    password: str

class CreateWebhookRequest(BaseModel):
    name: str
    url: str
    type: WebhookType
    events: list[WebhookEvent]
    secret: Optional[str] = None

# Multi-signature models
class CreateMultiSigDocumentRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    required_signatures: int = 2
    expires_in_hours: Optional[int] = 168  # 7 days default
    signers: List[str] = []  # List of user IDs or emails

class AddSignatureRequest(BaseModel):
    document_id: str
    private_key: Optional[str] = None
    notes: Optional[str] = None

class CreateSignatureRequestModel(BaseModel):
    document_id: str
    requested_from: str  # User ID or email
    message: Optional[str] = None
    expires_in_hours: Optional[int] = 168  # 7 days default

# Key management models
class CreateKeyPairRequest(BaseModel):
    key_name: str
    is_primary: Optional[bool] = False
    backup_location: Optional[str] = None

class RotateKeyRequest(BaseModel):
    key_pair_id: str
    reason: str = "manual"

# Browser extension models
class WhitelistRequest(BaseModel):
    domain: str

class BlacklistRequest(BaseModel):
    domain: str

# Authentication functions
async def get_api_key(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Authenticate using API key"""
    if not credentials:
        return None
    
    api_key = credentials.credentials
    if not api_key.startswith('om_'):
        raise HTTPException(status_code=401, detail="Invalid API key format")
    
    # Hash the provided key
    key_hash = hash_api_key(api_key)
    
    # Find the API key in database
    db_key = db.query(APIKey).filter(
        APIKey.key_hash == key_hash,
        APIKey.is_active == True
    ).first()
    
    if not db_key:
        raise HTTPException(status_code=401, detail="Invalid or inactive API key")
    
    # Update usage statistics
    db_key.last_used = datetime.now(timezone.utc)
    db_key.usage_count += 1
    db.commit()
    
    return db_key

async def get_optional_api_key(credentials: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    """Optionally authenticate using API key"""
    if not credentials:
        return None
    
    try:
        return await get_api_key(credentials, db)
    except HTTPException:
        return None

def compute_hash(content: bytes) -> str:
    """Compute SHA256 hash of content"""
    return hashlib.sha256(content).hexdigest()

@app.get("/")
async def root():
    return {"message": "OriginMark API - Digital signature service for AI content with authentication"}

# User Management Endpoints
@app.post("/auth/register")
async def register_user(user_data: CreateUserRequest, db: Session = Depends(get_db)):
    """Register a new user"""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(status_code=400, detail="User already exists")
    
    # Hash password using bcrypt (industry-standard secure password hashing)
    # bcrypt automatically handles salting and uses a work factor for computational cost
    password_hash = bcrypt.hashpw(user_data.password.encode(), bcrypt.gensalt()).decode()
    
    # Create user
    user_id = str(uuid.uuid4())
    new_user = User(
        id=user_id,
        email=user_data.email,
        username=user_data.username,
        password_hash=password_hash
    )
    
    db.add(new_user)
    db.commit()
    
    return {"message": "User registered successfully", "user_id": user_id}


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its bcrypt hash"""
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


class LoginRequest(BaseModel):
    username: str
    password: str


@app.post("/auth/login")
async def login_user(login_data: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate a user and return API key"""
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == login_data.username) | (User.email == login_data.username)
    ).first()
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password using bcrypt
    if not verify_password(login_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Generate or return existing API key
    existing_key = db.query(APIKey).filter(
        APIKey.user_id == user.id,
        APIKey.is_active == True
    ).first()
    
    if existing_key:
        # Return a message that they already have an active key
        return {
            "message": "Login successful",
            "user_id": user.id,
            "username": user.username,
            "has_api_key": True
        }
    
    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "has_api_key": False
    }


# API Key Management Endpoints
@app.post("/auth/api-keys")
async def create_api_key(
    key_data: CreateAPIKeyRequest,
    user_id: str,  # In production, get this from JWT token
    db: Session = Depends(get_db)
):
    """Create a new API key for a user"""
    # Generate API key
    api_key = generate_api_key()
    key_hash = hash_api_key(api_key)
    
    # Create API key record
    key_id = str(uuid.uuid4())
    new_key = APIKey(
        id=key_id,
        user_id=user_id,
        key_hash=key_hash,
        name=key_data.name,
        description=key_data.description,
        rate_limit=key_data.rate_limit
    )
    
    db.add(new_key)
    db.commit()
    
    return {
        "message": "API key created successfully",
        "api_key": api_key,  # Only shown once
        "key_id": key_id,
        "name": key_data.name
    }

@app.get("/auth/api-keys")
async def list_api_keys(user_id: str, db: Session = Depends(get_db)):
    """List all API keys for a user"""
    keys = db.query(APIKey).filter(
        APIKey.user_id == user_id,
        APIKey.is_active == True
    ).all()
    
    return {
        "api_keys": [
            {
                "id": key.id,
                "name": key.name,
                "description": key.description,
                "created_at": key.created_at.isoformat(),
                "last_used": key.last_used.isoformat() if key.last_used else None,
                "usage_count": key.usage_count,
                "rate_limit": key.rate_limit
            }
            for key in keys
        ]
    }

@app.delete("/auth/api-keys/{key_id}")
async def revoke_api_key(key_id: str, user_id: str, db: Session = Depends(get_db)):
    """Revoke an API key"""
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.user_id == user_id
    ).first()
    
    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    api_key.is_active = False
    db.commit()
    
    return {"message": "API key revoked successfully"}

# Webhook Management Endpoints
@app.post("/webhooks")
async def create_webhook(
    webhook_data: CreateWebhookRequest,
    user_id: str,  # In production, get this from JWT token
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Create a new webhook"""
    webhook_id = str(uuid.uuid4())
    
    webhook_config = WebhookConfig(
        id=webhook_id,
        name=webhook_data.name,
        url=webhook_data.url,
        type=webhook_data.type,
        events=webhook_data.events,
        secret=webhook_data.secret
    )
    
    webhook_manager.webhooks[webhook_id] = webhook_config
    
    return {
        "message": "Webhook created successfully",
        "webhook_id": webhook_id,
        "name": webhook_data.name,
        "type": webhook_data.type
    }

@app.get("/webhooks")
async def list_webhooks(
    user_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    """List all webhooks for a user"""
    # In a real implementation, you would filter by user_id
    webhooks = [
        {
            "id": webhook.id,
            "name": webhook.name,
            "url": str(webhook.url),
            "type": webhook.type,
            "events": webhook.events,
            "is_active": webhook.is_active
        }
        for webhook in webhook_manager.webhooks.values()
    ]
    
    return {"webhooks": webhooks}

@app.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    user_id: str,
    api_key: APIKey = Depends(get_api_key)
):
    """Delete a webhook"""
    if webhook_id in webhook_manager.webhooks:
        del webhook_manager.webhooks[webhook_id]
        return {"message": "Webhook deleted successfully"}
    else:
        raise HTTPException(status_code=404, detail="Webhook not found")

@app.post("/sign", response_model=SignatureResponse)
async def sign_content(
    request: Request,
    file: Optional[UploadFile] = File(None),
    author: Optional[str] = None,
    model_used: Optional[str] = None,
    private_key: Optional[str] = None,
    format: Optional[str] = None,
    api_key: Optional[APIKey] = Depends(get_optional_api_key),
    db: Session = Depends(get_db)
):
    """Sign content with Ed25519 signature"""
    start_time = time.time()
    try:
        # Read content
        if file:
            content = await file.read()
            content_type = "image" if file.content_type and file.content_type.startswith("image") else "text"
            file_name = file.filename
            file_size = len(content)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "No content provided"}
            )
        
        # Generate or use provided key pair
        if private_key:
            # Decode the provided private key
            signing_key = nacl.signing.SigningKey(
                base64.b64decode(private_key)
            )
        else:
            # Generate new key pair
            signing_key = nacl.signing.SigningKey.generate()
        
        verify_key = signing_key.verify_key
        
        # Compute hash
        content_hash = compute_hash(content)
        
        # Sign the hash
        signed = signing_key.sign(content_hash.encode())
        signature = base64.b64encode(signed.signature).decode()
        
        # Create metadata
        signature_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        metadata = {
            "author": author or "Anonymous",
            "timestamp": timestamp.isoformat(),
            "content_type": content_type,
            "model_used": model_used,
            "file_name": file_name,
            "file_size": file_size
        }
        
        # Store in database
        db_signature = SignatureMetadata(
            id=signature_id,
            user_id=api_key.user_id if api_key else None,
            api_key_id=api_key.id if api_key else None,
            content_hash=content_hash,
            signature=signature,
            public_key=base64.b64encode(bytes(verify_key)).decode(),
            author=author,
            timestamp=timestamp,
            content_type=content_type,
            ai_model_used=model_used,
            file_name=file_name,
            file_size=file_size,
            metadata_json=json.dumps(metadata)
        )
        db.add(db_signature)
        db.commit()
        
        # Save sidecar JSON file
        sidecar_data = {
            "id": signature_id,
            "content_hash": content_hash,
            "signature": signature,
            "public_key": base64.b64encode(bytes(verify_key)).decode(),
            "private_key": base64.b64encode(bytes(signing_key)).decode() if not private_key else None,
            "metadata": metadata
        }
        
        # Prepare response
        signature_response = SignatureResponse(
            id=signature_id,
            content_hash=content_hash,
            signature=signature,
            public_key=base64.b64encode(bytes(verify_key)).decode(),
            timestamp=timestamp.isoformat(),
            metadata=metadata
        )
        
        # Send webhook notification
        try:
            await notify_signature_created({
                "id": signature_id,
                "content_hash": content_hash,
                "metadata": metadata
            })
        except Exception as e:
            # Don't fail the request if webhook fails
            print(f"Webhook notification failed: {e}")
        
        # Track telemetry
        response_time_ms = int((time.time() - start_time) * 1000)
        await telemetry.track_usage(
            db=db,
            action="sign",
            user_id=api_key.user_id if api_key else None,
            api_key_id=api_key.id if api_key else None,
            content_type=content_type,
            status_code=200,
            response_time_ms=response_time_ms,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={
                "file_size": file_size,
                "model_used": model_used,
                "has_private_key": bool(private_key),
                "export_format": format
            }
        )
        
        # Handle C2PA export format
        if format and format.lower() == "c2pa":
            try:
                c2pa_exporter = C2PAManifestExporter()
                
                # Prepare OriginMark signature data for C2PA export
                originmark_data = {
                    "id": signature_id,
                    "content_hash": content_hash,
                    "signature": signature,
                    "public_key": base64.b64encode(bytes(verify_key)).decode(),
                    "timestamp": timestamp.isoformat(),
                    "metadata": metadata
                }
                
                # Create C2PA manifest
                c2pa_manifest = c2pa_exporter.create_c2pa_manifest(originmark_data)
                
                # Validate the manifest
                validation = c2pa_exporter.validate_export(c2pa_manifest)
                if not validation["valid"]:
                    print(f"C2PA validation warnings: {validation['warnings']}")
                    print(f"C2PA validation errors: {validation['errors']}")
                
                # Return C2PA manifest instead of standard response
                return JSONResponse(
                    status_code=200,
                    content={
                        "format": "c2pa",
                        "manifest": c2pa_manifest,
                        "originmark_signature": {
                            "id": signature_id,
                            "content_hash": content_hash,
                            "signature": signature,
                            "public_key": base64.b64encode(bytes(verify_key)).decode(),
                            "timestamp": timestamp.isoformat()
                        },
                        "validation": validation
                    }
                )
                
            except Exception as c2pa_error:
                # If C2PA export fails, log error but return standard response
                print(f"C2PA export failed: {c2pa_error}")
                signature_response.metadata["c2pa_export_error"] = str(c2pa_error)
        
        return signature_response
        
    except Exception as e:
        # Track error telemetry
        response_time_ms = int((time.time() - start_time) * 1000)
        await telemetry.track_usage(
            db=db,
            action="sign",
            user_id=api_key.user_id if api_key else None,
            api_key_id=api_key.id if api_key else None,
            content_type=content_type if 'content_type' in locals() else None,
            status_code=500,
            response_time_ms=response_time_ms,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/signatures/{signature_id}/c2pa")
async def export_signature_c2pa(
    signature_id: str,
    api_key: Optional[APIKey] = Depends(get_optional_api_key),
    db: Session = Depends(get_db)
):
    """Export existing signature as C2PA manifest"""
    try:
        # Get signature from database
        db_signature = db.query(SignatureMetadata).filter(
            SignatureMetadata.id == signature_id
        ).first()
        
        if not db_signature:
            raise HTTPException(status_code=404, detail="Signature not found")
        
        # Prepare OriginMark signature data
        originmark_data = {
            "id": db_signature.id,
            "content_hash": db_signature.content_hash,
            "signature": db_signature.signature,
            "public_key": db_signature.public_key,
            "timestamp": db_signature.timestamp.isoformat(),
            "metadata": {
                "author": db_signature.author,
                "model_used": db_signature.ai_model_used,
                "content_type": db_signature.content_type,
                "file_name": db_signature.file_name,
                "file_size": db_signature.file_size
            }
        }
        
        # Create C2PA manifest
        c2pa_exporter = C2PAManifestExporter()
        c2pa_manifest = c2pa_exporter.create_c2pa_manifest(originmark_data)
        
        # Validate the manifest
        validation = c2pa_exporter.validate_export(c2pa_manifest)
        
        return JSONResponse(
            status_code=200,
            content={
                "format": "c2pa",
                "signature_id": signature_id,
                "manifest": c2pa_manifest,
                "validation": validation,
                "export_info": {
                    "specification": "C2PA v1.4",
                    "exporter": "OriginMark/2.0.0",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "compatibility": "Adobe Content Authenticity Initiative"
                }
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"C2PA export failed: {str(e)}")

@app.post("/verify")
async def verify_content(
    request: Request,
    file: Optional[UploadFile] = File(None),
    signature: Optional[str] = Form(None),
    public_key: Optional[str] = Form(None),
    signature_id: Optional[str] = Form(None),
    api_key: Optional[APIKey] = Depends(get_optional_api_key),
    db: Session = Depends(get_db)
):
    """Verify content signature"""
    start_time = time.time()
    try:
        # Get signature metadata from DB if ID provided
        if signature_id:
            db_signature = db.query(SignatureMetadata).filter(
                SignatureMetadata.id == signature_id
            ).first()
            if not db_signature:
                return {"valid": False, "message": "Signature not found"}
            signature = db_signature.signature
            public_key = db_signature.public_key
            stored_hash = db_signature.content_hash
        
        if not signature or not public_key:
            return JSONResponse(
                status_code=400,
                content={"error": "Signature and public key required"}
            )
        
        # Read content
        if file:
            content = await file.read()
        else:
            return JSONResponse(
                status_code=400,
                content={"error": "No content provided"}
            )
        
        # Compute hash
        content_hash = compute_hash(content)
        
        # Verify against stored hash if available
        if signature_id and stored_hash != content_hash:
            # Track telemetry for failed verification
            response_time_ms = int((time.time() - start_time) * 1000)
            await telemetry.track_usage(
                db=db,
                action="verify",
                user_id=api_key.user_id if api_key else None,
                api_key_id=api_key.id if api_key else None,
                content_type=file.content_type if file else None,
                status_code=200,
                response_time_ms=response_time_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"result": "hash_mismatch", "signature_id": signature_id}
            )
            return {
                "valid": False,
                "message": "Content hash mismatch",
                "computed_hash": content_hash,
                "stored_hash": stored_hash
            }
        
        # Verify signature
        verify_key = nacl.signing.VerifyKey(base64.b64decode(public_key))
        
        try:
            verify_key.verify(
                content_hash.encode(),
                base64.b64decode(signature)
            )
            
            # Get metadata if signature ID provided
            metadata = None
            if signature_id and db_signature:
                metadata = json.loads(db_signature.metadata_json) if db_signature.metadata_json else None
            
            # Track successful verification
            response_time_ms = int((time.time() - start_time) * 1000)
            await telemetry.track_usage(
                db=db,
                action="verify",
                user_id=api_key.user_id if api_key else None,
                api_key_id=api_key.id if api_key else None,
                content_type=file.content_type if file else None,
                status_code=200,
                response_time_ms=response_time_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"result": "valid", "signature_id": signature_id}
            )
            return {
                "valid": True,
                "message": "Signature verified successfully",
                "content_hash": content_hash,
                "metadata": metadata
            }
        except nacl.exceptions.BadSignatureError:
            # Track failed verification
            response_time_ms = int((time.time() - start_time) * 1000)
            await telemetry.track_usage(
                db=db,
                action="verify",
                user_id=api_key.user_id if api_key else None,
                api_key_id=api_key.id if api_key else None,
                content_type=file.content_type if file else None,
                status_code=200,
                response_time_ms=response_time_ms,
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent"),
                metadata={"result": "invalid_signature"}
            )
            return {
                "valid": False,
                "message": "Invalid signature",
                "content_hash": content_hash
            }
            
    except Exception as e:
        # Track error telemetry
        response_time_ms = int((time.time() - start_time) * 1000)
        await telemetry.track_usage(
            db=db,
            action="verify",
            user_id=api_key.user_id if api_key else None,
            api_key_id=api_key.id if api_key else None,
            content_type=None,
            status_code=500,
            response_time_ms=response_time_ms,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/badge")
async def get_badge(id: str, db: Session = Depends(get_db)):
    """Generate verification badge HTML"""
    db_signature = db.query(SignatureMetadata).filter(
        SignatureMetadata.id == id
    ).first()
    
    if not db_signature:
        raise HTTPException(status_code=404, detail="Signature not found")
    
    metadata = json.loads(db_signature.metadata_json) if db_signature.metadata_json else {}
    
    badge_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OriginMark Verification Badge</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            }}
            .badge {{
                background: white;
                border-radius: 8px;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 400px;
                margin: 0 auto;
            }}
            .verified {{
                color: #22c55e;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 10px;
            }}
            .details {{
                font-size: 14px;
                color: #666;
                margin-top: 10px;
            }}
            .hash {{
                font-family: monospace;
                font-size: 12px;
                background: #f0f0f0;
                padding: 5px;
                border-radius: 4px;
                word-break: break-all;
            }}
        </style>
    </head>
    <body>
        <div class="badge">
            <div class="verified">✓ Verified AI Content</div>
            <div class="details">
                <p><strong>Author:</strong> {metadata.get('author', 'Unknown')}</p>
                <p><strong>Model:</strong> {metadata.get('model_used', 'Not specified')}</p>
                <p><strong>Timestamp:</strong> {metadata.get('timestamp', 'Unknown')}</p>
                <p><strong>Content Type:</strong> {metadata.get('content_type', 'Unknown')}</p>
                <p><strong>Hash:</strong></p>
                <div class="hash">{db_signature.content_hash}</div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return HTMLResponse(content=badge_html)

@app.get("/signatures/{signature_id}")
async def get_signature(signature_id: str, db: Session = Depends(get_db)):
    """Get signature metadata by ID"""
    db_signature = db.query(SignatureMetadata).filter(
        SignatureMetadata.id == signature_id
    ).first()
    
    if not db_signature:
        raise HTTPException(status_code=404, detail="Signature not found")
    
    metadata = json.loads(db_signature.metadata_json) if db_signature.metadata_json else {}
    
    return {
        "id": db_signature.id,
        "content_hash": db_signature.content_hash,
        "signature": db_signature.signature,
        "public_key": db_signature.public_key,
        "timestamp": db_signature.timestamp.isoformat(),
        "metadata": metadata
    }

@app.get("/users/{user_id}/signatures")
async def get_user_signatures(
    user_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get all signatures for a user"""
    # Ensure API key belongs to the requested user
    if api_key.user_id != user_id:
        raise HTTPException(status_code=403, detail="Access denied")
    
    signatures = db.query(SignatureMetadata).filter(
        SignatureMetadata.user_id == user_id
    ).order_by(SignatureMetadata.timestamp.desc()).all()
    
    return {
        "signatures": [
            {
                "id": sig.id,
                "content_hash": sig.content_hash,
                "author": sig.author,
                "timestamp": sig.timestamp.isoformat(),
                "content_type": sig.content_type,
                "model_used": sig.ai_model_used,
                "file_name": sig.file_name
            }
            for sig in signatures
        ]
    }

# Phase 3: Blockchain Integration Endpoints

@app.post("/blockchain/sign")
async def sign_to_blockchain(
    file: UploadFile = File(...),
    author: Optional[str] = None,
    model_used: Optional[str] = None,
    store_on_ipfs: bool = True,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Sign content and store on blockchain + IPFS"""
    try:
        content = await file.read()
        content_hash = compute_hash(content)
        
        # Store to IPFS if requested
        ipfs_hash = None
        if store_on_ipfs:
            try:
                signature_data = {
                    "author": author,
                    "model_used": model_used,
                    "content_type": file.content_type or "application/octet-stream",
                    "file_name": file.filename,
                    "signature_id": str(uuid.uuid4())
                }
                ipfs_hash = await store_signature_to_ipfs(content, signature_data)
            except Exception as e:
                print(f"IPFS storage failed: {e}")
        
        # Regular signature process
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        signed = signing_key.sign(content_hash.encode())
        signature = base64.b64encode(signed.signature).decode()
        
        # Store in database with blockchain info
        signature_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        metadata = {
            "author": author or "Anonymous",
            "timestamp": timestamp.isoformat(),
            "content_type": file.content_type or "application/octet-stream",
            "model_used": model_used,
            "file_name": file.filename,
            "file_size": len(content),
            "ipfs_hash": ipfs_hash,
            "blockchain_enabled": True
        }
        
        db_signature = SignatureMetadata(
            id=signature_id,
            user_id=api_key.user_id,
            api_key_id=api_key.id,
            content_hash=content_hash,
            signature=signature,
            public_key=base64.b64encode(bytes(verify_key)).decode(),
            author=author,
            timestamp=timestamp,
            content_type=file.content_type or "application/octet-stream",
            ai_model_used=model_used,
            file_name=file.filename,
            file_size=len(content),
            metadata_json=json.dumps(metadata)
        )
        db.add(db_signature)
        db.commit()
        
        return {
            "id": signature_id,
            "content_hash": content_hash,
            "signature": signature,
            "public_key": base64.b64encode(bytes(verify_key)).decode(),
            "private_key": base64.b64encode(bytes(signing_key)).decode(),
            "timestamp": timestamp.isoformat(),
            "ipfs_hash": ipfs_hash,
            "metadata": metadata,
            "blockchain_ready": True
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/blockchain/verify/{content_hash}")
async def verify_on_blockchain(content_hash: str, db: Session = Depends(get_db)):
    """Verify signature exists on blockchain"""
    db_signature = db.query(SignatureMetadata).filter(
        SignatureMetadata.content_hash == content_hash
    ).first()
    
    if not db_signature:
        return {"exists": False, "message": "Signature not found"}
    
    metadata = json.loads(db_signature.metadata_json) if db_signature.metadata_json else {}
    
    # Mock blockchain verification (in reality, would query smart contract)
    blockchain_verified = metadata.get("blockchain_enabled", False)
    
    return {
        "exists": True,
        "blockchain_verified": blockchain_verified,
        "signer": db_signature.public_key,
        "timestamp": db_signature.timestamp.isoformat(),
        "ipfs_hash": metadata.get("ipfs_hash"),
        "metadata": metadata
    }

@app.get("/reputation/{user_id}")
async def get_user_reputation_score(
    user_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get reputation score for a user"""
    try:
        reputation = get_user_reputation(user_id, db)
        
        return {
            "user_id": user_id,
            "overall_score": reputation.overall_score,
            "trust_score": reputation.trust_score,
            "activity_score": reputation.activity_score,
            "community_score": reputation.community_score,
            "expert_score": reputation.expert_score,
            "consistency_score": reputation.consistency_score,
            "total_signatures": reputation.total_signatures,
            "verified_signatures": reputation.verified_signatures,
            "disputed_signatures": reputation.disputed_signatures,
            "community_votes": reputation.community_votes
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/reputation/leaderboard")
async def get_reputation_leaderboard(
    limit: int = 50,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get reputation leaderboard"""
    try:
        leaderboard = get_reputation_leaderboard(limit, db)
        return {"leaderboard": leaderboard}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ipfs/store")
async def store_to_ipfs(
    file: UploadFile = File(...),
    metadata: Optional[str] = None,
    api_key: APIKey = Depends(get_api_key)
):
    """Store content to IPFS"""
    try:
        content = await file.read()
        
        signature_data = {
            "content_type": file.content_type or "application/octet-stream",
            "file_name": file.filename,
            "file_size": len(content),
            "user_id": api_key.user_id
        }
        
        if metadata:
            try:
                metadata_dict = json.loads(metadata)
                signature_data.update(metadata_dict)
            except json.JSONDecodeError:
                pass
        
        ipfs_hash = await store_signature_to_ipfs(content, signature_data)
        
        return {
            "ipfs_hash": ipfs_hash,
            "content_size": len(content),
            "content_type": file.content_type,
            "message": "Content stored successfully on IPFS"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/ipfs/retrieve/{ipfs_hash}")
async def retrieve_from_ipfs(ipfs_hash: str, api_key: APIKey = Depends(get_api_key)):
    """Retrieve content from IPFS"""
    try:
        from ipfs_storage import retrieve_signature_from_ipfs
        content, metadata = await retrieve_signature_from_ipfs(ipfs_hash)
        
        return {
            "content_size": len(content),
            "content_hash": hashlib.sha256(content).hexdigest(),
            "metadata": metadata,
            "message": "Content retrieved successfully from IPFS"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Multi-signature endpoints
@app.post("/multi-signature/documents")
async def create_multi_signature_document(
    file: UploadFile = File(...),
    request_data: CreateMultiSigDocumentRequest = Depends(),
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Create a new multi-signature document"""
    try:
        # Read content and compute hash
        content = await file.read()
        content_hash = compute_hash(content)
        
        # Create document record
        document_id = str(uuid.uuid4())
        expires_at = None
        if request_data.expires_in_hours:
            expires_at = datetime.now(timezone.utc) + timedelta(hours=request_data.expires_in_hours)
        
        document = MultiSignatureDocument(
            id=document_id,
            content_hash=content_hash,
            title=request_data.title or file.filename,
            description=request_data.description,
            created_by=api_key.user_id,
            required_signatures=request_data.required_signatures,
            expires_at=expires_at,
            metadata_json=json.dumps({
                "file_name": file.filename,
                "file_size": len(content),
                "content_type": file.content_type
            })
        )
        
        db.add(document)
        db.flush()  # Get the ID
        
        # Create signature requests for specified signers
        for signer in request_data.signers:
            request_id = str(uuid.uuid4())
            sig_request = SignatureRequest(
                id=request_id,
                document_id=document_id,
                requested_by=api_key.user_id,
                requested_from=signer,
                expires_at=expires_at
            )
            db.add(sig_request)
        
        db.commit()
        
        return {
            "document_id": document_id,
            "content_hash": content_hash,
            "required_signatures": request_data.required_signatures,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "signature_requests_created": len(request_data.signers)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/multi-signature/sign")
async def add_signature_to_document(
    file: UploadFile = File(...),
    request_data: AddSignatureRequest = Depends(),
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Add a signature to a multi-signature document"""
    try:
        # Get document
        document = db.query(MultiSignatureDocument).filter(
            MultiSignatureDocument.id == request_data.document_id
        ).first()
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        if document.status != "pending":
            raise HTTPException(status_code=400, detail="Document is not pending signatures")
        
        if document.expires_at and document.expires_at < datetime.now(timezone.utc):
            document.status = "expired"
            db.commit()
            raise HTTPException(status_code=400, detail="Document has expired")
        
        # Verify content matches
        content = await file.read()
        content_hash = compute_hash(content)
        
        if content_hash != document.content_hash:
            raise HTTPException(status_code=400, detail="Content hash mismatch")
        
        # Check if user already signed
        existing_chain = db.query(SignatureChain).filter(
            SignatureChain.document_id == request_data.document_id,
            SignatureChain.signer_user_id == api_key.user_id
        ).first()
        
        if existing_chain:
            raise HTTPException(status_code=400, detail="User has already signed this document")
        
        # Create signature
        if request_data.private_key:
            signing_key = nacl.signing.SigningKey(base64.b64decode(request_data.private_key))
        else:
            # Use user's primary key
            user_key = db.query(UserKeyPair).filter(
                UserKeyPair.user_id == api_key.user_id,
                UserKeyPair.is_primary == True,
                UserKeyPair.is_active == True
            ).first()
            
            if not user_key:
                raise HTTPException(status_code=400, detail="No primary key found. Please provide private_key or set up a primary key.")
            
            # In production, decrypt the private key here
            signing_key = nacl.signing.SigningKey.generate()  # Placeholder
        
        verify_key = signing_key.verify_key
        
        # Sign the content hash
        signed = signing_key.sign(content_hash.encode())
        signature = base64.b64encode(signed.signature).decode()
        
        # Create signature metadata
        signature_id = str(uuid.uuid4())
        db_signature = SignatureMetadata(
            id=signature_id,
            user_id=api_key.user_id,
            api_key_id=api_key.id,
            content_hash=content_hash,
            signature=signature,
            public_key=base64.b64encode(bytes(verify_key)).decode(),
            timestamp=datetime.now(timezone.utc),
            content_type="document",
            file_name=file.filename,
            file_size=len(content),
            metadata_json=json.dumps({
                "multi_signature_document_id": request_data.document_id,
                "signature_order": document.current_signatures + 1
            })
        )
        db.add(db_signature)
        db.flush()
        
        # Add to signature chain
        chain_id = str(uuid.uuid4())
        
        # Get previous signature for chain reference
        previous_chain = db.query(SignatureChain).filter(
            SignatureChain.document_id == request_data.document_id
        ).order_by(SignatureChain.signature_order.desc()).first()
        
        signature_chain = SignatureChain(
            id=chain_id,
            document_id=request_data.document_id,
            signature_id=signature_id,
            signer_user_id=api_key.user_id,
            signature_order=document.current_signatures + 1,
            previous_signature_id=previous_chain.signature_id if previous_chain else None,
            notes=request_data.notes
        )
        db.add(signature_chain)
        
        # Update document
        document.current_signatures += 1
        if document.current_signatures >= document.required_signatures:
            document.status = "completed"
            document.completed_at = datetime.now(timezone.utc)
        
        db.commit()
        
        return {
            "signature_id": signature_id,
            "signature_order": signature_chain.signature_order,
            "document_status": document.status,
            "signatures_remaining": max(0, document.required_signatures - document.current_signatures)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/multi-signature/documents/{document_id}")
async def get_multi_signature_document(
    document_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get multi-signature document details and signature chain"""
    document = db.query(MultiSignatureDocument).filter(
        MultiSignatureDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Get signature chain
    signatures = db.query(SignatureChain).filter(
        SignatureChain.document_id == document_id
    ).order_by(SignatureChain.signature_order).all()
    
    signature_details = []
    for sig_chain in signatures:
        sig_metadata = db.query(SignatureMetadata).filter(
            SignatureMetadata.id == sig_chain.signature_id
        ).first()
        
        user = db.query(User).filter(User.id == sig_chain.signer_user_id).first()
        
        signature_details.append({
            "signature_id": sig_chain.signature_id,
            "signer": user.username if user else "Unknown",
            "signature_order": sig_chain.signature_order,
            "timestamp": sig_chain.timestamp.isoformat(),
            "signature": sig_metadata.signature if sig_metadata else None,
            "public_key": sig_metadata.public_key if sig_metadata else None,
            "notes": sig_chain.notes
        })
    
    return {
        "document_id": document.id,
        "title": document.title,
        "description": document.description,
        "content_hash": document.content_hash,
        "status": document.status,
        "required_signatures": document.required_signatures,
        "current_signatures": document.current_signatures,
        "created_at": document.created_at.isoformat(),
        "completed_at": document.completed_at.isoformat() if document.completed_at else None,
        "expires_at": document.expires_at.isoformat() if document.expires_at else None,
        "signature_chain": signature_details
    }

@app.post("/multi-signature/aggregate")
async def aggregate_signatures(
    document_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Aggregate all signatures for a completed multi-signature document"""
    document = db.query(MultiSignatureDocument).filter(
        MultiSignatureDocument.id == document_id
    ).first()
    
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    
    if document.status != "completed":
        raise HTTPException(status_code=400, detail="Document is not completed")
    
    # Get all signatures in order
    signatures = db.query(SignatureChain).filter(
        SignatureChain.document_id == document_id
    ).order_by(SignatureChain.signature_order).all()
    
    aggregated_signatures = []
    public_keys = []
    
    for sig_chain in signatures:
        sig_metadata = db.query(SignatureMetadata).filter(
            SignatureMetadata.id == sig_chain.signature_id
        ).first()
        
        if sig_metadata:
            aggregated_signatures.append(sig_metadata.signature)
            public_keys.append(sig_metadata.public_key)
    
    # Create aggregated signature record
    aggregated_id = str(uuid.uuid4())
    aggregated_signature = SignatureMetadata(
        id=aggregated_id,
        user_id=document.created_by,
        content_hash=document.content_hash,
        signature=json.dumps(aggregated_signatures),  # Store as JSON array
        public_key=json.dumps(public_keys),  # Store as JSON array
        timestamp=datetime.now(timezone.utc),
        content_type="aggregated",
        metadata_json=json.dumps({
            "multi_signature_document_id": document_id,
            "signature_count": len(aggregated_signatures),
            "is_aggregated": True
        })
    )
    db.add(aggregated_signature)
    
    # Add to chain as aggregated signature
    chain_id = str(uuid.uuid4())
    signature_chain = SignatureChain(
        id=chain_id,
        document_id=document_id,
        signature_id=aggregated_id,
        signer_user_id=document.created_by,
        signature_order=len(signatures) + 1,
        signature_type="aggregated"
    )
    db.add(signature_chain)
    
    db.commit()
    
    return {
        "aggregated_signature_id": aggregated_id,
        "signature_count": len(aggregated_signatures),
        "aggregated_signature": json.dumps(aggregated_signatures),
        "public_keys": json.dumps(public_keys)
    }

@app.get("/multi-signature/requests")
async def list_signature_requests(
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """List signature requests for the current user"""
    requests = db.query(SignatureRequest).filter(
        SignatureRequest.requested_from == api_key.user_id,
        SignatureRequest.status == "pending"
    ).all()
    
    request_details = []
    for req in requests:
        document = db.query(MultiSignatureDocument).filter(
            MultiSignatureDocument.id == req.document_id
        ).first()
        
        requester = db.query(User).filter(User.id == req.requested_by).first()
        
        request_details.append({
            "request_id": req.id,
            "document_id": req.document_id,
            "document_title": document.title if document else "Unknown",
            "requested_by": requester.username if requester else "Unknown",
            "message": req.message,
            "requested_at": req.requested_at.isoformat(),
            "expires_at": req.expires_at.isoformat() if req.expires_at else None
        })
    
    return {"signature_requests": request_details}

# Key Management endpoints
@app.post("/keys/generate")
async def create_key_pair(
    request_data: CreateKeyPairRequest,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Generate a new key pair for the user"""
    try:
        # Generate new Ed25519 key pair
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        
        # In production, encrypt the private key before storing
        private_key_encrypted = base64.b64encode(bytes(signing_key)).decode()  # Placeholder
        public_key = base64.b64encode(bytes(verify_key)).decode()
        
        # If this is set as primary, deactivate other primary keys
        if request_data.is_primary:
            db.query(UserKeyPair).filter(
                UserKeyPair.user_id == api_key.user_id,
                UserKeyPair.is_primary == True
            ).update({"is_primary": False})
        
        # Create key pair record
        key_pair_id = str(uuid.uuid4())
        key_pair = UserKeyPair(
            id=key_pair_id,
            user_id=api_key.user_id,
            key_name=request_data.key_name,
            public_key=public_key,
            private_key_encrypted=private_key_encrypted,
            is_primary=request_data.is_primary,
            backup_location=request_data.backup_location
        )
        
        db.add(key_pair)
        db.commit()
        
        return {
            "key_pair_id": key_pair_id,
            "key_name": request_data.key_name,
            "public_key": public_key,
            "private_key": base64.b64encode(bytes(signing_key)).decode(),  # Only shown once
            "is_primary": request_data.is_primary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keys")
async def list_user_keys(
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """List all active key pairs for the user"""
    keys = db.query(UserKeyPair).filter(
        UserKeyPair.user_id == api_key.user_id,
        UserKeyPair.is_active == True
    ).all()
    
    key_list = []
    for key in keys:
        key_list.append({
            "key_pair_id": key.id,
            "key_name": key.key_name,
            "public_key": key.public_key,
            "key_type": key.key_type,
            "created_at": key.created_at.isoformat(),
            "last_used": key.last_used.isoformat() if key.last_used else None,
            "is_primary": key.is_primary,
            "backup_location": key.backup_location
        })
    
    return {"key_pairs": key_list}

@app.post("/keys/rotate")
async def rotate_key(
    request_data: RotateKeyRequest,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Rotate a key pair by creating a new one and marking the old one as inactive"""
    try:
        # Get the old key pair
        old_key = db.query(UserKeyPair).filter(
            UserKeyPair.id == request_data.key_pair_id,
            UserKeyPair.user_id == api_key.user_id,
            UserKeyPair.is_active == True
        ).first()
        
        if not old_key:
            raise HTTPException(status_code=404, detail="Key pair not found")
        
        # Generate new key pair
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        
        private_key_encrypted = base64.b64encode(bytes(signing_key)).decode()  # Placeholder
        public_key = base64.b64encode(bytes(verify_key)).decode()
        
        # Create new key pair
        new_key_id = str(uuid.uuid4())
        new_key = UserKeyPair(
            id=new_key_id,
            user_id=api_key.user_id,
            key_name=f"{old_key.key_name}_rotated",
            public_key=public_key,
            private_key_encrypted=private_key_encrypted,
            is_primary=old_key.is_primary,
            backup_location=old_key.backup_location
        )
        
        # Mark old key as inactive
        old_key.is_active = False
        
        # Record rotation history
        rotation_id = str(uuid.uuid4())
        rotation_record = KeyRotationHistory(
            id=rotation_id,
            user_id=api_key.user_id,
            old_key_pair_id=old_key.id,
            new_key_pair_id=new_key_id,
            rotation_reason=request_data.reason,
            rotated_by=api_key.user_id
        )
        
        db.add(new_key)
        db.add(rotation_record)
        db.commit()
        
        return {
            "old_key_pair_id": old_key.id,
            "new_key_pair_id": new_key_id,
            "new_public_key": public_key,
            "new_private_key": base64.b64encode(bytes(signing_key)).decode(),  # Only shown once
            "rotation_reason": request_data.reason
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/keys/rotation-history")
async def get_key_rotation_history(
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get key rotation history for the user"""
    history = db.query(KeyRotationHistory).filter(
        KeyRotationHistory.user_id == api_key.user_id
    ).order_by(KeyRotationHistory.rotated_at.desc()).all()
    
    history_list = []
    for record in history:
        old_key = db.query(UserKeyPair).filter(UserKeyPair.id == record.old_key_pair_id).first()
        new_key = db.query(UserKeyPair).filter(UserKeyPair.id == record.new_key_pair_id).first()
        
        history_list.append({
            "rotation_id": record.id,
            "old_key_name": old_key.key_name if old_key else "Unknown",
            "new_key_name": new_key.key_name if new_key else "Unknown",
            "rotation_reason": record.rotation_reason,
            "rotated_at": record.rotated_at.isoformat()
        })
    
    return {"rotation_history": history_list}

# Browser Extension Management endpoints
@app.post("/extension/whitelist")
async def add_to_whitelist(
    request_data: WhitelistRequest,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Add a domain to user's whitelist"""
    try:
        # Check if domain already exists
        existing = db.query(UserWhitelist).filter(
            UserWhitelist.user_id == api_key.user_id,
            UserWhitelist.domain == request_data.domain,
            UserWhitelist.is_active == True
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Domain already in whitelist")
        
        whitelist_id = str(uuid.uuid4())
        whitelist_entry = UserWhitelist(
            id=whitelist_id,
            user_id=api_key.user_id,
            domain=request_data.domain
        )
        
        db.add(whitelist_entry)
        db.commit()
        
        return {
            "whitelist_id": whitelist_id,
            "domain": request_data.domain,
            "added_at": whitelist_entry.added_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extension/blacklist")
async def add_to_blacklist(
    request_data: BlacklistRequest,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Add a domain to user's blacklist"""
    try:
        # Check if domain already exists
        existing = db.query(UserBlacklist).filter(
            UserBlacklist.user_id == api_key.user_id,
            UserBlacklist.domain == request_data.domain,
            UserBlacklist.is_active == True
        ).first()
        
        if existing:
            raise HTTPException(status_code=400, detail="Domain already in blacklist")
        
        blacklist_id = str(uuid.uuid4())
        blacklist_entry = UserBlacklist(
            id=blacklist_id,
            user_id=api_key.user_id,
            domain=request_data.domain
        )
        
        db.add(blacklist_entry)
        db.commit()
        
        return {
            "blacklist_id": blacklist_id,
            "domain": request_data.domain,
            "added_at": blacklist_entry.added_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/extension/whitelist")
async def get_whitelist(
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get user's domain whitelist"""
    whitelist = db.query(UserWhitelist).filter(
        UserWhitelist.user_id == api_key.user_id,
        UserWhitelist.is_active == True
    ).all()
    
    domains = [
        {
            "whitelist_id": entry.id,
            "domain": entry.domain,
            "added_at": entry.added_at.isoformat()
        }
        for entry in whitelist
    ]
    
    return {"whitelist": domains}

@app.get("/extension/blacklist")
async def get_blacklist(
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get user's domain blacklist"""
    blacklist = db.query(UserBlacklist).filter(
        UserBlacklist.user_id == api_key.user_id,
        UserBlacklist.is_active == True
    ).all()
    
    domains = [
        {
            "blacklist_id": entry.id,
            "domain": entry.domain,
            "added_at": entry.added_at.isoformat()
        }
        for entry in blacklist
    ]
    
    return {"blacklist": domains}

@app.delete("/extension/whitelist/{whitelist_id}")
async def remove_from_whitelist(
    whitelist_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Remove a domain from whitelist"""
    entry = db.query(UserWhitelist).filter(
        UserWhitelist.id == whitelist_id,
        UserWhitelist.user_id == api_key.user_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Whitelist entry not found")
    
    entry.is_active = False
    db.commit()
    
    return {"message": "Domain removed from whitelist"}

@app.delete("/extension/blacklist/{blacklist_id}")
async def remove_from_blacklist(
    blacklist_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Remove a domain from blacklist"""
    entry = db.query(UserBlacklist).filter(
        UserBlacklist.id == blacklist_id,
        UserBlacklist.user_id == api_key.user_id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="Blacklist entry not found")
    
    entry.is_active = False
    db.commit()
    
    return {"message": "Domain removed from blacklist"}

# Cloud Storage Integration endpoints
@app.post("/cloud-storage/connect")
async def connect_cloud_storage(
    provider: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Connect a cloud storage provider"""
    try:
        from cloud_storage import get_cloud_storage_provider
        
        # Validate provider
        if provider.lower() not in ['google_drive', 'dropbox']:
            raise HTTPException(status_code=400, detail="Unsupported provider")
        
        # Test connection
        storage_provider = get_cloud_storage_provider(provider, access_token, refresh_token)
        test_files = await storage_provider.list_files()
        
        # Encrypt tokens for storage
        access_token_encrypted = storage_provider.encrypt_token(access_token)
        refresh_token_encrypted = storage_provider.encrypt_token(refresh_token) if refresh_token else None
        
        # Store integration
        integration_id = str(uuid.uuid4())
        integration = CloudStorageIntegration(
            id=integration_id,
            user_id=api_key.user_id,
            provider=provider.lower(),
            access_token_encrypted=access_token_encrypted,
            refresh_token_encrypted=refresh_token_encrypted,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)  # Default 1 hour
        )
        
        db.add(integration)
        db.commit()
        
        return {
            "integration_id": integration_id,
            "provider": provider,
            "status": "connected",
            "test_files_count": len(test_files)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cloud-storage/upload")
async def upload_to_cloud_storage(
    provider: str,
    file: UploadFile = File(...),
    author: Optional[str] = None,
    model_used: Optional[str] = None,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Sign and upload file to cloud storage"""
    try:
        from cloud_storage import get_cloud_storage_provider, sync_signature_to_cloud
        
        # Get cloud storage integration
        integration = db.query(CloudStorageIntegration).filter(
            CloudStorageIntegration.user_id == api_key.user_id,
            CloudStorageIntegration.provider == provider.lower(),
            CloudStorageIntegration.is_active == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Cloud storage integration not found")
        
        # Decrypt tokens
        access_token = integration.access_token_encrypted  # In production, decrypt this
        refresh_token = integration.refresh_token_encrypted  # In production, decrypt this
        
        # Initialize provider
        storage_provider = get_cloud_storage_provider(provider, access_token, refresh_token)
        
        # Read and sign content
        content = await file.read()
        content_hash = compute_hash(content)
        
        # Generate signature
        signing_key = nacl.signing.SigningKey.generate()
        verify_key = signing_key.verify_key
        
        signed = signing_key.sign(content_hash.encode())
        signature = base64.b64encode(signed.signature).decode()
        
        # Create metadata
        signature_id = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc)
        
        metadata = {
            "id": signature_id,
            "content_hash": content_hash,
            "signature": signature,
            "public_key": base64.b64encode(bytes(verify_key)).decode(),
            "timestamp": timestamp.isoformat(),
            "author": author or "Anonymous",
            "model_used": model_used,
            "file_name": file.filename,
            "file_size": len(content),
            "provider": provider
        }
        
        # Store signature in database
        db_signature = SignatureMetadata(
            id=signature_id,
            user_id=api_key.user_id,
            api_key_id=api_key.id,
            content_hash=content_hash,
            signature=signature,
            public_key=base64.b64encode(bytes(verify_key)).decode(),
            author=author,
            timestamp=timestamp,
            content_type="cloud_file",
            ai_model_used=model_used,
            file_name=file.filename,
            file_size=len(content),
            metadata_json=json.dumps(metadata)
        )
        db.add(db_signature)
        db.commit()
        
        # Upload to cloud storage
        upload_result = await sync_signature_to_cloud(
            storage_provider,
            content,
            file.filename,
            metadata
        )
        
        return {
            "signature_id": signature_id,
            "cloud_upload": upload_result,
            "metadata": metadata
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cloud-storage/files")
async def list_cloud_storage_files(
    provider: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """List files in cloud storage"""
    try:
        from cloud_storage import get_cloud_storage_provider
        
        # Get cloud storage integration
        integration = db.query(CloudStorageIntegration).filter(
            CloudStorageIntegration.user_id == api_key.user_id,
            CloudStorageIntegration.provider == provider.lower(),
            CloudStorageIntegration.is_active == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Cloud storage integration not found")
        
        # Decrypt tokens (placeholder - implement proper decryption)
        access_token = integration.access_token_encrypted
        refresh_token = integration.refresh_token_encrypted
        
        # Initialize provider
        storage_provider = get_cloud_storage_provider(provider, access_token, refresh_token)
        
        # List files
        files = await storage_provider.list_files()
        
        return {"files": files}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cloud-storage/verify")
async def verify_cloud_storage_file(
    provider: str,
    file_identifier: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Download and verify a file from cloud storage"""
    try:
        from cloud_storage import get_cloud_storage_provider, verify_from_cloud
        
        # Get cloud storage integration
        integration = db.query(CloudStorageIntegration).filter(
            CloudStorageIntegration.user_id == api_key.user_id,
            CloudStorageIntegration.provider == provider.lower(),
            CloudStorageIntegration.is_active == True
        ).first()
        
        if not integration:
            raise HTTPException(status_code=404, detail="Cloud storage integration not found")
        
        # Decrypt tokens (placeholder)
        access_token = integration.access_token_encrypted
        refresh_token = integration.refresh_token_encrypted
        
        # Initialize provider
        storage_provider = get_cloud_storage_provider(provider, access_token, refresh_token)
        
        # Download and verify
        result = await verify_from_cloud(storage_provider, file_identifier)
        
        if not result['success']:
            return result
        
        # Verify signature
        if result['metadata']:
            content_hash = compute_hash(result['file_content'])
            stored_hash = result['metadata']['content_hash']
            
            if content_hash == stored_hash:
                # Verify cryptographic signature
                public_key = result['metadata']['public_key']
                signature = result['metadata']['signature']
                
                try:
                    verify_key = nacl.signing.VerifyKey(base64.b64decode(public_key))
                    verify_key.verify(content_hash.encode(), base64.b64decode(signature))
                    
                    return {
                        "valid": True,
                        "message": "File verified successfully from cloud storage",
                        "metadata": result['metadata'],
                        "provider": provider
                    }
                except:
                    return {
                        "valid": False,
                        "message": "Invalid cryptographic signature"
                    }
            else:
                return {
                    "valid": False,
                    "message": "Content hash mismatch"
                }
        else:
            return {
                "valid": False,
                "message": "No OriginMark metadata found"
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cloud-storage/integrations")
async def list_cloud_integrations(
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """List user's cloud storage integrations"""
    integrations = db.query(CloudStorageIntegration).filter(
        CloudStorageIntegration.user_id == api_key.user_id,
        CloudStorageIntegration.is_active == True
    ).all()
    
    integration_list = []
    for integration in integrations:
        integration_list.append({
            "integration_id": integration.id,
            "provider": integration.provider,
            "created_at": integration.created_at.isoformat(),
            "expires_at": integration.expires_at.isoformat() if integration.expires_at else None
        })
    
    return {"integrations": integration_list}

@app.delete("/cloud-storage/integrations/{integration_id}")
async def disconnect_cloud_storage(
    integration_id: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Disconnect a cloud storage integration"""
    integration = db.query(CloudStorageIntegration).filter(
        CloudStorageIntegration.id == integration_id,
        CloudStorageIntegration.user_id == api_key.user_id
    ).first()
    
    if not integration:
        raise HTTPException(status_code=404, detail="Integration not found")
    
    integration.is_active = False
    db.commit()
    
    return {"message": "Cloud storage integration disconnected"}

# Admin and Analytics Endpoints

@app.get("/admin/metrics")
async def get_admin_metrics(
    days: int = 7,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get metrics dashboard for admin users"""
    # In production, add admin role check
    
    # Update daily summaries first
    await telemetry.update_daily_summary(db)
    
    # Get metrics summary
    metrics = await telemetry.get_metrics_summary(db, days)
    
    return metrics

@app.post("/feedback")
async def submit_feedback(
    feedback_type: str = Form(...),
    message: str = Form(...),
    rating: Optional[int] = Form(None),
    page_url: Optional[str] = Form(None),
    api_key: Optional[APIKey] = Depends(get_optional_api_key),
    db: Session = Depends(get_db)
):
    """Submit user feedback"""
    try:
        # Validate feedback type
        valid_types = ["bug", "feature", "general"]
        if feedback_type not in valid_types:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid feedback type. Must be one of: {', '.join(valid_types)}"
            )
        
        # Validate rating if provided
        if rating is not None and (rating < 1 or rating > 5):
            raise HTTPException(
                status_code=400,
                detail="Rating must be between 1 and 5"
            )
        
        feedback_id = await telemetry.record_feedback(
            db=db,
            feedback_type=feedback_type,
            message=message,
            user_id=api_key.user_id if api_key else None,
            rating=rating,
            page_url=page_url,
            metadata={
                "api_version": "2.0.0",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
        
        return {
            "message": "Thank you for your feedback!",
            "feedback_id": feedback_id,
            "status": "submitted"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/feedback")
async def get_feedback(
    status: Optional[str] = None,
    limit: int = 50,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Get user feedback (admin only)"""
    # In production, add admin role check
    
    query = db.query(UserFeedback)
    
    if status:
        query = query.filter(UserFeedback.status == status)
    
    feedback_items = query.order_by(
        UserFeedback.created_at.desc()
    ).limit(limit).all()
    
    return {
        "feedback": [
            {
                "id": item.id,
                "type": item.feedback_type,
                "message": item.message,
                "rating": item.rating,
                "page_url": item.page_url,
                "user_id": item.user_id,
                "created_at": item.created_at.isoformat(),
                "status": item.status
            }
            for item in feedback_items
        ],
        "total": len(feedback_items)
    }

@app.patch("/admin/feedback/{feedback_id}")
async def update_feedback_status(
    feedback_id: str,
    status: str,
    api_key: APIKey = Depends(get_api_key),
    db: Session = Depends(get_db)
):
    """Update feedback status (admin only)"""
    # In production, add admin role check
    
    valid_statuses = ["new", "reviewed", "resolved"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    feedback = db.query(UserFeedback).filter(
        UserFeedback.id == feedback_id
    ).first()
    
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    feedback.status = status
    db.commit()
    
    return {"message": "Feedback status updated", "new_status": status}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 