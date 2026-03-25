from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.content_brief import ContentBrief
from app.models.project import Project
from app.models.user import User
from app.schemas.content_brief import ContentBriefCreate, ContentBriefRead, ContentBriefUpdate
from app.services.audit import record_audit_log


def _serialize_brief(brief: ContentBrief) -> ContentBriefRead:
    return ContentBriefRead(
        id=brief.id,
        campaign_id=brief.campaign_id,
        key_message=brief.key_message,
        call_to_action=brief.call_to_action,
        tone=brief.tone,
        channels=brief.channels,
        themes=brief.themes,
        references=brief.reference_materials,
        created_at=brief.created_at,
        updated_at=brief.updated_at,
    )


def _get_campaign_with_role(db: Session, *, campaign_id: int, user_id: int) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(selectinload(Campaign.brief), selectinload(Campaign.project).selectinload(Project.brand))
        .where(
            Campaign.id == campaign_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this campaign.")

    return row[0], row[1]


def get_campaign_brief(db: Session, *, campaign_id: int, user: User) -> ContentBriefRead | None:
    campaign, _ = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    return _serialize_brief(campaign.brief) if campaign.brief else None


def upsert_campaign_brief(
    db: Session,
    *,
    campaign_id: int,
    payload: ContentBriefCreate | ContentBriefUpdate,
    user: User,
) -> ContentBriefRead:
    campaign, membership = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign briefs.",
    )

    brief = campaign.brief
    is_create = brief is None
    if brief is None:
        brief = ContentBrief(campaign_id=campaign.id)
        db.add(brief)
        db.flush()

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        if field == "references":
            brief.reference_materials = value
        elif isinstance(value, str):
            setattr(brief, field, value.strip())
        else:
            setattr(brief, field, value)

    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="content_brief",
        entity_id=brief.id,
        action="brief.created" if is_create else "brief.updated",
        metadata={"campaign_id": campaign.id},
    )
    db.commit()
    db.refresh(brief)
    return _serialize_brief(brief)


def delete_campaign_brief(db: Session, *, campaign_id: int, user: User) -> None:
    campaign, membership = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign briefs.",
    )
    if campaign.brief is None:
        raise LookupError("Brief not found.")

    brief_id = campaign.brief.id
    db.delete(campaign.brief)
    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="content_brief",
        entity_id=brief_id,
        action="brief.deleted",
        metadata={"campaign_id": campaign.id},
    )
    db.commit()
