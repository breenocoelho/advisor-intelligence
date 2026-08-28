from app.models.organization import Organization
from app.models.user import User
from app.models.advisor import Advisor
from app.models.client import Client
from app.models.client_advisor_history import ClientAdvisorHistory
from app.models.account import Account
from app.models.asset import Asset
from app.models.position import Position
from app.models.alert import Alert
from app.models.positivador_snapshot import PositivadorSnapshot
from app.models.task import Task
from app.models.threshold_rule import ThresholdRule
from app.models.insight import Insight
from app.models.client_daily_snapshot import ClientDailySnapshot
from app.models.advisor_daily_snapshot import AdvisorDailySnapshot
from app.models.client_interaction import ClientInteraction
from app.models.benchmark import Benchmark, BenchmarkValue
from app.models.audit_log import AuditLog
from app.models.client_field_override import ClientFieldOverride
from app.models.client_extended_field import (
    ClientExtendedFieldDefinition, ClientExtendedFieldOption, ClientExtendedFieldAssignment,
)
from app.models.opportunity import Opportunity