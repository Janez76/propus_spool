"""
Tags endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas import (
    TagResponse,
    TagDetailResponse,
    SpoolMapCreate,
    SpoolMapResponse,
    TareRequest
)
from app.services.tags import (
    list_tags,
    get_tag_detail,
    assign_spool_to_tag,
    set_tag_tare
)

router = APIRouter()


@router.get("/tags", response_model=List[TagResponse])
async def get_tags(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """
    List all tags
    
    Returns a list of all NFC tags that have been seen by the system
    """
    return list_tags(db, skip=skip, limit=limit)


@router.get("/tags/{uid}", response_model=TagDetailResponse)
async def get_tag(uid: str, db: Session = Depends(get_db)):
    """
    Get details for a specific tag
    
    Returns tag information along with spool mapping and state
    """
    tag = get_tag_detail(db, uid)
    if not tag:
        raise HTTPException(status_code=404, detail="Tag not found")
    return tag


@router.post("/tags/{uid}/assign", response_model=SpoolMapResponse)
async def assign_spool(
    uid: str,
    assignment: SpoolMapCreate,
    db: Session = Depends(get_db)
):
    """
    Assign a Spoolman spool ID to a tag
    
    Creates or updates the mapping between an NFC tag UID and a Spoolman spool
    """
    try:
        return assign_spool_to_tag(db, uid, assignment)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tags/{uid}/tare", response_model=dict)
async def set_tare(
    uid: str,
    tare: TareRequest,
    db: Session = Depends(get_db)
):
    """
    Set tare weight for a tag
    
    Updates the tare weight and recalculates net weight for the spool
    """
    try:
        result = set_tag_tare(db, uid, tare.tare_weight_g)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
