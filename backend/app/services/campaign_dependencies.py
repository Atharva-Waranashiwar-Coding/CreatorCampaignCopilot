from __future__ import annotations

from collections import defaultdict

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import CampaignDependencyNodeType, DraftStageType, MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.campaign_dependency import CampaignDependency
from app.models.campaign_milestone import CampaignMilestone
from app.models.content_draft import ContentDraft
from app.models.project import Project
from app.models.user import User
from app.schemas.campaign_dependency import CampaignDependencyCreate, CampaignDependencyRead
from app.services.audit import record_audit_log
from app.services.draft_workflows import get_brand_draft_workflow, get_workflow_stage_or_raise

_STAGE_PROGRESS = {
    DraftStageType.BACKLOG: 10,
    DraftStageType.IN_PROGRESS: 20,
    DraftStageType.CHANGES_REQUESTED: 25,
    DraftStageType.REVIEW: 30,
    DraftStageType.APPROVED: 40,
    DraftStageType.SCHEDULED: 50,
    DraftStageType.PUBLISHED: 60,
}


def list_campaign_dependencies(db: Session, *, campaign_id: int, user: User) -> list[CampaignDependencyRead]:
    campaign, _ = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    workflow = get_brand_draft_workflow(campaign.project.brand)
    return [serialize_campaign_dependency(dependency, workflow=workflow) for dependency in campaign.dependencies]


def create_campaign_dependency(
    db: Session,
    *,
    campaign_id: int,
    payload: CampaignDependencyCreate,
    user: User,
) -> list[CampaignDependencyRead]:
    campaign, membership = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign dependencies.",
    )
    workflow = get_brand_draft_workflow(campaign.project.brand)

    dependent_node = _resolve_node(
        campaign=campaign,
        workflow=workflow,
        node_type=payload.dependent_type,
        milestone_id=payload.dependent_milestone_id,
        draft_id=payload.dependent_draft_id,
        stage_key=payload.dependent_stage_key,
        node_role="dependent",
    )
    blocker_node = _resolve_node(
        campaign=campaign,
        workflow=workflow,
        node_type=payload.blocker_type,
        milestone_id=payload.blocker_milestone_id,
        draft_id=payload.blocker_draft_id,
        stage_key=payload.blocker_stage_key,
        node_role="blocker",
    )

    if dependent_node["node_key"] == blocker_node["node_key"]:
        raise ValueError("A dependency cannot point to the same campaign step on both sides.")

    for dependency in campaign.dependencies:
        if (
            dependency.dependent_type == payload.dependent_type
            and dependency.dependent_milestone_id == dependent_node["milestone_id"]
            and dependency.dependent_draft_id == dependent_node["draft_id"]
            and dependency.dependent_stage_key == dependent_node["stage_key"]
            and dependency.blocker_type == payload.blocker_type
            and dependency.blocker_milestone_id == blocker_node["milestone_id"]
            and dependency.blocker_draft_id == blocker_node["draft_id"]
            and dependency.blocker_stage_key == blocker_node["stage_key"]
        ):
            raise ValueError("That dependency already exists for this campaign.")

    _assert_no_dependency_cycle(
        campaign=campaign,
        blocker_node_key=blocker_node["node_key"],
        dependent_node_key=dependent_node["node_key"],
    )

    dependency = CampaignDependency(
        campaign_id=campaign.id,
        dependent_type=payload.dependent_type,
        dependent_milestone_id=dependent_node["milestone_id"],
        dependent_draft_id=dependent_node["draft_id"],
        dependent_stage_key=dependent_node["stage_key"],
        blocker_type=payload.blocker_type,
        blocker_milestone_id=blocker_node["milestone_id"],
        blocker_draft_id=blocker_node["draft_id"],
        blocker_stage_key=blocker_node["stage_key"],
        note=payload.note.strip() if isinstance(payload.note, str) and payload.note.strip() else None,
        created_by=user.id,
    )
    db.add(dependency)
    db.flush()

    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="campaign_dependency",
        entity_id=dependency.id,
        action="campaign.dependency_created",
        metadata={
            "campaign_id": campaign.id,
            "dependent": dependent_node["node_key"],
            "blocker": blocker_node["node_key"],
        },
    )
    db.commit()
    db.refresh(campaign)
    return [serialize_campaign_dependency(item, workflow=workflow) for item in campaign.dependencies]


def delete_campaign_dependency(
    db: Session,
    *,
    campaign_id: int,
    dependency_id: int,
    user: User,
) -> list[CampaignDependencyRead]:
    dependency, membership = _get_dependency_with_role(
        db,
        campaign_id=campaign_id,
        dependency_id=dependency_id,
        user_id=user.id,
    )
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign dependencies.",
    )
    workflow = get_brand_draft_workflow(dependency.campaign.project.brand)

    record_audit_log(
        db,
        brand_id=dependency.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="campaign_dependency",
        entity_id=dependency.id,
        action="campaign.dependency_deleted",
        metadata={"campaign_id": dependency.campaign_id},
    )
    db.delete(dependency)
    db.commit()

    campaign = db.scalar(
        select(Campaign)
        .options(
            joinedload(Campaign.project).joinedload(Project.brand),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.creator),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.dependent_milestone),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.blocker_milestone),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.dependent_draft),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.blocker_draft),
        )
        .where(Campaign.id == campaign_id)
    )
    return [serialize_campaign_dependency(item, workflow=workflow) for item in campaign.dependencies] if campaign else []


def assert_draft_stage_dependencies_satisfied(
    db: Session,
    *,
    draft: ContentDraft,
    target_stage_key: str,
) -> None:
    dependencies = _load_dependencies_for_campaign(db, campaign_id=draft.campaign_id)
    workflow = get_brand_draft_workflow(draft.campaign.project.brand)
    blockers = [
        serialize_campaign_dependency(dependency, workflow=workflow)
        for dependency in dependencies
        if dependency.dependent_type == CampaignDependencyNodeType.DRAFT_STAGE
        and dependency.dependent_draft_id == draft.id
        and dependency.dependent_stage_key == target_stage_key
        and not _is_dependency_satisfied(dependency, workflow=workflow)
    ]
    if blockers:
        reasons = "; ".join(blocker.blocker_label for blocker in blockers)
        raise ValueError(f"This draft is blocked from entering that stage until these steps are complete: {reasons}.")


def assert_milestone_dependencies_satisfied(db: Session, *, milestone: CampaignMilestone) -> None:
    dependencies = _load_dependencies_for_campaign(db, campaign_id=milestone.campaign_id)
    workflow = get_brand_draft_workflow(milestone.campaign.project.brand)
    blockers = [
        serialize_campaign_dependency(dependency, workflow=workflow)
        for dependency in dependencies
        if dependency.dependent_type == CampaignDependencyNodeType.CAMPAIGN_MILESTONE
        and dependency.dependent_milestone_id == milestone.id
        and not _is_dependency_satisfied(dependency, workflow=workflow)
    ]
    if blockers:
        reasons = "; ".join(blocker.blocker_label for blocker in blockers)
        raise ValueError(f"This milestone is blocked until these steps are complete: {reasons}.")


def serialize_campaign_dependency(
    dependency: CampaignDependency,
    *,
    workflow,
) -> CampaignDependencyRead:
    return CampaignDependencyRead(
        id=dependency.id,
        campaign_id=dependency.campaign_id,
        dependent_type=dependency.dependent_type,
        dependent_milestone_id=dependency.dependent_milestone_id,
        dependent_draft_id=dependency.dependent_draft_id,
        dependent_stage_key=dependency.dependent_stage_key,
        dependent_label=_node_label(
            workflow=workflow,
            node_type=dependency.dependent_type,
            milestone=dependency.dependent_milestone,
            draft=dependency.dependent_draft,
            stage_key=dependency.dependent_stage_key,
        ),
        blocker_type=dependency.blocker_type,
        blocker_milestone_id=dependency.blocker_milestone_id,
        blocker_draft_id=dependency.blocker_draft_id,
        blocker_stage_key=dependency.blocker_stage_key,
        blocker_label=_node_label(
            workflow=workflow,
            node_type=dependency.blocker_type,
            milestone=dependency.blocker_milestone,
            draft=dependency.blocker_draft,
            stage_key=dependency.blocker_stage_key,
        ),
        note=dependency.note,
        created_by=dependency.created_by,
        creator_name=dependency.creator.full_name if dependency.creator else None,
        is_satisfied=_is_dependency_satisfied(dependency, workflow=workflow),
        created_at=dependency.created_at,
        updated_at=dependency.updated_at,
    )


def _resolve_node(
    *,
    campaign: Campaign,
    workflow,
    node_type: CampaignDependencyNodeType,
    milestone_id: int | None,
    draft_id: int | None,
    stage_key: str | None,
    node_role: str,
) -> dict[str, object | None]:
    if node_type == CampaignDependencyNodeType.CAMPAIGN_MILESTONE:
        milestone = next((item for item in campaign.milestones if item.id == milestone_id), None)
        if milestone is None:
            raise ValueError(f"The {node_role} milestone must belong to this campaign.")
        return {
            "milestone_id": milestone.id,
            "draft_id": None,
            "stage_key": None,
            "node_key": f"milestone:{milestone.id}",
        }

    draft = next((item for item in campaign.drafts if item.id == draft_id), None)
    if draft is None:
        raise ValueError(f"The {node_role} draft must belong to this campaign.")
    if not stage_key:
        raise ValueError(f"The {node_role} draft-stage dependency requires a stage key.")
    stage = get_workflow_stage_or_raise(workflow, stage_key, message_prefix=f"{node_role.capitalize()} stage")
    return {
        "milestone_id": None,
        "draft_id": draft.id,
        "stage_key": stage.key,
        "node_key": f"draft:{draft.id}:stage:{stage.key}",
    }


def _assert_no_dependency_cycle(*, campaign: Campaign, blocker_node_key: str, dependent_node_key: str) -> None:
    graph: dict[str, set[str]] = defaultdict(set)
    for dependency in campaign.dependencies:
        existing_blocker = _node_key(
            node_type=dependency.blocker_type,
            milestone_id=dependency.blocker_milestone_id,
            draft_id=dependency.blocker_draft_id,
            stage_key=dependency.blocker_stage_key,
        )
        existing_dependent = _node_key(
            node_type=dependency.dependent_type,
            milestone_id=dependency.dependent_milestone_id,
            draft_id=dependency.dependent_draft_id,
            stage_key=dependency.dependent_stage_key,
        )
        graph[existing_blocker].add(existing_dependent)

    stack = [dependent_node_key]
    visited: set[str] = set()
    while stack:
        current = stack.pop()
        if current == blocker_node_key:
            raise ValueError("This dependency would create a circular block in the campaign workflow.")
        if current in visited:
            continue
        visited.add(current)
        stack.extend(graph.get(current, set()))


def _is_dependency_satisfied(dependency: CampaignDependency, *, workflow) -> bool:
    if dependency.blocker_type == CampaignDependencyNodeType.CAMPAIGN_MILESTONE:
        return dependency.blocker_milestone is not None and dependency.blocker_milestone.completed_at is not None

    if dependency.blocker_draft is None or dependency.blocker_stage_key is None:
        return False

    current_stage = get_workflow_stage_or_raise(workflow, dependency.blocker_draft.status)
    required_stage = get_workflow_stage_or_raise(workflow, dependency.blocker_stage_key)
    if current_stage.key == required_stage.key:
        return True

    current_progress = _STAGE_PROGRESS[current_stage.stage_type]
    required_progress = _STAGE_PROGRESS[required_stage.stage_type]
    if current_progress != required_progress:
        return current_progress > required_progress

    stage_order = {stage.key: index for index, stage in enumerate(workflow.stages)}
    return stage_order[current_stage.key] > stage_order[required_stage.key]


def _node_key(
    *,
    node_type: CampaignDependencyNodeType,
    milestone_id: int | None,
    draft_id: int | None,
    stage_key: str | None,
) -> str:
    if node_type == CampaignDependencyNodeType.CAMPAIGN_MILESTONE:
        return f"milestone:{milestone_id}"
    return f"draft:{draft_id}:stage:{stage_key}"


def _node_label(
    *,
    workflow,
    node_type: CampaignDependencyNodeType,
    milestone: CampaignMilestone | None,
    draft: ContentDraft | None,
    stage_key: str | None,
) -> str:
    if node_type == CampaignDependencyNodeType.CAMPAIGN_MILESTONE:
        return milestone.label if milestone else "Campaign milestone"
    if draft is None or stage_key is None:
        return "Draft stage"
    stage = get_workflow_stage_or_raise(workflow, stage_key)
    return f"{draft.title} -> {stage.label}"


def _load_dependencies_for_campaign(db: Session, *, campaign_id: int) -> list[CampaignDependency]:
    return db.scalars(
        select(CampaignDependency)
        .options(
            joinedload(CampaignDependency.campaign).joinedload(Campaign.project).joinedload(Project.brand),
            joinedload(CampaignDependency.creator),
            joinedload(CampaignDependency.dependent_milestone),
            joinedload(CampaignDependency.blocker_milestone),
            joinedload(CampaignDependency.dependent_draft),
            joinedload(CampaignDependency.blocker_draft),
        )
        .where(CampaignDependency.campaign_id == campaign_id)
        .order_by(CampaignDependency.created_at.asc())
    ).all()


def _get_campaign_with_role(db: Session, *, campaign_id: int, user_id: int) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            selectinload(Campaign.project).selectinload(Project.brand),
            selectinload(Campaign.milestones),
            selectinload(Campaign.drafts),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.creator),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.dependent_milestone),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.blocker_milestone),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.dependent_draft),
            selectinload(Campaign.dependencies).joinedload(CampaignDependency.blocker_draft),
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


def _get_dependency_with_role(
    db: Session,
    *,
    campaign_id: int,
    dependency_id: int,
    user_id: int,
) -> tuple[CampaignDependency, BrandMembership]:
    row = db.execute(
        select(CampaignDependency, BrandMembership)
        .join(Campaign, Campaign.id == CampaignDependency.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            joinedload(CampaignDependency.campaign).joinedload(Campaign.project).joinedload(Project.brand),
            joinedload(CampaignDependency.creator),
            joinedload(CampaignDependency.dependent_milestone),
            joinedload(CampaignDependency.blocker_milestone),
            joinedload(CampaignDependency.dependent_draft),
            joinedload(CampaignDependency.blocker_draft),
        )
        .where(
            CampaignDependency.id == dependency_id,
            CampaignDependency.campaign_id == campaign_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise LookupError("Campaign dependency not found.")
    return row[0], row[1]
