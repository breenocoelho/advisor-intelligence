from app.models import AuditLog


def log_action(db, org_id, action_type: str, summary: str, client_id=None) -> None:
    """Grava uma linha de audit log. Chamado a partir de agora nos pontos
    de escrita que importam pra visao de administrador (tarefas,
    interacoes, contato, status de alerta, thresholds, overrides de
    cadastro, campos customizados) -- nao e' um backfill do que ja
    aconteceu antes desse ponto."""
    db.add(AuditLog(org_id=org_id, client_id=client_id, action_type=action_type, summary=summary))
