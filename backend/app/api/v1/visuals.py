"""
AI Tutor Platform - Visuals API
Endpoints for generating educational visual content using AI.
"""
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.document import GeneratedImage
from app.ai.agents.image_agent import image_agent


router = APIRouter(prefix="/visuals", tags=["visuals"])


# Request/Response Models
class ExplainVisualRequest(BaseModel):
    """Request to generate a visual explanation."""
    concept: str = Field(..., description="The concept to visualize", min_length=3, max_length=500)
    grade: int = Field(5, ge=1, le=12, description="Student grade level")
    size: str = Field("1024x1024", description="Image size")
    quality: str = Field("standard", description="Image quality (standard or hd)")
    additional_context: Optional[str] = Field(None, max_length=500)
    student_id: Optional[str] = Field(None, description="Optional student ID")


class VisualResponse(BaseModel):
    """Response with generated visual."""
    id: str
    concept: str
    grade_level: int
    image_url: Optional[str]
    image_path: Optional[str]
    enhanced_prompt: str
    provider: str
    status: str
    created_at: datetime


class VisualListResponse(BaseModel):
    """List of generated visuals."""
    visuals: list[VisualResponse]
    total: int


# Endpoints
@router.post("/explain", response_model=VisualResponse)
async def generate_visual_explanation(
    request: ExplainVisualRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Generate a visual explanation for a concept using AI.
    
    The image is generated using DALL-E 3 with grade-appropriate styling.
    """
    # Generate image
    result = await image_agent.generate_image(
        concept=request.concept,
        grade=request.grade,
        size=request.size,
        quality=request.quality,
        additional_context=request.additional_context or "",
    )
    
    # Check if blocked by guardrails
    if result.blocked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Request blocked: {result.block_reason}"
        )
    
    if result.error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate image: {result.error}"
        )
    
    # Store in database
    student_uuid = uuid.UUID(request.student_id) if request.student_id else None
    
    generated_image = GeneratedImage(
        id=uuid.uuid4(),
        user_id=current_user.id,
        student_id=student_uuid,
        prompt=request.concept,
        enhanced_prompt=result.enhanced_prompt,
        concept=request.concept,
        grade_level=request.grade,
        image_url=result.image_url,
        image_path=result.image_path,
        provider=result.provider,
        status="completed",
    )
    
    db.add(generated_image)
    await db.commit()
    await db.refresh(generated_image)
    
    return VisualResponse(
        id=str(generated_image.id),
        concept=generated_image.concept,
        grade_level=generated_image.grade_level,
        image_url=generated_image.image_url,
        image_path=generated_image.image_path,
        enhanced_prompt=generated_image.enhanced_prompt,
        provider=generated_image.provider,
        status=generated_image.status,
        created_at=generated_image.created_at,
    )


@router.get("/{visual_id}", response_model=VisualResponse)
async def get_visual(
    visual_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific generated visual by ID."""
    result = await db.execute(
        select(GeneratedImage).where(
            GeneratedImage.id == uuid.UUID(visual_id),
            GeneratedImage.user_id == current_user.id,
        )
    )
    visual = result.scalar_one_or_none()
    
    if not visual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visual not found"
        )
    
    return VisualResponse(
        id=str(visual.id),
        concept=visual.concept,
        grade_level=visual.grade_level,
        image_url=visual.image_url,
        image_path=visual.image_path,
        enhanced_prompt=visual.enhanced_prompt,
        provider=visual.provider,
        status=visual.status,
        created_at=visual.created_at,
    )


@router.get("/", response_model=VisualListResponse)
async def list_visuals(
    student_id: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all generated visuals for the current user."""
    query = select(GeneratedImage).where(
        GeneratedImage.user_id == current_user.id
    )
    
    if student_id:
        query = query.where(GeneratedImage.student_id == uuid.UUID(student_id))
    
    query = query.order_by(GeneratedImage.created_at.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    visuals = result.scalars().all()
    
    # Get total count
    count_query = select(GeneratedImage).where(
        GeneratedImage.user_id == current_user.id
    )
    if student_id:
        count_query = count_query.where(GeneratedImage.student_id == uuid.UUID(student_id))
    
    count_result = await db.execute(count_query)
    total = len(count_result.scalars().all())
    
    return VisualListResponse(
        visuals=[
            VisualResponse(
                id=str(v.id),
                concept=v.concept,
                grade_level=v.grade_level,
                image_url=v.image_url,
                image_path=v.image_path,
                enhanced_prompt=v.enhanced_prompt,
                provider=v.provider,
                status=v.status,
                created_at=v.created_at,
            )
            for v in visuals
        ],
        total=total,
    )


@router.delete("/{visual_id}")
async def delete_visual(
    visual_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Delete a generated visual."""
    result = await db.execute(
        select(GeneratedImage).where(
            GeneratedImage.id == uuid.UUID(visual_id),
            GeneratedImage.user_id == current_user.id,
        )
    )
    visual = result.scalar_one_or_none()
    
    if not visual:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Visual not found"
        )
    
    await db.delete(visual)
    await db.commit()
    
    return {"message": "Visual deleted successfully"}
