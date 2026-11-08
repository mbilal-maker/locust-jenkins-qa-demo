"""Tiny staging API for a QA CI/CD performance testing workshop."""
import asyncio
from fastapi import FastAPI, HTTPException

app = FastAPI(title="QA Locust CI/CD Demo API", version="1.0.0")

# CHANGE THIS from 0.05 to 1.20, commit, and push to demonstrate a FAILED performance gate.
RESPONSE_DELAY_SECONDS = 0.05

# CHANGE THIS to True to demonstrate an HTTP-error / failure-rate gate.
FORCE_HTTP_ERROR = False


@app.get("/health")
async def health():
    return {"status": "healthy"}


@app.get("/api/products")
async def get_products():
    await asyncio.sleep(RESPONSE_DELAY_SECONDS)

    if FORCE_HTTP_ERROR:
        raise HTTPException(status_code=503, detail="Simulated service outage")

    products = [
        {"id": 1, "name": "Laptop", "price": 800},
        {"id": 2, "name": "Mouse", "price": 25},
        {"id": 3, "name": "Keyboard", "price": 65},
    ]
    return {"products": products, "total": len(products)}
