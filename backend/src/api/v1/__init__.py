from fastapi import APIRouter

from src.api.v1.listings import router as listings_router
from src.api.v1.recommendations import router as recommendations_router

router = APIRouter()
router.include_router(listings_router)
router.include_router(recommendations_router)
