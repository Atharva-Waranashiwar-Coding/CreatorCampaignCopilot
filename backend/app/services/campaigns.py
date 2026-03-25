from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import CampaignStatus, MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.project import Project
from app.models.user import User
from app.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate
from app.services.audit import record_audit_log


def _serialize_campaign(campaign: Campaign) -> CampaignRead:
    return CampaignRead(
        id=campaign.id,
        project_id=campaign.project_id,
        project_name=campaign.project.name,
        brand_id=campaign.project.brand_id,
        brand_name=campaign.project.brand.name,
        name=campaign.name,
        objective=campaign.objective,
        audience=campaign.audience,
        campaign_type=campaign.campaign_type,
        start_date=campaign.start_date,
        end_date=campaign.end_date,
        status=campaign.status,
        created_by=campaign.created_by,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def _get_campaign_with_role(db: Session, *, campaign_id: int, user_id: int) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(selectinload(Campaign.project).selectinload(Project.brand))
        .where(
            Campaign.id == campaign_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this campaign.")
    return row[0], row[1]


def list_campaigns(
    db: Session,
    *,
    user: User,
    brand_id: int | None = None,
    project_id: int | None = None,
) -> list[CampaignRead]:
    query = (
        select(Campaign)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(selectinload(Campaign.project).selectinload(Project.brand))
        .where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
        .order_by(Campaign.created_at.desc())
    )
    if brand_id is not None:
        query = query.where(Project.brand_id == brand_id)
    if project_id is not None:
        query = query.where(Campaign.project_id == project_id)

    campaigns = db.scalars(query).all()
    return [_serialize_campaign(campaign) for campaign in campaigns]


def get_campaign(db: Session, *, campaign_id: int, user: User) -> CampaignRead:
    campaign, _ = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    return _serialize_campaign(campaign)


def create_campaign(db: Session, *, payload: CampaignCreate, user: User) -> CampaignRead:
    if payload.start_date and payload.end_date and payload.start_date > payload.end_date:
        raise ValueError("Campaign start date must be before the end date.")

    row = db.execute(
        select(Project, BrandMembership)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(selectinload(Project.brand))
        .where(
            Project.id == payload.project_id,
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this project.")

    project, membership = row[0], row[1]
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to create campaigns.",
    )

    campaign = Campaign(
        project_id=project.id,
        name=payload.name.strip(),
        objective=payload.objective,
        audience=payload.audience,
        campaign_type=payload.campaign_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status,
        created_by=user.id,
    )
    db.add(campaign)
    db.flush()

    record_audit_log(
        db,
        brand_id=project.brand_id,
        actor_user_id=user.id,
        entity_type="campaign",
        entity_id=campaign.id,
        action="campaign.created",
        metadata={"name": campaign.name, "project_id": project.id},
    )
    db.commit()
    db.refresh(campaign)
    return get_campaign(db, campaign_id=campaign.id, user=user)


def update_campaign(db: Session, *, campaign_id: int, payload: CampaignUpdate, user: User) -> CampaignRead:
    campaign, membership = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to update campaigns.",
    )

    data = payload.model_dump(exclude_unset=True)
    start_date = data.get("start_date", campaign.start_date)
    end_date = data.get("end_date", campaign.end_date)
    if start_date and end_date and start_date > end_date:
        raise ValueError("Campaign start date must be before the end date.")

    for field, value in data.items():
        setattr(campaign, field, value.strip() if isinstance(value, str) else value)

    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="campaign",
        entity_id=campaign.id,
        action="campaign.updated",
        metadata={"changes": {key: str(value) for key, value in data.items()}},
    )
    db.commit()
    db.refresh(campaign)
    return _serialize_campaign(campaign)


def delete_campaign(db: Session, *, campaign_id: int, user: User) -> None:
    campaign, membership = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to delete campaigns.",
    )
    db.delete(campaign)
    db.commit()
