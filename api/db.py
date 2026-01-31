import os
from datetime import datetime, timezone
from typing import Optional
import secrets

from sqlalchemy import create_engine, Column, String, DateTime, Text, Integer, Boolean, ForeignKey, Float
from sqlalchemy.orm import DeclarativeBase, sessionmaker, relationship, Mapped, mapped_column


# Database URL from environment variable (production-ready)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./originmark.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# SQLAlchemy 2.0 style declarative base
class Base(DeclarativeBase):
    pass


def utc_now() -> datetime:
    """Return current UTC time (timezone-aware)"""
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class APIKey(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    key_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    rate_limit: Mapped[int] = mapped_column(Integer, default=1000)


class SignatureMetadata(Base):
    __tablename__ = "signatures"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    api_key_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)
    public_key: Mapped[str] = mapped_column(String, nullable=False)
    author: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    content_type: Mapped[str] = mapped_column(String, nullable=False)
    ai_model_used: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    file_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class MultiSignatureDocument(Base):
    __tablename__ = "multi_signature_documents"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    content_hash: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_by: Mapped[str] = mapped_column(String, nullable=False)
    required_signatures: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    current_signatures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class SignatureChain(Base):
    __tablename__ = "signature_chains"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("multi_signature_documents.id"), nullable=False)
    signature_id: Mapped[str] = mapped_column(String, ForeignKey("signatures.id"), nullable=False)
    signer_user_id: Mapped[str] = mapped_column(String, nullable=False)
    signature_order: Mapped[int] = mapped_column(Integer, nullable=False)
    previous_signature_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    signature_type: Mapped[str] = mapped_column(String, nullable=False, default="standard")
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    document = relationship("MultiSignatureDocument")
    signature = relationship("SignatureMetadata")


class SignatureRequest(Base):
    __tablename__ = "signature_requests"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(String, ForeignKey("multi_signature_documents.id"), nullable=False)
    requested_by: Mapped[str] = mapped_column(String, nullable=False)
    requested_from: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    responded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    document = relationship("MultiSignatureDocument")


class UserKeyPair(Base):
    __tablename__ = "user_key_pairs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    key_name: Mapped[str] = mapped_column(String, nullable=False)
    public_key: Mapped[str] = mapped_column(String, nullable=False)
    private_key_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    key_type: Mapped[str] = mapped_column(String, nullable=False, default="ed25519")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
    backup_location: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    rotation_schedule: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class KeyRotationHistory(Base):
    __tablename__ = "key_rotation_history"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    old_key_pair_id: Mapped[str] = mapped_column(String, nullable=False)
    new_key_pair_id: Mapped[str] = mapped_column(String, nullable=False)
    rotation_reason: Mapped[str] = mapped_column(String, nullable=False)
    rotated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    rotated_by: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class UserWhitelist(Base):
    __tablename__ = "user_whitelists"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserBlacklist(Base):
    __tablename__ = "user_blacklists"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[str] = mapped_column(String, nullable=False)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class CloudStorageIntegration(Base):
    __tablename__ = "cloud_storage_integrations"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    provider: Mapped[str] = mapped_column(String, nullable=False)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UsageMetrics(Base):
    __tablename__ = "usage_metrics"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    api_key_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    action: Mapped[str] = mapped_column(String, nullable=False)
    content_type: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    response_time_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status_code: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DailyMetricsSummary(Base):
    __tablename__ = "daily_metrics_summary"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    total_sign_count: Mapped[int] = mapped_column(Integer, default=0)
    total_verify_count: Mapped[int] = mapped_column(Integer, default=0)
    unique_users: Mapped[int] = mapped_column(Integer, default=0)
    new_users: Mapped[int] = mapped_column(Integer, default=0)
    total_api_calls: Mapped[int] = mapped_column(Integer, default=0)
    avg_response_time_ms: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    ipfs_operations: Mapped[int] = mapped_column(Integer, default=0)
    blockchain_operations: Mapped[int] = mapped_column(Integer, default=0)


class UserFeedback(Base):
    __tablename__ = "user_feedback"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    feedback_type: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    page_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    status: Mapped[str] = mapped_column(String, default="new")
    metadata_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


# Create tables
Base.metadata.create_all(bind=engine)


def get_db():
    """Database session dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def generate_api_key() -> str:
    """Generate a secure API key with 'om_' prefix"""
    return f"om_{secrets.token_urlsafe(32)}"


def hash_api_key(api_key: str) -> str:
    """Hash an API key for secure storage"""
    import hashlib
    return hashlib.sha256(api_key.encode()).hexdigest()