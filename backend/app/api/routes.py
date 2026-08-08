from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
import time
import json
import asyncio
from app.config import settings
from app.db import models
from app.db.database import SessionLocal
from app.db.schemas import (
    MessagesCreateRequest, MessagesCreateResponse, MessageResponse,
    CostEstimate, CostEstimateResponse, DashboardSummary, DashboardModels,
    ModelCostBreakdown, RequestDetail, RequestListResponse
)
from app.dependencies import get_current_user, get_db
from app.services.cost_predictor import cost_predictor
from app.services.llm_client import llm_client
from app.services.model_router import model_router
from app.services.context_truncation import context_truncation
from app.services.batch_manager import batch_manager
from app.services.response_cache import response_cache
from app.utils.logger import get_logger
from app.utils.metrics import metrics

logger = get_logger(__name__)
router = APIRouter(prefix="/api", tags=["messages"])


def _prepare_optimized_request(request: MessagesCreateRequest) -> Dict[str, Any]:
    """
    Shared prep for both the direct and streaming message endpoints:
    message conversion, cost estimate, task classification (once, reused
    everywhere below instead of re-embedding the prompt per call site),
    context truncation, model routing, optimized cost estimate, and
    cost_limit enforcement.

    Raises HTTPException(402) if cost_limit is exceeded.
    """
    messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
    prompt_text = "\n".join(msg["content"] for msg in messages)

    original_estimate = cost_predictor.estimate_from_text(
        prompt_text, request.model, request.max_tokens
    )
    original_cost = original_estimate["estimated_cost"]

    optimizations_applied = []
    routed_model = request.model
    quality_score = 9.0
    task_type = model_router.classify_task(prompt_text)

    # Context truncation (skipped in "speed" mode - computing embeddings adds latency)
    truncated_messages = messages
    if settings.context_truncation_enabled and request.optimize_for != "speed":
        truncated_messages = context_truncation.truncate_context(
            messages,
            relevance_threshold=settings.context_relevance_threshold,
            preserve_recent=settings.preserve_recent_messages
        )
        if len(truncated_messages) < len(messages):
            optimizations_applied.append("context_truncation")

    # Model routing (skipped in "quality" mode - never downgrade below the requested model)
    if settings.model_routing_enabled and request.optimize_for != "quality":
        routing_decision = model_router.get_routing_decision(
            request.model, prompt_text, quality_threshold=request.quality_threshold, task_type=task_type
        )
        routed_model = routing_decision["routed_model"]
        quality_score = routing_decision["quality_score"]
        if routing_decision["was_routed"]:
            optimizations_applied.append("model_routing")

    # Estimate optimized cost
    truncated_text = "\n".join(msg["content"] for msg in truncated_messages)
    optimized_estimate = cost_predictor.estimate_from_text(
        truncated_text, routed_model, request.max_tokens
    )
    optimized_cost = optimized_estimate["estimated_cost"]

    # Enforce a per-request budget, if given, before spending anything
    if request.cost_limit is not None and optimized_cost > request.cost_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"Estimated cost ${optimized_cost:.6f} exceeds "
                f"cost_limit ${request.cost_limit:.6f}"
            )
        )

    return {
        "task_type": task_type,
        "truncated_messages": truncated_messages,
        "truncated_text": truncated_text,
        "routed_model": routed_model,
        "quality_score": quality_score,
        "optimizations_applied": optimizations_applied,
        "original_cost": original_cost,
        "optimized_cost": optimized_cost,
    }


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
        prep = _prepare_optimized_request(request)
        truncated_messages = prep["truncated_messages"]
        routed_model = prep["routed_model"]
        quality_score = prep["quality_score"]
        optimizations_applied = prep["optimizations_applied"]
        original_cost = prep["original_cost"]

        # Semantic response cache: skip the LLM entirely on a near-duplicate
        # prompt. Gated by temperature - reusing an old response instead of
        # sampling a new one isn't obviously correct for stochastic requests.
        cache_hit = None
        if request.temperature <= settings.response_cache_max_temperature:
            cache_hit = response_cache.get(routed_model, prep["truncated_text"])

        if cache_hit:
            response = cache_hit
            optimizations_applied.append("semantic_cache")

        # Call Claude API (direct, or grouped through the batch queue)
        elif request.batch and settings.batch_processing_enabled:
            batch_key = batch_manager.add_to_batch(
                request_id=request_id,
                model=routed_model,
                task_type=prep["task_type"],
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

        if not cache_hit:
            response_cache.set(
                routed_model, prep["truncated_text"],
                response["content"], response["input_tokens"], response["output_tokens"]
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


@router.post("/messages/stream")
async def create_message_stream(
    request: MessagesCreateRequest,
    current_user: models.User = Depends(get_current_user),
):
    """
    Same optimization pipeline as POST /messages, streamed back as
    Server-Sent Events. Not combinable with batch=true - a batched
    response is deferred/grouped by design, which isn't a coherent
    combination with a live streamed connection.
    """
    if request.batch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="streaming and batch are mutually exclusive"
        )

    start_time = time.time()
    request_id = str(uuid.uuid4())

    prep = _prepare_optimized_request(request)
    truncated_messages = prep["truncated_messages"]
    routed_model = prep["routed_model"]
    quality_score = prep["quality_score"]
    optimizations_applied = prep["optimizations_applied"]
    original_cost = prep["original_cost"]

    cache_hit = None
    if request.temperature <= settings.response_cache_max_temperature:
        cache_hit = response_cache.get(routed_model, prep["truncated_text"])

    async def event_generator():
        full_text = ""
        input_tokens = 0
        output_tokens = 0

        # Opened here (not injected via Depends) so the session's lifetime
        # is tied to this generator, not to FastAPI's dependency cleanup
        # timing for the outer endpoint call.
        db_session = SessionLocal()
        try:
            if cache_hit:
                optimizations_applied.append("semantic_cache")
                words = cache_hit["content"].split(" ")
                for i, word in enumerate(words):
                    chunk = word if i == 0 else f" {word}"
                    full_text += chunk
                    yield f"data: {json.dumps({'text': chunk})}\n\n"
                    await asyncio.sleep(0.02)
                input_tokens = cache_hit["input_tokens"]
                output_tokens = cache_hit["output_tokens"]
            else:
                async for event in llm_client.stream_message(
                    model=routed_model,
                    messages=truncated_messages,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature
                ):
                    if event["type"] == "delta":
                        yield f"data: {json.dumps({'text': event['text']})}\n\n"
                    elif event["type"] == "done":
                        full_text = event["content"]
                        input_tokens = event["input_tokens"]
                        output_tokens = event["output_tokens"]

                response_cache.set(
                    routed_model, prep["truncated_text"], full_text, input_tokens, output_tokens
                )

            actual_cost = cost_predictor.estimate_cost(routed_model, input_tokens, output_tokens)
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
            db_session.add(db_request)
            db_session.commit()

            metrics.increment_counter("requests_total", labels={"model": routed_model})
            metrics.add_total("cost_usd_total", actual_cost)
            metrics.add_total("savings_usd_total", max(0, original_cost - actual_cost))
            metrics.set_gauge("quality_score_avg", quality_score)

            metadata = {
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
            yield f"data: {json.dumps({'done': True, 'metadata': metadata})}\n\n"

        except Exception as e:
            logger.error(f"Error in create_message_stream: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
        finally:
            db_session.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")


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
                avg_quality_score=0.0,
                total_tokens_processed=0,
                avg_latency_ms=0.0
            )

        total_original = sum(r.original_cost or 0 for r in requests)
        total_optimized = sum(r.optimized_cost or 0 for r in requests)
        total_savings = sum(r.savings or 0 for r in requests)
        avg_quality = sum(r.quality_score or 0 for r in requests) / len(requests)
        total_tokens = sum((r.input_tokens or 0) + (r.output_tokens or 0) for r in requests)
        avg_latency = sum(r.latency_ms or 0 for r in requests) / len(requests)

        savings_pct = (total_savings / total_original * 100) if total_original > 0 else 0

        return DashboardSummary(
            total_spend_month=round(total_original, 2),
            optimized_spend_month=round(total_optimized, 2),
            total_savings=round(total_savings, 2),
            savings_percentage=round(savings_pct, 2),
            requests_optimized=len(requests),
            avg_quality_score=round(avg_quality, 2),
            total_tokens_processed=total_tokens,
            avg_latency_ms=round(avg_latency, 2)
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


def _to_request_detail(request: models.ApiRequest) -> RequestDetail:
    return RequestDetail(
        id=request.id,
        created_at=request.created_at,
        original_model=request.original_model or "",
        routed_model=request.routed_model or "",
        original_cost=request.original_cost or 0,
        optimized_cost=request.optimized_cost or 0,
        savings=request.savings or 0,
        optimizations_applied=request.optimizations_applied or [],
        quality_score=request.quality_score or 0,
        input_tokens=request.input_tokens or 0,
        output_tokens=request.output_tokens or 0,
        latency_ms=request.latency_ms or 0
    )


@router.get("/requests", response_model=RequestListResponse)
async def list_requests(
    page: int = 1,
    page_size: int = 20,
    model: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List requests for the current user, most recent first"""
    try:
        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)

        query = db.query(models.ApiRequest).filter(
            models.ApiRequest.user_id == current_user.id
        )

        if model:
            query = query.filter(models.ApiRequest.routed_model == model)
        if start_date:
            query = query.filter(models.ApiRequest.created_at >= start_date)
        if end_date:
            query = query.filter(models.ApiRequest.created_at <= end_date)

        total = query.count()

        results = query.order_by(models.ApiRequest.created_at.desc()) \
            .offset((page - 1) * page_size) \
            .limit(page_size) \
            .all()

        return RequestListResponse(
            items=[_to_request_detail(r) for r in results],
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        logger.error(f"Error in list_requests: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching requests"
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

        return _to_request_detail(request)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_request_details: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching request details"
        )
