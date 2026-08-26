from fastapi import APIRouter, Depends
from app.auth import get_current_user

router = APIRouter()

router = APIRouter()

@router.get("/")
def list_alerts(current_user: dict = Depends(get_current_user)):
    return []