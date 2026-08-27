# app/models/benchmark.py
import uuid
from sqlalchemy import Column, String, Numeric, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base

class Benchmark(Base):
    __tablename__ = "benchmarks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key = Column(String, unique=True, nullable=False)  # "cdi" | "ibovespa" | "ipca" | "usd"
    name = Column(String, nullable=False)


class BenchmarkValue(Base):
    __tablename__ = "benchmark_values"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    benchmark_id = Column(UUID(as_uuid=True), ForeignKey("benchmarks.id"), nullable=False)
    value_date = Column(Date, nullable=False)
    index_value = Column(Numeric, nullable=False)  # indexado a 100 na primeira data da serie
