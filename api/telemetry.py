from sqlalchemy.orm import Session
from sqlalchemy import func, text
from db import UsageMetrics, DailyMetricsSummary, UserFeedback, get_db
from datetime import datetime, timedelta, timezone, date
import json
import time
from typing import Optional, Dict, Any
import uuid

class TelemetryTracker:
    """Handles telemetry and analytics tracking"""
    
    @staticmethod
    async def track_usage(
        db: Session,
        action: str,
        user_id: Optional[str] = None,
        api_key_id: Optional[str] = None,
        content_type: Optional[str] = None,
        status_code: int = 200,
        response_time_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Track a usage event"""
        try:
            usage_metric = UsageMetrics(
                user_id=user_id,
                api_key_id=api_key_id,
                action=action,
                content_type=content_type,
                timestamp=datetime.now(timezone.utc),
                response_time_ms=response_time_ms,
                status_code=status_code,
                ip_address=ip_address,
                user_agent=user_agent,
                metadata_json=json.dumps(metadata) if metadata else None
            )
            db.add(usage_metric)
            db.commit()
        except Exception as e:
            # Don't let telemetry errors break the main flow
            print(f"Telemetry error: {e}")
            db.rollback()
    
    @staticmethod
    async def update_daily_summary(db: Session):
        """Update daily metrics summary - should be run periodically"""
        try:
            today = date.today()
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = start_of_day + timedelta(days=1)
            
            # Get or create today's summary
            summary = db.query(DailyMetricsSummary).filter(
                func.date(DailyMetricsSummary.date) == today
            ).first()
            
            if not summary:
                summary = DailyMetricsSummary(date=start_of_day)
                db.add(summary)
            
            # Calculate metrics for today
            today_metrics = db.query(UsageMetrics).filter(
                UsageMetrics.timestamp >= start_of_day,
                UsageMetrics.timestamp < end_of_day
            )
            
            # Count actions
            summary.total_sign_count = today_metrics.filter(
                UsageMetrics.action == "sign"
            ).count()
            
            summary.total_verify_count = today_metrics.filter(
                UsageMetrics.action == "verify"
            ).count()
            
            summary.total_api_calls = today_metrics.count()
            
            # Count unique users
            unique_users = db.query(func.count(func.distinct(UsageMetrics.user_id))).filter(
                UsageMetrics.timestamp >= start_of_day,
                UsageMetrics.timestamp < end_of_day,
                UsageMetrics.user_id.isnot(None)
            ).scalar()
            summary.unique_users = unique_users or 0
            
            # Calculate average response time
            avg_response = db.query(func.avg(UsageMetrics.response_time_ms)).filter(
                UsageMetrics.timestamp >= start_of_day,
                UsageMetrics.timestamp < end_of_day,
                UsageMetrics.response_time_ms.isnot(None)
            ).scalar()
            summary.avg_response_time_ms = float(avg_response) if avg_response else None
            
            # Count errors
            summary.error_count = today_metrics.filter(
                UsageMetrics.status_code >= 400
            ).count()
            
            # Count IPFS operations
            summary.ipfs_operations = today_metrics.filter(
                UsageMetrics.action.in_(["ipfs_store", "ipfs_retrieve"])
            ).count()
            
            # Count blockchain operations
            summary.blockchain_operations = today_metrics.filter(
                UsageMetrics.action.in_(["blockchain_sign", "blockchain_verify"])
            ).count()
            
            db.commit()
            
        except Exception as e:
            print(f"Daily summary update error: {e}")
            db.rollback()
    
    @staticmethod
    async def get_metrics_summary(db: Session, days: int = 7) -> Dict[str, Any]:
        """Get metrics summary for the specified number of days"""
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Get usage metrics
        metrics = db.query(UsageMetrics).filter(
            UsageMetrics.timestamp >= start_date,
            UsageMetrics.timestamp <= end_date
        )
        
        # Get daily summaries
        daily_summaries = db.query(DailyMetricsSummary).filter(
            DailyMetricsSummary.date >= start_date,
            DailyMetricsSummary.date <= end_date
        ).order_by(DailyMetricsSummary.date.desc()).all()
        
        # Calculate totals
        total_signs = metrics.filter(UsageMetrics.action == "sign").count()
        total_verifies = metrics.filter(UsageMetrics.action == "verify").count()
        total_api_calls = metrics.count()
        unique_users = db.query(func.count(func.distinct(UsageMetrics.user_id))).filter(
            UsageMetrics.timestamp >= start_date,
            UsageMetrics.timestamp <= end_date,
            UsageMetrics.user_id.isnot(None)
        ).scalar()
        
        # Get action breakdown
        action_breakdown = db.query(
            UsageMetrics.action,
            func.count(UsageMetrics.id).label('count')
        ).filter(
            UsageMetrics.timestamp >= start_date,
            UsageMetrics.timestamp <= end_date
        ).group_by(UsageMetrics.action).all()
        
        # Get content type breakdown
        content_breakdown = db.query(
            UsageMetrics.content_type,
            func.count(UsageMetrics.id).label('count')
        ).filter(
            UsageMetrics.timestamp >= start_date,
            UsageMetrics.timestamp <= end_date,
            UsageMetrics.content_type.isnot(None)
        ).group_by(UsageMetrics.content_type).all()
        
        # Get recent feedback
        recent_feedback = db.query(UserFeedback).order_by(
            UserFeedback.created_at.desc()
        ).limit(10).all()
        
        return {
            "period": {
                "start": start_date.isoformat(),
                "end": end_date.isoformat(),
                "days": days
            },
            "totals": {
                "sign_count": total_signs,
                "verify_count": total_verifies,
                "total_api_calls": total_api_calls,
                "unique_users": unique_users or 0
            },
            "daily_summaries": [
                {
                    "date": summary.date.isoformat(),
                    "sign_count": summary.total_sign_count,
                    "verify_count": summary.total_verify_count,
                    "api_calls": summary.total_api_calls,
                    "unique_users": summary.unique_users,
                    "avg_response_time_ms": summary.avg_response_time_ms,
                    "error_count": summary.error_count
                }
                for summary in daily_summaries
            ],
            "action_breakdown": {
                action: count for action, count in action_breakdown
            },
            "content_type_breakdown": {
                content_type: count for content_type, count in content_breakdown
            },
            "recent_feedback": [
                {
                    "id": feedback.id,
                    "type": feedback.feedback_type,
                    "message": feedback.message,
                    "rating": feedback.rating,
                    "created_at": feedback.created_at.isoformat()
                }
                for feedback in recent_feedback
            ]
        }
    
    @staticmethod
    async def record_feedback(
        db: Session,
        feedback_type: str,
        message: str,
        user_id: Optional[str] = None,
        rating: Optional[int] = None,
        page_url: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Record user feedback"""
        feedback_id = str(uuid.uuid4())
        feedback = UserFeedback(
            id=feedback_id,
            user_id=user_id,
            feedback_type=feedback_type,
            message=message,
            rating=rating,
            page_url=page_url,
            created_at=datetime.now(timezone.utc),
            metadata_json=json.dumps(metadata) if metadata else None
        )
        db.add(feedback)
        db.commit()
        return feedback_id

# Middleware for tracking API response times
def track_request_time():
    """Middleware to track request processing time"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            response_time_ms = int((time.time() - start_time) * 1000)
            # Response time is stored in the request state for telemetry
            if hasattr(result, '__dict__'):
                result.telemetry_response_time = response_time_ms
            return result
        return wrapper
    return decorator

# Global telemetry instance
telemetry = TelemetryTracker() 