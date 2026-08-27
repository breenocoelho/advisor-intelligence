"""
Popula os benchmarks mais usados no mercado brasileiro (CDI, Ibovespa,
IPCA, Dolar) com serie sintetica indexada a 100 na primeira data --
mesmas datas do client_daily_snapshot, pra poder comparar diretamente
nos graficos do Client 360 / Assessores. Nao toca em nenhuma tabela de
cliente (positions, snapshots, etc.) -- so' cria/atualiza essas duas
tabelas de referencia, pequenas e independentes.
"""
import random
from decimal import Decimal

from app.database import SessionLocal
from app.models import Benchmark, BenchmarkValue, ClientDailySnapshot

# taxa anual aproximada e volatilidade anual -- heuristica de mock, nao
# dado de mercado real
BENCHMARKS = {
    "cdi": {"name": "CDI", "annual_rate": 0.1375, "annual_vol": 0.0},
    "ibovespa": {"name": "Ibovespa", "annual_rate": 0.12, "annual_vol": 0.18},
    "ipca": {"name": "IPCA", "annual_rate": 0.045, "annual_vol": 0.0},
    "usd": {"name": "Dólar (USD/BRL)", "annual_rate": 0.02, "annual_vol": 0.10},
}


def main():
    db = SessionLocal()
    dates = sorted({row[0] for row in db.query(ClientDailySnapshot.snapshot_date).distinct().all()})
    if not dates:
        print("Sem client_daily_snapshot -- rode o replay historico primeiro.")
        return

    periods_per_year = 52  # snapshots semanais
    rng = random.Random(42)

    for key, cfg in BENCHMARKS.items():
        benchmark = db.query(Benchmark).filter(Benchmark.key == key).first()
        if benchmark is None:
            benchmark = Benchmark(key=key, name=cfg["name"])
            db.add(benchmark)
            db.flush()
        else:
            db.query(BenchmarkValue).filter(BenchmarkValue.benchmark_id == benchmark.id).delete()

        period_drift = cfg["annual_rate"] / periods_per_year
        period_vol = cfg["annual_vol"] / (periods_per_year ** 0.5)
        index = Decimal("100")
        for i, d in enumerate(dates):
            if i > 0:
                shock = rng.gauss(0, period_vol) if period_vol else 0.0
                index = index * Decimal(str(round(1 + period_drift + shock, 6)))
            db.add(BenchmarkValue(benchmark_id=benchmark.id, value_date=d, index_value=index))
        db.commit()

    print(f"{len(BENCHMARKS)} benchmarks, {len(dates)} pontos cada ({dates[0]} a {dates[-1]}).")


if __name__ == "__main__":
    main()
