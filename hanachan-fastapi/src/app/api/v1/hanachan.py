from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from jose import jwt, JWTError
from app.core.config import settings
from app.db import get_supabase
from supabase import Client
from app.services.hanachan_service import HanachanService
from app.schemas.hanachan_wanikani import (
    AssignmentStart,
    ReviewCreate,
    StudyMaterialCreate,
    StudyMaterialUpdate,
    SyncRequest,
)

router = APIRouter()


def get_user_id_from_token(authorization: Optional[str] = Header(None)) -> str:
    """Validate JWT or WaniKani API Key (Universal ID) and extract user ID"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = authorization.replace("Bearer ", "")
    
    # 1. Try decoding as Supabase JWT
    try:
        payload = jwt.decode(
            token, 
            settings.SUPABASE_JWT_SECRET, 
            algorithms=["HS256"],
            options={"verify_aud": False}
        )
        user_id = payload.get("sub")
        if user_id:
            return user_id
    except JWTError:
        pass # Fallback to API Key / UUID check
        
    # 2. Try validating as a direct UUID (Personal Access Token / Universal ID)
    import re
    UUID_PATTERN = re.compile(r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$", re.I)
    if UUID_PATTERN.match(token):
        return token
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )


def get_service(
    user_id: str = Depends(get_user_id_from_token),
    db: Client = Depends(get_supabase)
) -> HanachanService:
    return HanachanService(db, user_id)


@router.get("/user")
async def get_user(service: HanachanService = Depends(get_service)):
    """Get current user information"""
    try:
        return await service.get_user()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/assignments")
async def get_assignments(
    available_after: Optional[datetime] = Query(None),
    available_before: Optional[datetime] = Query(None),
    burned: Optional[bool] = Query(None),
    hidden: Optional[bool] = Query(None),
    ids: Optional[List[int]] = Query(None),
    immediately_available_for_lessons: Optional[bool] = Query(None),
    immediately_available_for_review: Optional[bool] = Query(None),
    in_review: Optional[bool] = Query(None),
    levels: Optional[List[int]] = Query(None),
    srs_stages: Optional[List[int]] = Query(None),
    started: Optional[bool] = Query(None),
    subject_ids: Optional[List[int]] = Query(None),
    subject_types: Optional[List[str]] = Query(None),
    unlocked: Optional[bool] = Query(None),
    updated_after: Optional[datetime] = Query(None),
    service: HanachanService = Depends(get_service),
):
    """Get all assignments"""
    try:
        return await service.get_assignments(
            available_after=available_after,
            available_before=available_before,
            burned=burned,
            hidden=hidden,
            ids=ids,
            immediately_available_for_lessons=immediately_available_for_lessons,
            immediately_available_for_review=immediately_available_for_review,
            in_review=in_review,
            levels=levels,
            srs_stages=srs_stages,
            started=started,
            subject_ids=subject_ids,
            subject_types=subject_types,
            unlocked=unlocked,
            updated_after=updated_after,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/assignments/{assignment_id}")
async def get_assignment(
    assignment_id: str,
    service: HanachanService = Depends(get_service),
):
    """Get a specific assignment"""
    try:
        return await service.get_assignment(assignment_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/assignments/{assignment_id}/start")
async def start_assignment(
    assignment_id: str,
    body: AssignmentStart,
    service: HanachanService = Depends(get_service),
):
    """Start an assignment"""
    try:
        return await service.start_assignment(assignment_id, body.started_at)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/level_progressions")
async def get_level_progressions(
    ids: Optional[str] = Query(None),
    updated_after: Optional[datetime] = Query(None),
    service: HanachanService = Depends(get_service),
):
    """Get all level progressions"""
    try:
        return await service.get_level_progressions(ids=ids, updated_after=updated_after)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/level_progressions/{progression_id}")
async def get_level_progression(
    progression_id: str,
    service: HanachanService = Depends(get_service),
):
    """Get a specific level progression"""
    try:
        return await service.get_level_progression(progression_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/resets")
async def get_resets(
    ids: Optional[str] = Query(None),
    updated_after: Optional[datetime] = Query(None),
    service: HanachanService = Depends(get_service),
):
    """Get all resets"""
    try:
        return await service.get_resets(ids=ids, updated_after=updated_after)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/resets/{reset_id}")
async def get_reset(
    reset_id: str,
    service: HanachanService = Depends(get_service),
):
    """Get a specific reset"""
    try:
        return await service.get_reset(reset_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reviews")
async def get_reviews(
    ids: Optional[str] = Query(None),
    updated_after: Optional[datetime] = Query(None),
    assignment_ids: Optional[str] = Query(None),
    subject_ids: Optional[str] = Query(None),
    service: HanachanService = Depends(get_service),
):
    """Get all reviews"""
    try:
        return await service.get_reviews(
            ids=ids,
            updated_after=updated_after,
            assignment_ids=assignment_ids,
            subject_ids=subject_ids,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/reviews")
async def create_review(
    body: ReviewCreate,
    service: HanachanService = Depends(get_service),
):
    """Create a review"""
    try:
        return await service.create_review(
            assignment_id=body.review.assignment_id,
            incorrect_meaning_answers=body.review.incorrect_meaning_answers,
            incorrect_reading_answers=body.review.incorrect_reading_answers,
            created_at=body.review.created_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/reviews/{review_id}")
async def get_review(
    review_id: str,
    service: HanachanService = Depends(get_service),
):
    """Get a specific review"""
    try:
        return await service.get_review(review_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/review_statistics")
async def get_review_statistics(
    ids: Optional[str] = Query(None),
    updated_after: Optional[datetime] = Query(None),
    hidden: Optional[bool] = Query(None),
    subject_ids: Optional[str] = Query(None),
    subject_types: Optional[List[str]] = Query(None),
    percentages_greater_than: Optional[int] = Query(None),
    percentages_less_than: Optional[int] = Query(None),
    service: HanachanService = Depends(get_service),
):
    """Get all review statistics"""
    try:
        return await service.get_review_statistics(
            ids=ids,
            updated_after=updated_after,
            hidden=hidden,
            subject_ids=subject_ids,
            subject_types=subject_types,
            percentages_greater_than=percentages_greater_than,
            percentages_less_than=percentages_less_than,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/review_statistics/{statistic_id}")
async def get_review_statistic(
    statistic_id: str,
    service: HanachanService = Depends(get_service),
):
    """Get a specific review statistic"""
    try:
        return await service.get_review_statistic(statistic_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/spaced_repetition_systems")
async def get_spaced_repetition_systems(
    hidden: Optional[bool] = Query(None),
    ids: Optional[str] = Query(None),
    updated_after: Optional[datetime] = Query(None),
    subject_ids: Optional[str] = Query(None),
    subject_types: Optional[List[str]] = Query(None),
    service: HanachanService = Depends(get_service),
):
    """Get all spaced repetition systems"""
    try:
        return await service.get_spaced_repetition_systems(
            hidden=hidden,
            ids=ids,
            updated_after=updated_after,
            subject_ids=subject_ids,
            subject_types=subject_types,
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/spaced_repetition_systems/{srs_id}")
async def get_spaced_repetition_system(
    srs_id: str,
    service: HanachanService = Depends(get_service),
):
    """Get a specific spaced repetition system"""
    try:
        return await service.get_spaced_repetition_system(srs_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/study_materials")
async def get_study_materials(
    ids: Optional[str] = Query(None),
    updated_after: Optional[datetime] = Query(None),
    service: HanachanService = Depends(get_service),
):
    """Get all study materials"""
    try:
        return await service.get_study_materials(ids=ids, updated_after=updated_after)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/study_materials")
async def create_study_material(
    body: StudyMaterialCreate,
    service: HanachanService = Depends(get_service),
):
    """Create a new study material"""
    try:
        return await service.create_study_material(
            subject_id=body.study_material.subject_id,
            meaning_note=body.study_material.meaning_note,
            reading_note=body.study_material.reading_note,
            meaning_synonyms=body.study_material.meaning_synonyms,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/study_materials/{material_id}")
async def get_study_material(
    material_id: str,
    service: HanachanService = Depends(get_service),
):
    """Get a specific study material"""
    try:
        return await service.get_study_material(material_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/study_materials/{material_id}")
async def update_study_material(
    material_id: str,
    body: StudyMaterialUpdate,
    service: HanachanService = Depends(get_service),
):
    """Update a study material"""
    try:
        return await service.update_study_material(
            material_id=material_id,
            meaning_note=body.study_material.meaning_note,
            reading_note=body.study_material.reading_note,
            meaning_synonyms=body.study_material.meaning_synonyms,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/summary")
async def get_summary(
    service: HanachanService = Depends(get_service),
):
    """Get summary of available lessons and reviews"""
    try:
        return await service.get_summary()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/subjects")
async def get_subjects(
    updated_after: Optional[datetime] = Query(None),
    service: HanachanService = Depends(get_service),
):
    """Get all subjects"""
    try:
        return await service.get_subjects(updated_after=updated_after)
    except Exception as e:
        import traceback
        print(f"ERROR in get_subjects: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/subjects/{subject_id}")
async def get_subject(
    subject_id: int,
    service: HanachanService = Depends(get_service),
):
    """Get a specific subject"""
    try:
        return await service.get_subject(subject_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Sync – replaces the crawl-wanikani Edge Function
# =============================================================================
@router.post("/sync")
async def sync_wanikani(
    body: SyncRequest,
    service: HanachanService = Depends(get_service),
):
    """
    Sync subjects, assignments, and review statistics from WaniKani.
    Replaces the crawl-wanikani Supabase Edge Function.
    Modes:
    - merge: Upsert data (current behavior)
    - overwrite: Clear user data first, then sync
    """
    try:
        return await service.sync_wanikani(
            api_key=body.api_key,
            mode=body.mode
        )
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
