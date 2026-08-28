"""
Behavioral Health (Client Health Intelligence, camada 3 -- ao lado de
Portfolio Health/health_score.py e Relationship Health/relationship_score.py).

Nao compara o cliente contra uma regra fixa do sistema -- compara o cliente
contra o PROPRIO historico (baseline individual), como pede a spec:
"a logica deve considerar baseline individual do cliente". Sem baseline
suficiente, nao infere nada (retorna lista vazia em vez de arriscar falso
positivo com pouco dado).
"""
import statistics
from dataclasses import dataclass

from app.services.intelligence.thresholds import get_threshold


@dataclass
class BehavioralFinding:
    finding_type: str  # "unusual_movement" | "unusual_allocation_shift"
    severity: str  # "critical" | "opportunity" | "follow_up"
    label: str
    detail: str


ASSET_CLASS_LABELS: dict[str, str] = {
    "coe": "COE",
    "funds": "Fundos de Investimento",
    "fixedIncome": "Renda Fixa",
    "checkingAccount": "Caixa / Disponível",
    "pensionFunds": "Previdência",
    "repo": "Compromissada",
    "treasury": "Tesouro Direto",
    "stock": "Ações",
    "tradedFunds": "Fundos Imobiliários",
}


def compute_behavioral_findings(db, org_id, client, snapshots: list, cache: dict | None = None) -> list[BehavioralFinding]:
    """snapshots: historico de ClientDailySnapshot do cliente, ja ordenado
    por snapshot_date (evita re-buscar -- o caller normalmente ja tem essa
    lista em maos, ex: get_client_detail)."""
    min_points = int(get_threshold(db, "behavioral_anomaly_min_history_points", org_id, client, cache=cache))
    if len(snapshots) < min_points + 1:
        return []

    baseline = snapshots[:-1]
    current = snapshots[-1]
    k = float(get_threshold(db, "behavioral_anomaly_stdev_multiplier", org_id, client, cache=cache))

    findings: list[BehavioralFinding] = []

    # Movimentacao (aportes + resgates do periodo) fora do padrao individual
    baseline_movement = [float(s.monthly_purchase_value or 0) + float(s.monthly_sale_value or 0) for s in baseline]
    current_movement = float(current.monthly_purchase_value or 0) + float(current.monthly_sale_value or 0)
    if len(baseline_movement) >= 2:
        mean_movement = statistics.mean(baseline_movement)
        stdev_movement = statistics.pstdev(baseline_movement)
        threshold_movement = mean_movement + k * stdev_movement
        if current_movement > threshold_movement and current_movement > 0:
            findings.append(BehavioralFinding(
                finding_type="unusual_movement",
                severity="critical",
                label="Movimentação fora do padrão",
                detail=(
                    f"Histórico do cliente: R$ {min(baseline_movement):,.0f}–R$ {max(baseline_movement):,.0f} "
                    f"por período. Movimentação atual: R$ {current_movement:,.0f}."
                ),
            ))

    # Mudanca de alocacao por classe fora do padrao individual (mesma logica,
    # aplicada ao peso % de cada classe no lugar do valor movimentado)
    baseline_alloc: dict[str, list[float]] = {}
    for s in baseline:
        for asset_class, pct in (s.allocation_json or {}).items():
            baseline_alloc.setdefault(asset_class, []).append(float(pct or 0))

    current_alloc = current.allocation_json or {}
    for asset_class, current_pct in current_alloc.items():
        history = baseline_alloc.get(asset_class, [])
        if len(history) < 2:
            continue
        mean_pct = statistics.mean(history)
        stdev_pct = statistics.pstdev(history)
        if stdev_pct <= 0:
            continue
        delta = abs(float(current_pct or 0) - mean_pct)
        if delta > k * stdev_pct and delta >= 0.05:
            label = ASSET_CLASS_LABELS.get(asset_class, asset_class)
            direction = "aumentou" if current_pct > mean_pct else "caiu"
            findings.append(BehavioralFinding(
                finding_type="unusual_allocation_shift",
                severity="follow_up",
                label=f"Alocação em {label} fora do padrão",
                detail=(
                    f"Historicamente em torno de {mean_pct * 100:.1f}% da carteira, "
                    f"{direction} para {float(current_pct or 0) * 100:.1f}%."
                ),
            ))

    return findings
