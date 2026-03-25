from collections import Counter

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import CampaignStatus, DraftStageType, MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.audit_log import AuditLog
from app.models.brand_membership import BrandMembership
from app.models.calendar_item import CalendarItem
from app.models.campaign import Campaign
from app.models.campaign_asset import CampaignAsset
from app.models.campaign_milestone import CampaignMilestone
from app.models.content_draft import ContentDraft
from app.models.draft_version import DraftVersion
from app.models.project import Project
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.schemas.calendar_item import CalendarItemRead
from app.schemas.campaign import CampaignCreate, CampaignRead, CampaignUpdate
from app.schemas.campaign_asset import CampaignAssetRead
from app.schemas.campaign_workspace import CampaignOverviewRead, CampaignPlanningSummaryRead
from app.schemas.content_brief import ContentBriefRead
from app.schemas.content_draft import ContentDraftRead, DraftWorkflowStageCount
from app.schemas.draft_version import DraftVersionRead
from app.services.access import assert_brand_limit_available
from app.services.audit import record_audit_log
from app.services.campaign_milestones import ensure_campaign_milestones, serialize_campaign_milestone
from app.services.draft_workflows import get_brand_draft_workflow, get_workflow_stage_or_raise


def _coerce_draft_status(value: str) -> str:
    return str(value)


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
        brief_id=campaign.brief.id if campaign.brief else None,
        draft_count=len(campaign.drafts),
    )


def _serialize_asset(asset: CampaignAsset) -> CampaignAssetRead:
    return CampaignAssetRead(
        id=asset.id,
        campaign_id=asset.campaign_id,
        name=asset.name,
        asset_type=asset.asset_type,
        file_url=asset.file_url,
        thumbnail_url=asset.thumbnail_url,
        mime_type=asset.mime_type,
        file_size_bytes=asset.file_size_bytes,
        notes=asset.notes,
        created_by=asset.created_by,
        creator_name=asset.creator.full_name if asset.creator else None,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _serialize_calendar_item(item: CalendarItem) -> CalendarItemRead:
    return CalendarItemRead(
        id=item.id,
        brand_id=item.brand_id,
        brand_name=item.campaign.project.brand.name,
        campaign_id=item.campaign_id,
        campaign_name=item.campaign.name,
        draft_id=item.draft_id,
        draft_title=item.draft.title if item.draft else None,
        title=item.title,
        platform=item.platform,
        item_type=item.item_type,
        scheduled_for=item.scheduled_for,
        status=item.status,
        notes=item.notes,
        created_by=item.created_by,
        creator_name=item.creator.full_name if item.creator else None,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _serialize_draft_version(version: DraftVersion) -> DraftVersionRead:
    draft = version.draft
    campaign = draft.campaign
    project = campaign.project
    stage = get_workflow_stage_or_raise(get_brand_draft_workflow(project.brand), version.status)
    return DraftVersionRead(
        id=version.id,
        draft_id=version.draft_id,
        draft_title=draft.title,
        campaign_id=campaign.id,
        campaign_name=campaign.name,
        project_id=project.id,
        project_name=project.name,
        brand_id=project.brand_id,
        brand_name=project.brand.name,
        version_number=version.version_number,
        title=version.title,
        platform=version.platform,
        content_type=version.content_type,
        content_body=version.content_body,
        status=stage.key,
        status_label=stage.label,
        status_type=stage.stage_type,
        status_color=stage.color,
        planned_publish_at=version.planned_publish_at,
        change_summary=version.change_summary,
        created_by=version.created_by,
        creator_name=version.creator.full_name if version.creator else None,
        created_at=version.created_at,
    )


def _get_campaign_with_role(db: Session, *, campaign_id: int, user_id: int) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            selectinload(Campaign.project).selectinload(Project.brand),
            selectinload(Campaign.brief),
            selectinload(Campaign.assets).joinedload(CampaignAsset.creator),
            selectinload(Campaign.milestones).joinedload(CampaignMilestone.completed_by),
            selectinload(Campaign.calendar_items).joinedload(CalendarItem.creator),
            selectinload(Campaign.calendar_items).joinedload(CalendarItem.draft),
            selectinload(Campaign.drafts).selectinload(ContentDraft.creator),
            selectinload(Campaign.drafts).selectinload(ContentDraft.reviews),
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
        .options(
            selectinload(Campaign.project).selectinload(Project.brand),
            selectinload(Campaign.brief),
            selectinload(Campaign.drafts).selectinload(ContentDraft.reviews),
        )
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


def _serialize_brief_for_campaign(campaign: Campaign) -> ContentBriefRead | None:
    if campaign.brief is None:
        return None

    return ContentBriefRead(
        id=campaign.brief.id,
        campaign_id=campaign.brief.campaign_id,
        key_message=campaign.brief.key_message,
        call_to_action=campaign.brief.call_to_action,
        tone=campaign.brief.tone,
        channels=campaign.brief.channels,
        themes=campaign.brief.themes,
        references=campaign.brief.reference_materials,
        created_at=campaign.brief.created_at,
        updated_at=campaign.brief.updated_at,
    )


def _serialize_draft_for_campaign(draft: ContentDraft) -> ContentDraftRead:
    stage = get_workflow_stage_or_raise(get_brand_draft_workflow(draft.campaign.project.brand), draft.status)
    latest_review = draft.reviews[0] if draft.reviews else None
    return ContentDraftRead(
        id=draft.id,
        campaign_id=draft.campaign_id,
        campaign_name=draft.campaign.name,
        project_id=draft.campaign.project_id,
        project_name=draft.campaign.project.name,
        brand_id=draft.campaign.project.brand_id,
        brand_name=draft.campaign.project.brand.name,
        title=draft.title,
        platform=draft.platform,
        content_type=draft.content_type,
        content_body=draft.content_body,
        status=stage.key,
        status_label=stage.label,
        status_type=stage.stage_type,
        status_color=stage.color,
        planned_publish_at=draft.planned_publish_at,
        current_version_number=draft.current_version_number,
        created_by=draft.created_by,
        creator_name=draft.creator.full_name if draft.creator else None,
        review_count=len(draft.reviews),
        latest_review_action=latest_review.action if latest_review else None,
        latest_reviewed_at=latest_review.created_at if latest_review else None,
        created_at=draft.created_at,
        updated_at=draft.updated_at,
    )


def _serialize_audit_log(log: AuditLog) -> AuditLogRead:
    return AuditLogRead(
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


def _belongs_to_campaign(log: AuditLog, campaign_id: int) -> bool:
    if log.entity_type == "campaign" and log.entity_id == campaign_id:
        return True

    campaign_ref = log.metadata_json.get("campaign_id")
    return campaign_ref in {campaign_id, str(campaign_id)}


def get_campaign_overview(db: Session, *, campaign_id: int, user: User) -> CampaignOverviewRead:
    campaign, _ = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    ensure_campaign_milestones(db, campaign=campaign)
    db.refresh(campaign, attribute_names=["milestones"])
    ordered_drafts = sorted(campaign.drafts, key=lambda draft: draft.created_at, reverse=True)
    workflow = get_brand_draft_workflow(campaign.project.brand)
    status_counts = Counter(_coerce_draft_status(draft.status) for draft in ordered_drafts)
    stage_type_counts = Counter(
        get_workflow_stage_or_raise(workflow, draft.status).stage_type for draft in ordered_drafts
    )
    next_planned_publish_at = min(
        (draft.planned_publish_at for draft in ordered_drafts if draft.planned_publish_at is not None),
        default=None,
    )
    recent_versions = db.scalars(
        select(DraftVersion)
        .join(ContentDraft, ContentDraft.id == DraftVersion.draft_id)
        .options(
            joinedload(DraftVersion.creator),
            joinedload(DraftVersion.draft).joinedload(ContentDraft.campaign).joinedload(Campaign.project).joinedload(Project.brand),
        )
        .where(ContentDraft.campaign_id == campaign.id)
        .order_by(DraftVersion.created_at.desc())
        .limit(12)
    ).all()
    brand_logs = db.scalars(
        select(AuditLog)
        .options(joinedload(AuditLog.actor))
        .where(AuditLog.brand_id == campaign.project.brand_id)
        .order_by(AuditLog.created_at.desc())
        .limit(80)
    ).all()
    activity_timeline = [_serialize_audit_log(log) for log in brand_logs if _belongs_to_campaign(log, campaign.id)][:20]

    return CampaignOverviewRead(
        campaign=_serialize_campaign(campaign),
        draft_workflow=workflow,
        brief=_serialize_brief_for_campaign(campaign),
        drafts=[_serialize_draft_for_campaign(draft) for draft in ordered_drafts],
        assets=[_serialize_asset(asset) for asset in campaign.assets],
        milestones=[serialize_campaign_milestone(milestone) for milestone in campaign.milestones],
        recent_versions=[_serialize_draft_version(version) for version in recent_versions],
        schedule=[_serialize_calendar_item(item) for item in campaign.calendar_items],
        status_breakdown=[
            DraftWorkflowStageCount(
                status=stage.key,
                status_label=stage.label,
                status_type=stage.stage_type,
                count=status_counts.get(stage.key, 0),
            )
            for stage in workflow.stages
        ],
        planning_summary=CampaignPlanningSummaryRead(
            total_drafts=len(ordered_drafts),
            idea_count=stage_type_counts.get(DraftStageType.BACKLOG, 0),
            draft_count=stage_type_counts.get(DraftStageType.IN_PROGRESS, 0),
            in_review_count=stage_type_counts.get(DraftStageType.REVIEW, 0),
            approved_count=stage_type_counts.get(DraftStageType.APPROVED, 0),
            scheduled_count=stage_type_counts.get(DraftStageType.SCHEDULED, 0),
            published_count=stage_type_counts.get(DraftStageType.PUBLISHED, 0),
            rejected_count=stage_type_counts.get(DraftStageType.CHANGES_REQUESTED, 0),
            next_planned_publish_at=next_planned_publish_at,
        ),
        activity_timeline=activity_timeline,
    )


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
    if payload.status == CampaignStatus.ACTIVE:
        assert_brand_limit_available(
            db,
            brand_id=project.brand_id,
            user_id=user.id,
            metric_key="active_campaigns",
            message="This brand has reached the active campaign limit for its current plan.",
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
    ensure_campaign_milestones(db, campaign=campaign)

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
    next_status = data.get("status", campaign.status)
    if next_status == CampaignStatus.ACTIVE and campaign.status != CampaignStatus.ACTIVE:
        assert_brand_limit_available(
            db,
            brand_id=campaign.project.brand_id,
            user_id=user.id,
            metric_key="active_campaigns",
            message="Moving this campaign to active would exceed the current plan limit.",
        )

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
