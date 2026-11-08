"""Locust API scenario plus CI quality gate (no web UI needed)."""
import json
from pathlib import Path

from locust import HttpUser, between, events, task

MAX_ERROR_RATE = 0.02   # <= 2% request failures
MAX_P95_MS = 800       # <= 800 ms for the 95th percentile
MIN_REQUEST_COUNT = 20 # Catch tests that never really ran


class ProductApiUser(HttpUser):
    wait_time = between(0.5, 1.0)

    @task
    def read_products(self):
        with self.client.get(
            "/api/products", name="GET /api/products", catch_response=True, timeout=5
        ) as response:
            if response.status_code != 200:
                response.failure(f"Expected HTTP 200, got {response.status_code}")
                return

            try:
                payload = response.json()
            except ValueError:
                response.failure("Response is not valid JSON")
                return

            if payload.get("total") != 3:
                response.failure("Expected 3 products in API response")


@events.quitting.add_listener
def evaluate_quality_gate(environment, **kwargs):
    stats = environment.stats.total
    count = stats.num_requests
    failure_rate = stats.fail_ratio if count else 1.0
    p95_ms = stats.get_response_time_percentile(0.95) if count else None

    reasons = []
    if count < MIN_REQUEST_COUNT:
        reasons.append(f"Only {count} requests; minimum is {MIN_REQUEST_COUNT}")
    if failure_rate > MAX_ERROR_RATE:
        reasons.append(f"Error rate {failure_rate * 100:.2f}% exceeded 2%")
    if p95_ms is not None and p95_ms > MAX_P95_MS:
        reasons.append(f"P95 {p95_ms} ms exceeded {MAX_P95_MS} ms")

    report = {
        "status": "FAIL" if reasons else "PASS",
        "total_requests": count,
        "failed_requests": stats.num_failures,
        "error_rate_percent": round(failure_rate * 100, 2),
        "p95_response_time_ms": p95_ms,
        "thresholds": {
            "minimum_requests": MIN_REQUEST_COUNT,
            "maximum_error_rate_percent": MAX_ERROR_RATE * 100,
            "maximum_p95_ms": MAX_P95_MS,
        },
        "reasons": reasons,
    }

    Path("reports").mkdir(parents=True, exist_ok=True)
    Path("reports/quality-gate.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    print("\n========== QA PERFORMANCE QUALITY GATE ==========")
    print(json.dumps(report, indent=2))
    print("=================================================\n")

    # Nonzero exit -> Locust GitHub Actions step fails -> dependent job is skipped.
    environment.process_exit_code = 1 if reasons else 0
