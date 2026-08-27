from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.deps import get_db
from app.models import Benchmark, BenchmarkValue
from app.schemas import BenchmarkOut, BenchmarkSeriesPointOut

router = APIRouter()


@router.get("/", response_model=list[BenchmarkOut])
def list_benchmarks(
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = db.query(Benchmark).order_by(Benchmark.name).all()
    return [BenchmarkOut(key=b.key, name=b.name) for b in rows]


@router.get("/{key}/series", response_model=list[BenchmarkSeriesPointOut])
def get_benchmark_series(
    key: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    benchmark = db.query(Benchmark).filter(Benchmark.key == key).first()
    if benchmark is None:
        return []
    rows = (
        db.query(BenchmarkValue)
        .filter(BenchmarkValue.benchmark_id == benchmark.id)
        .order_by(BenchmarkValue.value_date)
        .all()
    )
    return [BenchmarkSeriesPointOut(value_date=r.value_date, index_value=float(r.index_value)) for r in rows]
