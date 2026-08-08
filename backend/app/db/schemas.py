from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime


class UserBase(BaseModel):
    email: EmailStr
    name: str


class UserCreate(UserBase):
    pass


class User(UserBase):
    id: int
    oauth_provider: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MessageInput(BaseModel):
    role: str  # "user", "assistant", "system"
    content: str


class MessagesCreateRequest(BaseModel):
    model: str  # "claude-opus", "claude-sonnet", "claude-haiku"
    messages: List[MessageInput]
    max_tokens: int = 1024
    temperature: float = 0.7
    optimize_for: Literal["cost", "speed", "quality"] = "cost"
    cost_limit: Optional[float] = None
    batch: bool = False
    quality_threshold: float = 8.5  # 0-10 scale, matches ModelRouter.QUALITY_SCORES


class MessageResponse(BaseModel):
    content: str
    role: str = "assistant"


class MessagesCreateResponse(BaseModel):
    content: MessageResponse
    metadata: Dict[str, Any] = {
        "cost": 0.0,
        "original_cost": 0.0,
        "savings": 0.0,
        "model_used": "",
        "model_original": "",
        "optimizations_applied": [],
        "quality_score": 0.0,
        "latency_ms": 0
    }


class CostEstimate(BaseModel):
    prompt: str
    model: str = "claude-opus"
    expected_output_tokens: int = 512


class CostEstimateResponse(BaseModel):
    estimated_cost: float
    token_count: int
    model: str


class DashboardSummary(BaseModel):
    total_spend_month: float
    optimized_spend_month: float
    total_savings: float
    savings_percentage: float
    requests_optimized: int
    avg_quality_score: float


class ModelCostBreakdown(BaseModel):
    model: str
    usage_count: int
    total_cost: float
    avg_cost_per_request: float


class DashboardModels(BaseModel):
    models: List[ModelCostBreakdown]


class RequestDetail(BaseModel):
    original_cost: float
    optimized_cost: float
    savings: float
    optimizations_applied: List[str]
    quality_score: float
    latency_ms: int


# OAuth schemas
class GoogleTokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    id_token: Optional[str] = None
