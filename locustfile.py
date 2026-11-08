"""Locust test with a pass/fail quality gate for Jenkins."""
import json
from pathlib import Path

from locust import HttpUser, between, events, task

MAX_ERROR_RATE = 0.02
MAX_P95_MS = 800
MIN_REQUESTS = 20


class ProductApiUser(HttpUser):
    wait_time = between(0.5, 1.0)

    @task
    def get_products(self):
        with self.client.get(
            "/api/products",
            name="GET /api/products",
            catch_response=True,
            timeout=5,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Expected 200, got {response.status_code}")
                return
            try:
                payload = response.json()
            except ValueError:
                response.failure("Response body is not JSON")
                return
            if payload.get("total") != 3:
                response.failure("Expected total=3")


@events.quitting.add_listener
def quality_gate(environment, **kwargs):
    stats = environment.stats.total
    count = stats.num_requests
    rate = stats.fail_ratio if count else 1.0
    p95 = stats.get_response_time_percentile(0.95) if count else None

    reasons = []
    if count < MIN_REQUESTS:
        reasons.append(f"Only {count} requests (minimum {MIN_REQUESTS})")
    if rate > MAX_ERROR_RATE:
        reasons.append(f"Failure rate {rate * 100:.2f}% exceeds 2%")
    if p95 is not None and p95 > MAX_P95_MS:
        reasons.append(f"P95 {p95} ms exceeds {MAX_P95_MS} ms")

    result = {
        "status": "FAIL" if reasons else "PASS",
        "requests": count,
        "failures": stats.num_failures,
        "failure_rate_percent": round(rate * 100, 2),
        "p95_ms": p95,
        "reasons": reasons,
    }
    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("reports/quality-gate.json").write_text(
        json.dumps(result, indent=2) + "\n", encoding="utf-8"
    )
    print("\nQA PERFORMANCE GATE:\n" + json.dumps(result, indent=2), flush=True)
    environment.process_exit_code = 1 if reasons else 0
