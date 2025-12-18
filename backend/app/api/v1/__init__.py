"""AI Tutor Platform - API v1 Router."""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.api.v1.curriculum import router as curriculum_router
from app.api.v1.practice import router as practice_router
from app.api.v1.assessment import router as assessment_router
from app.api.v1.exam import router as exam_router
from app.api.v1.test import router as test_router
from app.api.v1.study import router as study_router
from app.api.v1.chat import router as chat_router
from app.api.v1.parent import router as parent_router
from app.api.v1.review import router as review_router
from app.api.v1.gamification import router as gamification_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(curriculum_router)
api_router.include_router(practice_router)
api_router.include_router(assessment_router)
api_router.include_router(exam_router)
api_router.include_router(test_router)
api_router.include_router(study_router)
api_router.include_router(chat_router)
api_router.include_router(parent_router)
api_router.include_router(review_router)
api_router.include_router(gamification_router)

