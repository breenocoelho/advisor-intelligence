from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def list_clients():
    return []