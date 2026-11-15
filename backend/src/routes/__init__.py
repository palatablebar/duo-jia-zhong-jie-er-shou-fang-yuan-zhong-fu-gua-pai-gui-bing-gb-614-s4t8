"""路由聚合：统一 /api 前缀（Nginx 反代时剥掉 /api）。"""
from fastapi import APIRouter

from src.routes.agencies import router as agencies_router
from src.routes.audit import router as audit_router
from src.routes.auth import router as auth_router
from src.routes.exports import router as exports_router
from src.routes.health import router as health_router
from src.routes.listings import router as listings_router
from src.routes.overview import router as overview_router
from src.routes.properties import router as properties_router
from src.routes.reviews import router as reviews_router
from src.routes.runs import router as runs_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(overview_router)
api_router.include_router(agencies_router)
api_router.include_router(listings_router)
api_router.include_router(properties_router)
api_router.include_router(runs_router)
api_router.include_router(reviews_router)
api_router.include_router(exports_router)
api_router.include_router(audit_router)
