from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.admin import is_local_url, setup_admin
from app.config import settings
from app.db import SessionLocal
from app.routers import checkout, health, orders, products, shipping, webhooks

app = FastAPI(title="Pachnie miło API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router, prefix="/api")
app.include_router(products.router, prefix="/api")
app.include_router(shipping.router, prefix="/api")
app.include_router(checkout.router, prefix="/api")
app.include_router(orders.router, prefix="/api")
app.include_router(webhooks.router, prefix="/api")

setup_admin(
    app,
    SessionLocal,
    password=settings.admin_password,
    secret_key=settings.admin_secret_key,
    # Secure cookie everywhere except local development over plain http.
    https_only=not is_local_url(settings.frontend_url),
)
