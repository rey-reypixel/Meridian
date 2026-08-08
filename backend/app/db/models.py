from sqlalchemy import Column, String, Float, Integer, DateTime, JSON, Boolean
from sqlalchemy.sql import func
from datetime import datetime
from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True)
    name = Column(String)
    oauth_provider = Column(String)  # "google"
    oauth_id = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class ApiRequest(Base):
    __tablename__ = "api_requests"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    original_model = Column(String)  # claude-opus, claude-sonnet, etc.
    routed_model = Column(String)
    original_cost = Column(Float)
    optimized_cost = Column(Float)
    savings = Column(Float)
    optimizations_applied = Column(JSON, default=list)  # ["context_truncation", "model_routing"]
    quality_score = Column(Float)  # 0-10 scale
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    latency_ms = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
