from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import CampaignMilestoneKey, MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.campaign_milestone import CampaignMilestone
from app.models.project import Project
from app.models.user import User
from app.schemas.campaign_milestone import CampaignMilestoneRead, CampaignMilestoneUpdate
from app.services.audit import record_audit_log
from app.services.campaign_dependencies import assert_milestone_dependencies_satisfied

DEFAULT_CAMPAIGN_MILESTONES: list[dict[str, object]] = [
    {
        "key": CampaignMilestoneKey.BRIEF_APPROVED,
        "label": "Brief approved",
        "sort_order": 10,
    },
    {
        "key": CampaignMilestoneKey.FIRST_DRAFTS_READY,
        "label": "First drafts ready",
        "sort_order": 20,
    },
    {
        "key": CampaignMilestoneKey.ALL_REVIEWS_COMPLETE,
        "label": "All reviews complete",
        "sort_order": 30,
    },
    {
        "key": CampaignMilestoneKey.CAMPAIGN_LAUNCH_READY,
        "label": "Campaign launch ready",
        "sort_order": 40,
    },
    {
        "key": CampaignMilestoneKey.CAMPAIGN_COMPLETED,
        "label": "Campaign completed",
        "sort_order": 50,
    },
]


def serialize_campaign_milestone(milestone: CampaignMilestone) -> CampaignMilestoneRead:
    return CampaignMilestoneRead(
        id=milestone.id,
        campaign_id=milestone.campaign_id,
        key=milestone.key,
        label=milestone.label,
        sort_order=milestone.sort_order,
        target_date=milestone.target_date,
        completed_at=milestone.completed_at,
        completed_by_user_id=milestone.completed_by_user_id,
        completed_by_name=milestone.completed_by.full_name if milestone.completed_by else None,
        is_complete=milestone.completed_at is not None,
        notes=milestone.notes,
        created_at=milestone.created_at,
        updated_at=milestone.updated_at,
    )


def ensure_campaign_milestones(db: Session, *, campaign: Campaign) -> None:
    existing_keys = {
        milestone.key.value if isinstance(milestone.key, CampaignMilestoneKey) else str(milestone.key)
        for milestone in campaign.milestones
    }
    for milestone_template in DEFAULT_CAMPAIGN_MILESTONES:
        key = milestone_template["key"]
        key_value = key.value if isinstance(key, CampaignMilestoneKey) else str(key)
        if key_value in existing_keys:
            continue
        db.add(
            CampaignMilestone(
                campaign_id=campaign.id,
                key=key,
                label=str(milestone_template["label"]),
                sort_order=int(milestone_template["sort_order"]),
            )
        )
    db.flush()


def list_campaign_milestones(db: Session, *, campaign_id: int, user: User) -> list[CampaignMilestoneRead]:
    campaign, _ = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    ensure_campaign_milestones(db, campaign=campaign)
    db.refresh(campaign, attribute_names=["milestones"])
    return [serialize_campaign_milestone(milestone) for milestone in campaign.milestones]


def update_campaign_milestone(
    db: Session,
    *,
    campaign_id: int,
    milestone_id: int,
    payload: CampaignMilestoneUpdate,
    user: User,
) -> CampaignMilestoneRead:
    milestone, membership = _get_campaign_milestone_with_role(
        db,
        campaign_id=campaign_id,
        milestone_id=milestone_id,
        user_id=user.id,
    )
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to update campaign milestones.",
    )

    data = payload.model_dump(exclude_unset=True)
    changes: dict[str, object] = {}

    if "target_date" in data:
        milestone.target_date = data["target_date"]
        changes["target_date"] = str(data["target_date"]) if data["target_date"] is not None else None

    if "notes" in data:
        milestone.notes = data["notes"].strip() if isinstance(data["notes"], str) and data["notes"].strip() else None
        changes["notes"] = milestone.notes

    if "is_complete" in data and data["is_complete"] is not None:
        if data["is_complete"]:
            assert_milestone_dependencies_satisfied(db, milestone=milestone)
            milestone.completed_at = datetime.now(UTC)
            milestone.completed_by_user_id = user.id
        else:
            milestone.completed_at = None
            milestone.completed_by_user_id = None
        changes["is_complete"] = bool(data["is_complete"])

    record_audit_log(
        db,
        brand_id=milestone.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="campaign_milestone",
        entity_id=milestone.id,
        action="campaign.milestone_updated",
        metadata={
            "campaign_id": milestone.campaign_id,
            "milestone_key": milestone.key.value if isinstance(milestone.key, CampaignMilestoneKey) else str(milestone.key),
            "changes": changes,
        },
    )
    db.commit()
    db.refresh(milestone)
    return serialize_campaign_milestone(milestone)


def _get_campaign_with_role(db: Session, *, campaign_id: int, user_id: int) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            selectinload(Campaign.project).selectinload(Project.brand),
            selectinload(Campaign.milestones).joinedload(CampaignMilestone.completed_by),
        )
        .where(
            Campaign.id == campaign_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this campaign.")
    return row[0], row[1]


def _get_campaign_milestone_with_role(
    db: Session,
    *,
    campaign_id: int,
    milestone_id: int,
    user_id: int,
) -> tuple[CampaignMilestone, BrandMembership]:
    row = db.execute(
        select(CampaignMilestone, BrandMembership)
        .join(Campaign, Campaign.id == CampaignMilestone.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            joinedload(CampaignMilestone.completed_by),
            joinedload(CampaignMilestone.campaign).joinedload(Campaign.project).joinedload(Project.brand),
        )
        .where(
            CampaignMilestone.id == milestone_id,
            CampaignMilestone.campaign_id == campaign_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise LookupError("Campaign milestone not found.")
    return row[0], row[1]
