from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_alerts():
    return []