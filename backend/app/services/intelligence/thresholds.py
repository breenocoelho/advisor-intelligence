"""
Modulo central de thresholds. Antes, cada regra do alert_engine tinha sua
propria constante hardcoded; agora todo mundo (alert_engine, signals,
health_score) resolve o valor por aqui, permitindo parametrizacao por
perfil de suitability sem que cada chamador saiba de onde o numero vem.

Resolucao (get_threshold): regra especifica do perfil do cliente -> default
da org -> default do sistema (hardcoded abaixo, nunca falha).
"""
from decimal import Decimal

from app.models import ThresholdRule

DEFAULT_THRESHOLDS: dict[str, Decimal] = {
    "idle_cash": Decimal("0.20"),
    "concentration": Decimal("0.40"),
    "concentration_issuer": Decimal("0.40"),
    "upcoming_maturity_days": Decimal("30"),
    "relevant_movement": Decimal("0.20"),
    "no_contact_days": Decimal("30"),
    "health_score_good": Decimal("80"),
    "health_score_warn": Decimal("60"),
    # cadencia de contato por tier de cliente (Relationship Intelligence) --
    # nao e' regra fixa no codigo, e' configuravel por org via /config/thresholds
    "high_value_aum_threshold": Decimal("1000000"),
    "contact_cadence_high_value_days": Decimal("30"),
    "contact_cadence_standard_days": Decimal("60"),
    "contact_cadence_low_engagement_days": Decimal("90"),
    "relationship_score_good": Decimal("80"),
    "relationship_score_warn": Decimal("60"),
}


def get_threshold(db, signal_key: str, org_id, client=None, cache: dict | None = None) -> Decimal:
    """cache (opcional): dict pre-carregado por preload_threshold_cache, pra
    resolver em memoria em vez de bater no banco a cada chamada -- usado
    pelos endpoints que resolvem threshold pra muitos clientes na mesma
    requisicao (ex: lista de clientes), onde uma query por (regra, cliente)
    vira centenas de round-trips."""
    suitability = getattr(client, "suitability", None)

    if cache is not None:
        return cache.get((signal_key, suitability), cache.get((signal_key, None), DEFAULT_THRESHOLDS[signal_key]))

    if suitability:
        rule = (
            db.query(ThresholdRule)
            .filter(
                ThresholdRule.org_id == org_id,
                ThresholdRule.signal_key == signal_key,
                ThresholdRule.suitability_profile == suitability,
            )
            .first()
        )
        if rule is not None:
            return Decimal(rule.value)

    org_default = (
        db.query(ThresholdRule)
        .filter(
            ThresholdRule.org_id == org_id,
            ThresholdRule.signal_key == signal_key,
            ThresholdRule.suitability_profile.is_(None),
        )
        .first()
    )
    if org_default is not None:
        return Decimal(org_default.value)

    return DEFAULT_THRESHOLDS[signal_key]


def preload_threshold_cache(db, org_id, signal_keys: list[str]) -> dict:
    """Busca todas as ThresholdRule relevantes da org numa unica query e
    monta um dict {(signal_key, suitability_profile_ou_None): Decimal},
    ja' resolvendo o default do sistema pras chaves sem nenhum override.
    Passar o resultado pra get_threshold(..., cache=...) evita 1 query por
    (regra, cliente)."""
    rules = (
        db.query(ThresholdRule)
        .filter(ThresholdRule.org_id == org_id, ThresholdRule.signal_key.in_(signal_keys))
        .all()
    )
    cache: dict = {(key, None): DEFAULT_THRESHOLDS[key] for key in signal_keys if key in DEFAULT_THRESHOLDS}
    for rule in rules:
        cache[(rule.signal_key, rule.suitability_profile)] = Decimal(rule.value)
    return cache
