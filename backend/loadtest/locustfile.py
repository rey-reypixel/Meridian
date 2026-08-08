"""
Load test for Meridian's own routing/truncation/DB overhead - run with
MOCK_ANTHROPIC=true so the real Anthropic API is never involved (free,
and it isolates exactly what the README's latency claims are actually
about: Meridian's own pipeline cost, not Claude's response time).

Usage:
    python loadtest/setup_test_user.py          # prints a token
    export LOCUST_JWT=<token>                    # (or `set` on Windows)
    locust -f loadtest/locustfile.py --host http://localhost:8000 \
        --headless -u 20 -r 5 -t 60s --csv=loadtest_results
"""
import os
from locust import HttpUser, task, between

TOKEN = os.environ.get("LOCUST_JWT", "")


class MeridianUser(HttpUser):
    wait_time = between(0.5, 2.0)

    def on_start(self):
        self.client.headers.update({"Authorization": f"Bearer {TOKEN}"})

    @task(5)
    def send_message(self):
        self.client.post("/api/messages", json={
            "model": "claude-opus",
            "messages": [{"role": "user", "content": "What is the capital of France?"}],
            "max_tokens": 50,
        }, name="/api/messages")

    @task(2)
    def send_message_long_context(self):
        # Exercises context truncation + embedding lookups under load
        messages = [
            {"role": "user", "content": f"Tell me fact number {i} about space"}
            for i in range(8)
        ]
        self.client.post("/api/messages", json={
            "model": "claude-sonnet",
            "messages": messages,
            "max_tokens": 50,
        }, name="/api/messages (long context)")

    @task(3)
    def estimate_cost(self):
        self.client.get(
            "/api/estimate?prompt=Hello+world&model=claude-haiku",
            name="/api/estimate"
        )

    @task(1)
    def dashboard_summary(self):
        self.client.get("/api/dashboard/summary", name="/api/dashboard/summary")
