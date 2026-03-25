from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import CampaignStatus, MembershipStatus
from app.models.audit_log import AuditLog
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.project import Project
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.dashboard import DashboardSummary


def get_dashboard_summary(db: Session, *, user: User) -> DashboardSummary:
    brand_ids = db.scalars(
        select(BrandMembership.brand_id).where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).all()
    if not brand_ids:
        return DashboardSummary(
            brand_count=0,
            project_count=0,
            campaign_count=0,
            active_campaign_count=0,
            recent_activity=[],
        )

    project_count = db.scalar(select(func.count(Project.id)).where(Project.brand_id.in_(brand_ids))) or 0
    campaign_count = db.scalar(
        select(func.count(Campaign.id)).join(Project, Project.id == Campaign.project_id).where(Project.brand_id.in_(brand_ids))
    ) or 0
    active_campaign_count = db.scalar(
        select(func.count(Campaign.id))
        .join(Project, Project.id == Campaign.project_id)
        .where(
            Project.brand_id.in_(brand_ids),
            Campaign.status == CampaignStatus.ACTIVE,
        )
    ) or 0

    recent_logs = db.scalars(
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .where(AuditLog.brand_id.in_(brand_ids))
        .order_by(AuditLog.created_at.desc())
        .limit(10)
    ).all()

    return DashboardSummary(
        brand_count=len(brand_ids),
        project_count=project_count,
        campaign_count=campaign_count,
        active_campaign_count=active_campaign_count,
        recent_activity=[
            AuditLogRead(
                id=log.id,
                brand_id=log.brand_id,
                actor_user_id=log.actor_user_id,
                actor_name=log.actor.full_name if log.actor else None,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                action=log.action,
                metadata=log.metadata_json,
                created_at=log.created_at,
            )
            for log in recent_logs
        ],
    )
