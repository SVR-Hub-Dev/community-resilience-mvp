"""API router initialization."""

from fastapi import APIRouter

from api.documents import router as documents_router
from api.sync import router as sync_router

# Create main API router
api_router = APIRouter()

# Include sub-routers
api_router.include_router(documents_router)
api_router.include_router(sync_router)

__all__ = ["api_router", "documents_router", "sync_router"]
