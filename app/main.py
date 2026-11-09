"""Small staging API for demonstrating Locust CI/CD quality gates."""
import asyncio
from fastapi import FastAPI, HTTPException

app = FastAPI(title="Locust QA Jenkins Demo")

# Change 0.05 to 1.20 and push to demonstrate a performance failure.
RESPONSE_DELAY_SECONDS = 1.25

# Change to True and push to demonstrate a 503/error-rate failure.
FORCE_HTTP_ERROR = False


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/products")
async def products():
    await asyncio.sleep(RESPONSE_DELAY_SECONDS)

    if FORCE_HTTP_ERROR:
        raise HTTPException(status_code=503, detail="Simulated API error")

    return {
        "products": [
            {"id": 1, "name": "Laptop", "price": 800},
            {"id": 2, "name": "Mouse", "price": 25},
            {"id": 3, "name": "Keyboard", "price": 65},
        ],
        "total": 3,
    }
