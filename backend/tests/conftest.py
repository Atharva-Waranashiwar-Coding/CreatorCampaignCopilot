from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.api.deps import get_current_user
from app.core.enums import BrandRole, CampaignStatus, MembershipStatus, PlanInterval, ProjectStatus, SubscriptionStatus
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.brand import Brand
from app.models.brand_membership import BrandMembership
from app.models.brand_subscription import BrandSubscription
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.plan import Plan
from app.models.project import Project
from app.models.user import User
from app.services.draft_workflows import build_default_draft_workflow_payload


@dataclass
class SeededWorkspace:
    user: User
    plan: Plan
    brand: Brand
    project: Project
    campaign: Campaign
    draft: ContentDraft


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record) -> None:  # type: ignore[no-untyped-def]
        del connection_record
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, class_=Session)
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def seeded_workspace(db_session: Session) -> SeededWorkspace:
    user = User(
        full_name="Test User",
        email="tester@example.com",
        password_hash="not-used",
    )
    db_session.add(user)
    db_session.flush()

    plan = Plan(
        code="growth",
        name="Growth",
        description="Growth test plan",
        monthly_price_cents=4900,
        yearly_price_cents=49000,
        limits_json={
            "max_members": 25,
            "max_active_campaigns": 50,
            "max_templates": 100,
            "max_scheduled_items": 100,
            "max_monthly_review_actions": 500,
            "max_monthly_helper_runs": 200,
            "max_monthly_advanced_helper_runs": 80,
            "max_saved_helper_artifacts": 50,
            "max_helper_runs_per_10_minutes": 20,
            "max_advanced_helper_runs_per_10_minutes": 10,
        },
        features_json={
            "template_library": True,
            "advanced_analytics": True,
            "priority_support": False,
            "helper_tools": True,
            "advanced_ai_helpers": True,
        },
        is_active=True,
        sort_order=1,
    )
    db_session.add(plan)
    db_session.flush()

    brand = Brand(
        name="Acme",
        slug="acme",
        description="B2B software brand",
        industry="Software",
        tone_of_voice="Measured, helpful, evidence-based",
        target_audience="Marketing leaders and demand generation teams",
        preferred_channels=["LinkedIn", "Instagram"],
        guidelines_summary="Lead with outcomes, support claims with proof, keep the tone controlled.",
        draft_workflow_config=build_default_draft_workflow_payload(),
        created_by=user.id,
    )
    db_session.add(brand)
    db_session.flush()

    membership = BrandMembership(
        brand_id=brand.id,
        user_id=user.id,
        invite_email=user.email,
        invited_by_id=user.id,
        role=BrandRole.OWNER,
        status=MembershipStatus.ACTIVE,
        joined_at=datetime.now(UTC),
    )
    subscription = BrandSubscription(
        brand_id=brand.id,
        plan_id=plan.id,
        status=SubscriptionStatus.ACTIVE,
        billing_interval=PlanInterval.MONTHLY,
        current_period_start=datetime.now(UTC) - timedelta(days=2),
        current_period_end=datetime.now(UTC) + timedelta(days=28),
        cancel_at_period_end=False,
        plan_snapshot_json={
            "code": plan.code,
            "name": plan.name,
        },
    )
    db_session.add_all([membership, subscription])
    db_session.flush()

    project = Project(
        brand_id=brand.id,
        name="Pipeline Push",
        description="Q2 pipeline campaign",
        status=ProjectStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(project)
    db_session.flush()

    campaign = Campaign(
        project_id=project.id,
        name="Spring Launch",
        objective="Drive demo demand",
        audience="Marketing leaders",
        campaign_type="Demand gen",
        status=CampaignStatus.ACTIVE,
        created_by=user.id,
    )
    db_session.add(campaign)
    db_session.flush()

    draft = ContentDraft(
        campaign_id=campaign.id,
        title="Proof-backed launch plan",
        platform="LinkedIn",
        content_type="Thought leadership post",
        content_body=(
            "Teams that want more predictable pipeline need a cleaner launch plan. "
            "This framework shows how to align proof points, creative, and CTA timing. "
            "Reply if you want the rollout checklist."
        ),
        status="draft",
        created_by=user.id,
    )
    db_session.add(draft)
    db_session.commit()

    return SeededWorkspace(
        user=user,
        plan=plan,
        brand=brand,
        project=project,
        campaign=campaign,
        draft=draft,
    )


@pytest.fixture
def client(db_session: Session, seeded_workspace: SeededWorkspace) -> TestClient:
    def _override_get_db():
        yield db_session

    def _override_get_current_user() -> User:
        return db_session.get(User, seeded_workspace.user.id)

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _override_get_current_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
