"""
OriginMark Reputation System
Community-driven reputation and trust scoring for signers
"""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta, timezone
from enum import Enum
import json
import math
from dataclasses import dataclass
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from db import get_db, SignatureMetadata, User, APIKey

class ReputationEvent(Enum):
    SIGNATURE_CREATED = "signature_created"
    SIGNATURE_VERIFIED = "signature_verified"
    SIGNATURE_DISPUTED = "signature_disputed"
    COMMUNITY_UPVOTE = "community_upvote"
    COMMUNITY_DOWNVOTE = "community_downvote"
    EXPERT_ENDORSEMENT = "expert_endorsement"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    ACCOUNT_VERIFIED = "account_verified"

@dataclass
class ReputationScore:
    """Reputation score breakdown"""
    overall_score: float
    trust_score: float
    activity_score: float
    community_score: float
    expert_score: float
    consistency_score: float
    age_factor: float
    total_signatures: int
    verified_signatures: int
    disputed_signatures: int
    community_votes: int

@dataclass
class TrustLevel:
    """Trust level classification"""
    level: str
    threshold: float
    color: str
    description: str

class ReputationCalculator:
    """Calculates and manages reputation scores"""
    
    # Trust level thresholds
    TRUST_LEVELS = [
        TrustLevel("Unverified", 0.0, "#gray-400", "New or unverified signer"),
        TrustLevel("Basic", 200.0, "#blue-400", "Basic trust level"),
        TrustLevel("Reliable", 400.0, "#green-400", "Reliable signer"),
        TrustLevel("Trusted", 600.0, "#green-600", "Highly trusted signer"),
        TrustLevel("Expert", 800.0, "#purple-600", "Expert-level signer"),
        TrustLevel("Authority", 950.0, "#gold-500", "Authoritative signer")
    ]
    
    # Scoring weights
    WEIGHTS = {
        "activity": 0.25,
        "community": 0.20,
        "expert": 0.20,
        "consistency": 0.20,
        "trust": 0.15
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_reputation(self, user_id: str) -> ReputationScore:
        """Calculate comprehensive reputation score for a user"""
        
        # Get user signatures
        signatures = self.db.query(SignatureMetadata).filter(
            SignatureMetadata.user_id == user_id
        ).all()
        
        if not signatures:
            return self._get_default_score()
        
        # Calculate component scores
        activity_score = self._calculate_activity_score(signatures)
        community_score = self._calculate_community_score(user_id)
        expert_score = self._calculate_expert_score(user_id)
        consistency_score = self._calculate_consistency_score(signatures)
        trust_score = self._calculate_trust_score(signatures)
        age_factor = self._calculate_age_factor(signatures)
        
        # Calculate weighted overall score
        overall_score = (
            activity_score * self.WEIGHTS["activity"] +
            community_score * self.WEIGHTS["community"] +
            expert_score * self.WEIGHTS["expert"] +
            consistency_score * self.WEIGHTS["consistency"] +
            trust_score * self.WEIGHTS["trust"]
        ) * age_factor
        
        # Cap at 1000
        overall_score = min(overall_score, 1000.0)
        
        # Get statistics
        total_signatures = len(signatures)
        verified_signatures = len([s for s in signatures if self._is_verified(s)])
        disputed_signatures = len([s for s in signatures if self._is_disputed(s)])
        community_votes = self._get_community_votes(user_id)
        
        return ReputationScore(
            overall_score=round(overall_score, 1),
            trust_score=round(trust_score, 1),
            activity_score=round(activity_score, 1),
            community_score=round(community_score, 1),
            expert_score=round(expert_score, 1),
            consistency_score=round(consistency_score, 1),
            age_factor=round(age_factor, 3),
            total_signatures=total_signatures,
            verified_signatures=verified_signatures,
            disputed_signatures=disputed_signatures,
            community_votes=community_votes
        )
    
    def _calculate_activity_score(self, signatures: List[SignatureMetadata]) -> float:
        """Calculate score based on signing activity"""
        total_sigs = len(signatures)
        
        if total_sigs == 0:
            return 0.0
        
        # Recent activity bonus
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent_sigs = len([s for s in signatures if s.timestamp > recent_cutoff])
        
        # Base score from total signatures (logarithmic)
        base_score = min(math.log10(total_sigs + 1) * 100, 300)
        
        # Recent activity multiplier
        recent_multiplier = 1.0 + (recent_sigs / max(total_sigs, 1)) * 0.5
        
        return min(base_score * recent_multiplier, 400.0)
    
    def _calculate_community_score(self, user_id: str) -> float:
        """Calculate score based on community feedback"""
        # This would integrate with a community voting system
        # For now, return a placeholder based on user activity
        
        # Get community votes (mock implementation)
        upvotes = self._get_community_upvotes(user_id)
        downvotes = self._get_community_downvotes(user_id)
        
        if upvotes + downvotes == 0:
            return 100.0  # Neutral starting score
        
        vote_ratio = upvotes / (upvotes + downvotes) if (upvotes + downvotes) > 0 else 0.5
        total_votes = upvotes + downvotes
        
        # Score based on positive vote ratio and total engagement
        score = vote_ratio * 200 + min(math.log10(total_votes + 1) * 50, 100)
        
        return min(score, 300.0)
    
    def _calculate_expert_score(self, user_id: str) -> float:
        """Calculate score based on expert endorsements"""
        # This would track expert endorsements and verifications
        # For now, return a score based on account verification
        
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return 0.0
        
        # Basic verification bonus
        base_score = 50.0 if hasattr(user, 'is_verified') and user.is_verified else 0.0
        
        # Expert endorsements (mock)
        endorsements = self._get_expert_endorsements(user_id)
        endorsement_score = min(endorsements * 50, 200)
        
        return min(base_score + endorsement_score, 250.0)
    
    def _calculate_consistency_score(self, signatures: List[SignatureMetadata]) -> float:
        """Calculate score based on signature consistency and quality"""
        if not signatures:
            return 0.0
        
        # Check for consistent metadata
        has_author = len([s for s in signatures if s.author]) / len(signatures)
        has_model = len([s for s in signatures if s.ai_model_used]) / len(signatures)
        
        # Check for consistent file types
        content_types = set(s.content_type for s in signatures if s.content_type)
        type_consistency = 1.0 if len(content_types) <= 3 else 0.7
        
        # Time consistency (regular signing pattern)
        time_consistency = self._calculate_time_consistency(signatures)
        
        # Combine factors
        metadata_score = (has_author + has_model) * 100
        consistency_bonus = type_consistency * time_consistency * 100
        
        return min(metadata_score + consistency_bonus, 300.0)
    
    def _calculate_trust_score(self, signatures: List[SignatureMetadata]) -> float:
        """Calculate trust score based on verification history"""
        total_sigs = len(signatures)
        if total_sigs == 0:
            return 100.0
        
        # Count verified vs disputed signatures
        verified_count = len([s for s in signatures if self._is_verified(s)])
        disputed_count = len([s for s in signatures if self._is_disputed(s)])
        
        # Calculate trust ratio
        if disputed_count == 0:
            trust_ratio = 1.0
        else:
            trust_ratio = max(0.0, (verified_count - disputed_count * 2) / total_sigs)
        
        # Base trust score
        base_score = trust_ratio * 200
        
        # Penalty for disputes
        dispute_penalty = min(disputed_count * 10, 50)
        
        return max(base_score - dispute_penalty, 0.0)
    
    def _calculate_age_factor(self, signatures: List[SignatureMetadata]) -> float:
        """Calculate age factor based on account longevity"""
        if not signatures:
            return 1.0
        
        # Get account age from first signature
        first_signature = min(signatures, key=lambda s: s.timestamp)
        account_age_days = (datetime.now(timezone.utc) - first_signature.timestamp).days
        
        # Age factor increases over time but caps at 1.2
        age_factor = 1.0 + min(account_age_days / 365, 0.2)
        
        return age_factor
    
    def _calculate_time_consistency(self, signatures: List[SignatureMetadata]) -> float:
        """Calculate consistency of signing patterns over time"""
        if len(signatures) < 3:
            return 1.0
        
        # Sort by timestamp
        sorted_sigs = sorted(signatures, key=lambda s: s.timestamp)
        
        # Calculate intervals between signatures
        intervals = []
        for i in range(1, len(sorted_sigs)):
            interval = (sorted_sigs[i].timestamp - sorted_sigs[i-1].timestamp).total_seconds()
            intervals.append(interval)
        
        if not intervals:
            return 1.0
        
        # Calculate coefficient of variation (lower is more consistent)
        mean_interval = sum(intervals) / len(intervals)
        if mean_interval == 0:
            return 1.0
        
        variance = sum((x - mean_interval) ** 2 for x in intervals) / len(intervals)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_interval
        
        # Convert to consistency score (0-1, higher is better)
        consistency = max(0.0, 1.0 - cv)
        
        return consistency
    
    def _is_verified(self, signature: SignatureMetadata) -> bool:
        """Check if a signature is verified"""
        # This would integrate with blockchain verification
        # For now, assume signatures with complete metadata are verified
        return bool(signature.author and signature.ai_model_used)
    
    def _is_disputed(self, signature: SignatureMetadata) -> bool:
        """Check if a signature is disputed"""
        # This would integrate with dispute system
        # For now, return False (no disputes tracked yet)
        return False
    
    def _get_community_votes(self, user_id: str) -> int:
        """Get total community votes for user"""
        return self._get_community_upvotes(user_id) + self._get_community_downvotes(user_id)
    
    def _get_community_upvotes(self, user_id: str) -> int:
        """Get community upvotes for user (mock implementation)"""
        # This would integrate with community voting system
        sig_count = self.db.query(SignatureMetadata).filter(
            SignatureMetadata.user_id == user_id
        ).count()
        
        # Mock: assume 1 upvote per 3 signatures on average
        return sig_count // 3
    
    def _get_community_downvotes(self, user_id: str) -> int:
        """Get community downvotes for user (mock implementation)"""
        # Mock: assume minimal downvotes for active users
        return 0
    
    def _get_expert_endorsements(self, user_id: str) -> int:
        """Get expert endorsements for user (mock implementation)"""
        # This would integrate with expert endorsement system
        return 0
    
    def _get_default_score(self) -> ReputationScore:
        """Get default score for new users"""
        return ReputationScore(
            overall_score=100.0,
            trust_score=100.0,
            activity_score=0.0,
            community_score=100.0,
            expert_score=0.0,
            consistency_score=0.0,
            age_factor=1.0,
            total_signatures=0,
            verified_signatures=0,
            disputed_signatures=0,
            community_votes=0
        )
    
    def get_trust_level(self, score: float) -> TrustLevel:
        """Get trust level for a given score"""
        for level in reversed(self.TRUST_LEVELS):
            if score >= level.threshold:
                return level
        return self.TRUST_LEVELS[0]
    
    def get_leaderboard(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get reputation leaderboard"""
        # Get all users with signatures
        users_with_sigs = self.db.query(User.id, User.username, User.email).join(
            SignatureMetadata, User.id == SignatureMetadata.user_id
        ).distinct().limit(limit).all()
        
        leaderboard = []
        for user in users_with_sigs:
            reputation = self.calculate_reputation(user.id)
            trust_level = self.get_trust_level(reputation.overall_score)
            
            leaderboard.append({
                "user_id": user.id,
                "username": user.username,
                "overall_score": reputation.overall_score,
                "trust_level": trust_level.level,
                "total_signatures": reputation.total_signatures,
                "verified_signatures": reputation.verified_signatures
            })
        
        # Sort by overall score
        leaderboard.sort(key=lambda x: x["overall_score"], reverse=True)
        
        return leaderboard[:limit]

class CommunityModeration:
    """Handles community-driven moderation and voting"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def submit_dispute(self, 
                      signature_id: str, 
                      disputer_id: str, 
                      reason: str, 
                      evidence: Optional[str] = None) -> str:
        """Submit a dispute for a signature"""
        # This would create a dispute record in the database
        # For now, just log the dispute
        
        dispute_data = {
            "signature_id": signature_id,
            "disputer_id": disputer_id,
            "reason": reason,
            "evidence": evidence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending"
        }
        
        # In a real implementation, store in disputes table
        print(f"Dispute submitted: {json.dumps(dispute_data, indent=2)}")
        
        return f"dispute_{signature_id}_{disputer_id}"
    
    def vote_on_dispute(self, 
                       dispute_id: str, 
                       voter_id: str, 
                       vote: str, 
                       weight: float = 1.0) -> bool:
        """Vote on a signature dispute"""
        # This would record votes in the database
        # For now, just log the vote
        
        vote_data = {
            "dispute_id": dispute_id,
            "voter_id": voter_id,
            "vote": vote,  # "uphold" or "dismiss"
            "weight": weight,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"Vote recorded: {json.dumps(vote_data, indent=2)}")
        return True
    
    def endorse_signer(self, 
                      signer_id: str, 
                      endorser_id: str, 
                      endorsement_type: str = "general") -> bool:
        """Submit expert endorsement for a signer"""
        
        endorsement_data = {
            "signer_id": signer_id,
            "endorser_id": endorser_id,
            "endorsement_type": endorsement_type,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        print(f"Endorsement submitted: {json.dumps(endorsement_data, indent=2)}")
        return True

# Utility functions for easy integration
def get_user_reputation(user_id: str, db: Session) -> ReputationScore:
    """Get reputation score for a user"""
    calculator = ReputationCalculator(db)
    return calculator.calculate_reputation(user_id)

def get_trust_level_for_score(score: float) -> TrustLevel:
    """Get trust level for a given score"""
    calculator = ReputationCalculator(None)
    return calculator.get_trust_level(score)

def get_reputation_leaderboard(limit: int = 50, db: Session = None) -> List[Dict[str, Any]]:
    """Get reputation leaderboard"""
    if not db:
        db = next(get_db())
    
    calculator = ReputationCalculator(db)
    return calculator.get_leaderboard(limit) 