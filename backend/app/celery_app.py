from celery import Celery
from app.config import settings

celery_app = Celery(
    "meridian",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(name="meridian.process_batch")
def process_batch_task(batch_key: str) -> None:
    """
    Pop every queued request for a batch, call Claude for each one, and
    store each result in Redis under its own request_id so the HTTP handler
    that's waiting on it (see BatchManager.wait_for_result) can pick it up.

    Note: this is a simplification vs. Anthropic's real Message Batches API,
    which has ~24h turnaround and doesn't fit a synchronous request/response
    HTTP flow. Here we group requests and call them sequentially inside the
    worker instead, which still captures the "process similar requests
    together" cost-tracking behavior without the async turnaround.
    """
    from app.services.batch_manager import batch_manager
    from app.services.llm_client import llm_client

    items = batch_manager.pop_batch(batch_key)

    for item in items:
        request_id = item["request_id"]
        data = item["data"]
        try:
            response = llm_client.create_message_sync(
                model=data["model"],
                messages=data["messages"],
                max_tokens=data["max_tokens"],
                temperature=data["temperature"],
            )
            result = {
                "content": response["content"],
                "input_tokens": response["input_tokens"],
                "output_tokens": response["output_tokens"],
            }
        except Exception as e:
            result = {"error": str(e)}

        batch_manager.store_result(request_id, result)
