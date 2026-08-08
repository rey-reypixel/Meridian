from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import uuid
import time
from app.config import settings
from app.db import models
from app.db.schemas import (
    MessagesCreateRequest, MessagesCreateResponse, MessageResponse,
    CostEstimate, CostEstimateResponse, DashboardSummary, DashboardModels,
    ModelCostBreakdown, RequestDetail
)
from app.dependencies import get_current_user, get_db
from app.services.cost_predictor import cost_predictor
from app.services.llm_client import llm_client
from app.services.model_router import model_router
from app.services.context_truncation import context_truncation
from app.services.batch_manager import batch_manager
from app.utils.logger import get_logger
from app.utils.metrics import metrics

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["messages"])


@router.post("/messages", response_model=MessagesCreateResponse)
async def create_message(
    request: MessagesCreateRequest,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a message with automatic optimization"""
    start_time = time.time()
    request_id = str(uuid.uuid4())

    try:
        # Convert message format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]

        # Estimate original cost
        prompt_text = "\n".join(msg["content"] for msg in messages)
        original_estimate = cost_predictor.estimate_from_text(
            prompt_text,
            request.model,
            request.max_tokens
        )
        original_cost = original_estimate["estimated_cost"]

        # Apply optimizations
        optimizations_applied = []
        routed_model = request.model
        quality_score = 9.0

        # Context truncation
        truncated_messages = messages
        if settings.context_truncation_enabled:
            truncated_messages = context_truncation.truncate_context(
                messages,
                relevance_threshold=settings.context_relevance_threshold,
                preserve_recent=settings.preserve_recent_messages
            )
            if len(truncated_messages) < len(messages):
                optimizations_applied.append("context_truncation")

        # Model routing
        if settings.model_routing_enabled and len(optimizations_applied) > 0:
            routing_decision = model_router.get_routing_decision(request.model, prompt_text)
            routed_model = routing_decision["routed_model"]
            quality_score = routing_decision["quality_score"]
            if routing_decision["was_routed"]:
                optimizations_applied.append("model_routing")

        # Estimate optimized cost
        truncated_text = "\n".join(msg["content"] for msg in truncated_messages)
        optimized_estimate = cost_predictor.estimate_from_text(
            truncated_text,
            routed_model,
            request.max_tokens
        )
        optimized_cost = optimized_estimate["estimated_cost"]
        savings = max(0, original_cost - optimized_cost)

        # Call Claude API (direct, or grouped through the batch queue)
        if request.batch and settings.batch_processing_enabled:
            task_type = model_router.classify_task(prompt_text)
            batch_key = batch_manager.add_to_batch(
                request_id=request_id,
                model=routed_model,
                task_type=task_type,
                request_data={
                    "model": routed_model,
                    "messages": truncated_messages,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                }
            )
            batch_result = await run_in_threadpool(
                batch_manager.wait_for_result, request_id, batch_key, 15.0
            )
            if batch_result is None:
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Batch processing timed out"
                )
            if "error" in batch_result:
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=f"Error processing batched request: {batch_result['error']}"
                )
            response = batch_result
            optimizations_applied.append("batch_processing")
        else:
            response = await llm_client.create_message(
                model=routed_model,
                messages=truncated_messages,
                max_tokens=request.max_tokens,
                temperature=request.temperature
            )

        # Calculate actual cost
        input_tokens = response["input_tokens"]
        output_tokens = response["output_tokens"]
        actual_cost = cost_predictor.estimate_cost(routed_model, input_tokens, output_tokens)

        # Save to database
        latency_ms = int((time.time() - start_time) * 1000)
        db_request = models.ApiRequest(
            id=request_id,
            user_id=current_user.id,
            original_model=request.model,
            routed_model=routed_model,
            original_cost=original_cost,
            optimized_cost=actual_cost,
            savings=max(0, original_cost - actual_cost),
            optimizations_applied=optimizations_applied,
            quality_score=quality_score,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            latency_ms=latency_ms
        )
        db.add(db_request)
        db.commit()

        # Update metrics
        metrics.increment_counter("requests_total", labels={"model": routed_model})
        metrics.add_total("cost_usd_total", actual_cost)
        metrics.add_total("savings_usd_total", max(0, original_cost - actual_cost))
        metrics.set_gauge("quality_score_avg", quality_score)

        logger.info(f"Request {request_id}: {request.model} -> {routed_model}, savings: ${max(0, original_cost - actual_cost):.2f}")

        return MessagesCreateResponse(
            content=MessageResponse(content=response["content"]),
            metadata={
                "cost": round(actual_cost, 6),
                "original_cost": round(original_cost, 6),
                "savings": round(max(0, original_cost - actual_cost), 6),
                "model_used": routed_model,
                "model_original": request.model,
                "optimizations_applied": optimizations_applied,
                "quality_score": quality_score,
                "latency_ms": latency_ms,
                "request_id": request_id
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in create_message: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing request: {str(e)}"
        )


@router.get("/estimate", response_model=CostEstimateResponse)
async def estimate_cost(
    prompt: str,
    model: str = "claude-opus",
    expected_output_tokens: int = 512,
    current_user: models.User = Depends(get_current_user)
):
    """Estimate cost for a prompt"""
    try:
        estimate = cost_predictor.estimate_from_text(
            prompt,
            model,
            expected_output_tokens
        )
        return CostEstimateResponse(**estimate)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error in estimate_cost: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error estimating cost"
        )


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard summary for current user"""
    try:
        # Get user's requests
        requests = db.query(models.ApiRequest).filter(
            models.ApiRequest.user_id == current_user.id
        ).all()

        if not requests:
            return DashboardSummary(
                total_spend_month=0.0,
                optimized_spend_month=0.0,
                total_savings=0.0,
                savings_percentage=0.0,
                requests_optimized=0,
                avg_quality_score=0.0
            )

        total_original = sum(r.original_cost or 0 for r in requests)
        total_optimized = sum(r.optimized_cost or 0 for r in requests)
        total_savings = sum(r.savings or 0 for r in requests)
        avg_quality = sum(r.quality_score or 0 for r in requests) / len(requests)

        savings_pct = (total_savings / total_original * 100) if total_original > 0 else 0

        return DashboardSummary(
            total_spend_month=round(total_original, 2),
            optimized_spend_month=round(total_optimized, 2),
            total_savings=round(total_savings, 2),
            savings_percentage=round(savings_pct, 2),
            requests_optimized=len(requests),
            avg_quality_score=round(avg_quality, 2)
        )
    except Exception as e:
        logger.error(f"Error in get_dashboard_summary: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching dashboard summary"
        )


@router.get("/dashboard/models", response_model=DashboardModels)
async def get_dashboard_models(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cost breakdown by model"""
    try:
        # Get aggregated data by model
        results = db.query(
            models.ApiRequest.routed_model,
            func.count(models.ApiRequest.id).label("usage_count"),
            func.sum(models.ApiRequest.optimized_cost).label("total_cost")
        ).filter(
            models.ApiRequest.user_id == current_user.id
        ).group_by(
            models.ApiRequest.routed_model
        ).all()

        models_data = []
        for model_name, usage_count, total_cost in results:
            avg_cost = (total_cost / usage_count) if usage_count > 0 else 0
            models_data.append(ModelCostBreakdown(
                model=model_name or "unknown",
                usage_count=usage_count or 0,
                total_cost=round(total_cost or 0, 2),
                avg_cost_per_request=round(avg_cost, 6)
            ))

        return DashboardModels(models=models_data)
    except Exception as e:
        logger.error(f"Error in get_dashboard_models: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching model breakdown"
        )


@router.get("/requests/{request_id}", response_model=RequestDetail)
async def get_request_details(
    request_id: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get details for a specific request"""
    try:
        request = db.query(models.ApiRequest).filter(
            and_(
                models.ApiRequest.id == request_id,
                models.ApiRequest.user_id == current_user.id
            )
        ).first()

        if not request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Request not found"
            )

        return RequestDetail(
            original_cost=request.original_cost or 0,
            optimized_cost=request.optimized_cost or 0,
            savings=request.savings or 0,
            optimizations_applied=request.optimizations_applied or [],
            quality_score=request.quality_score or 0,
            latency_ms=request.latency_ms or 0
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_request_details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching request details"
        )
