"""
"What Changed?" (Prioridade 7) -- funcionalidade transversal que responde
"o que mudou neste periodo". Nao e' uma tabela nova: reaproveita a mesma
fonte de verdade dos endpoints de analytics (client_daily_snapshot /
advisor_daily_snapshot), so' que filtrando e formatando apenas as
variacoes que passam de um piso de materialidade -- pra nao virar uma
segunda planilha ao lado da de Analytics.
"""
from dataclasses import dataclass
from datetime import date

from app.models import ClientDailySnapshot, AdvisorDailySnapshot
from app.services.intelligence.thresholds import get_threshold
from app.services.intelligence.relationship_score import get_contact_cadence_days

PP_MATERIALITY = 5.0  # mesmo piso ja usado no frontend (AnalyticsTab) pra marcar "mudança relevante"

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


@dataclass
class ChangeItem:
    label: str
    direction: str  # "up" | "down" | "neutral"
    value_display: str


def compute_client_what_changed(
    db, org_id, client, date_from: date | None, date_to: date | None,
    has_interaction: bool = False, cache: dict | None = None,
) -> list[ChangeItem]:
    query = db.query(ClientDailySnapshot).filter(ClientDailySnapshot.client_id == client.id)
    if date_from:
        query = query.filter(ClientDailySnapshot.snapshot_date >= date_from)
    if date_to:
        query = query.filter(ClientDailySnapshot.snapshot_date <= date_to)
    snapshots = query.order_by(ClientDailySnapshot.snapshot_date).all()

    items: list[ChangeItem] = []

    if len(snapshots) >= 2:
        start, end = snapshots[0], snapshots[-1]

        min_aum_delta = float(get_threshold(db, "what_changed_min_aum_delta_pct", org_id, client, cache=cache))
        if start.aum and float(start.aum) > 0:
            aum_pct = (float(end.aum or 0) - float(start.aum)) / float(start.aum)
            if abs(aum_pct) >= min_aum_delta:
                items.append(ChangeItem(
                    label="AUM",
                    direction="up" if aum_pct >= 0 else "down",
                    value_display=f"{'+' if aum_pct >= 0 else ''}{aum_pct * 100:.1f}%",
                ))

        if start.allocation_json and end.allocation_json:
            classes = set(start.allocation_json) | set(end.allocation_json)
            for asset_class in classes:
                pct_start = float(start.allocation_json.get(asset_class, 0)) * 100
                pct_end = float(end.allocation_json.get(asset_class, 0)) * 100
                delta_pp = pct_end - pct_start
                if abs(delta_pp) >= PP_MATERIALITY:
                    label = ASSET_CLASS_LABELS.get(asset_class, asset_class)
                    items.append(ChangeItem(
                        label=label,
                        direction="up" if delta_pp >= 0 else "down",
                        value_display=f"{'+' if delta_pp >= 0 else ''}{delta_pp:.1f}pp",
                    ))

        gross_inflow = sum(float(s.monthly_purchase_value or 0) for s in snapshots)
        gross_outflow = sum(float(s.monthly_sale_value or 0) for s in snapshots)
        net_flow = gross_inflow - gross_outflow
        if start.aum and float(start.aum) > 0 and abs(net_flow) / float(start.aum) >= min_aum_delta:
            items.append(ChangeItem(
                label="Net Flow",
                direction="up" if net_flow >= 0 else "down",
                value_display=f"{'+' if net_flow >= 0 else '-'} R$ {abs(net_flow):,.0f}",
            ))

        top_issuer_start = float(start.top_issuer_concentration or 0) * 100
        top_issuer_end = float(end.top_issuer_concentration or 0) * 100
        delta_issuer = top_issuer_end - top_issuer_start
        if abs(delta_issuer) >= PP_MATERIALITY:
            items.append(ChangeItem(
                label="Concentração de emissor",
                direction="up" if delta_issuer >= 0 else "down",
                value_display=f"{'+' if delta_issuer >= 0 else ''}{delta_issuer:.1f}pp",
            ))

    # Status de contato (independe do range de datas -- e' "agora")
    cadence_days = int(get_contact_cadence_days(db, org_id, client, has_any_interaction=has_interaction, cache=cache))
    if client.last_contact_at is not None:
        days_since = (date.today() - client.last_contact_at.date()).days
        if days_since > cadence_days:
            items.append(ChangeItem(
                label="Contato",
                direction="down",
                value_display=f"Sem contato há {days_since} dias ({days_since - cadence_days} além da cadência)",
            ))

    return items


def compute_advisor_what_changed(db, org_id, advisor, date_from: date | None, date_to: date | None) -> list[ChangeItem]:
    query = db.query(AdvisorDailySnapshot).filter(AdvisorDailySnapshot.advisor_id == advisor.id)
    if date_from:
        query = query.filter(AdvisorDailySnapshot.snapshot_date >= date_from)
    if date_to:
        query = query.filter(AdvisorDailySnapshot.snapshot_date <= date_to)
    snapshots = query.order_by(AdvisorDailySnapshot.snapshot_date).all()

    items: list[ChangeItem] = []
    if len(snapshots) < 2:
        return items

    start, end = snapshots[0], snapshots[-1]

    if start.aum and float(start.aum) > 0:
        aum_pct = (float(end.aum or 0) - float(start.aum)) / float(start.aum)
        if abs(aum_pct) >= 0.03:
            items.append(ChangeItem(
                label="AUM",
                direction="up" if aum_pct >= 0 else "down",
                value_display=f"{'+' if aum_pct >= 0 else ''}{aum_pct * 100:.1f}%",
            ))

    net_flow_total = sum(float(s.net_flow or 0) for s in snapshots)
    if start.aum and float(start.aum) > 0 and abs(net_flow_total) / float(start.aum) >= 0.03:
        items.append(ChangeItem(
            label="Net Flow",
            direction="up" if net_flow_total >= 0 else "down",
            value_display=f"{'+' if net_flow_total >= 0 else '-'} R$ {abs(net_flow_total):,.0f}",
        ))

    client_delta = (end.client_count or 0) - (start.client_count or 0)
    if client_delta != 0:
        items.append(ChangeItem(
            label="Carteira de clientes",
            direction="up" if client_delta > 0 else "down",
            value_display=f"{'+' if client_delta > 0 else ''}{client_delta} cliente(s)",
        ))

    return items
