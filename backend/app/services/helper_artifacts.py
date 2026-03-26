from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.draft_helper_artifact import DraftHelperArtifact
from app.models.project import Project
from app.models.tool_usage_log import ToolUsageLog
from app.models.user import User
from app.schemas.draft_helper_artifact import (
    DraftHelperArtifactCreate,
    DraftHelperArtifactRead,
    DraftHelperArtifactUpdate,
)
from app.services.access import assert_brand_limit_available
from app.services.audit import record_audit_log


def _serialize_artifact(artifact: DraftHelperArtifact) -> DraftHelperArtifactRead:
    return DraftHelperArtifactRead(
        id=artifact.id,
        draft_id=artifact.draft_id,
        tool_name=artifact.tool_name,
        artifact_type=artifact.artifact_type,
        title=artifact.title,
        summary=artifact.summary,
        payload=artifact.payload,
        status=artifact.status,
        source_tool_usage_log_id=artifact.source_tool_usage_log_id,
        source_tool_created_at=artifact.source_tool_usage_log.created_at if artifact.source_tool_usage_log else None,
        created_by=artifact.created_by,
        creator_name=artifact.creator.full_name if artifact.creator else None,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
    )


def _get_draft_with_membership(
    db: Session,
    *,
    draft_id: int,
    user_id: int,
) -> tuple[ContentDraft, BrandMembership]:
    row = db.execute(
        select(ContentDraft, BrandMembership)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            selectinload(ContentDraft.campaign).selectinload(Campaign.project).selectinload(Project.brand),
            selectinload(ContentDraft.helper_artifacts).joinedload(DraftHelperArtifact.creator),
            selectinload(ContentDraft.helper_artifacts).joinedload(DraftHelperArtifact.source_tool_usage_log),
        )
        .where(
            ContentDraft.id == draft_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this draft.")
    return row[0], row[1]


def _get_artifact_with_membership(
    db: Session,
    *,
    draft_id: int,
    artifact_id: int,
    user_id: int,
) -> tuple[DraftHelperArtifact, BrandMembership]:
    row = db.execute(
        select(DraftHelperArtifact, BrandMembership)
        .join(ContentDraft, ContentDraft.id == DraftHelperArtifact.draft_id)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            joinedload(DraftHelperArtifact.creator),
            joinedload(DraftHelperArtifact.source_tool_usage_log),
            joinedload(DraftHelperArtifact.draft).joinedload(ContentDraft.campaign).joinedload(Campaign.project),
        )
        .where(
            DraftHelperArtifact.id == artifact_id,
            DraftHelperArtifact.draft_id == draft_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this helper artifact.")
    return row[0], row[1]


def list_draft_helper_artifacts(db: Session, *, draft_id: int, user: User) -> list[DraftHelperArtifactRead]:
    draft, _ = _get_draft_with_membership(db, draft_id=draft_id, user_id=user.id)
    return [_serialize_artifact(artifact) for artifact in draft.helper_artifacts]


def create_draft_helper_artifact(
    db: Session,
    *,
    draft_id: int,
    payload: DraftHelperArtifactCreate,
    user: User,
) -> DraftHelperArtifactRead:
    draft, _membership = _get_draft_with_membership(db, draft_id=draft_id, user_id=user.id)
    brand_id = draft.campaign.project.brand_id
    assert_brand_limit_available(
        db,
        brand_id=brand_id,
        user_id=user.id,
        metric_key="saved_helper_artifacts",
        message="This brand has reached the saved helper artifact limit for its current plan.",
    )

    if payload.source_tool_usage_log_id is not None:
        source_log = db.get(ToolUsageLog, payload.source_tool_usage_log_id)
        if source_log is None:
            raise LookupError("Source tool usage log was not found.")
        if source_log.draft_id not in {None, draft_id}:
            raise ValueError("Source tool usage log does not belong to this draft.")

    artifact = DraftHelperArtifact(
        draft_id=draft_id,
        tool_name=payload.tool_name.strip(),
        artifact_type=payload.artifact_type,
        title=payload.title.strip(),
        summary=payload.summary.strip() if payload.summary else None,
        payload=payload.payload,
        status=payload.status,
        source_tool_usage_log_id=payload.source_tool_usage_log_id,
        created_by=user.id,
    )
    db.add(artifact)
    db.flush()

    record_audit_log(
        db,
        brand_id=brand_id,
        actor_user_id=user.id,
        entity_type="draft_helper_artifact",
        entity_id=artifact.id,
        action="helper_artifact.created",
        metadata={
            "draft_id": draft_id,
            "tool_name": artifact.tool_name,
            "artifact_type": artifact.artifact_type,
            "status": artifact.status,
        },
    )

    db.commit()
    db.refresh(artifact)
    return _serialize_artifact(artifact)


def update_draft_helper_artifact(
    db: Session,
    *,
    draft_id: int,
    artifact_id: int,
    payload: DraftHelperArtifactUpdate,
    user: User,
) -> DraftHelperArtifactRead:
    artifact, membership = _get_artifact_with_membership(
        db,
        draft_id=draft_id,
        artifact_id=artifact_id,
        user_id=user.id,
    )
    if artifact.created_by != user.id:
        require_role(
            membership.role,
            WORKSPACE_MANAGEMENT_ROLES,
            "Only the artifact creator or workspace managers can update helper artifacts.",
        )

    changes: dict[str, object] = {}
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        next_value = value.strip() if isinstance(value, str) else value
        if getattr(artifact, field) == next_value:
            continue
        setattr(artifact, field, next_value)
        changes[field] = next_value

    if changes:
        record_audit_log(
            db,
            brand_id=artifact.draft.campaign.project.brand_id,
            actor_user_id=user.id,
            entity_type="draft_helper_artifact",
            entity_id=artifact.id,
            action="helper_artifact.updated",
            metadata={"draft_id": draft_id, "changes": changes},
        )

    db.commit()
    db.refresh(artifact)
    return _serialize_artifact(artifact)


def delete_draft_helper_artifact(
    db: Session,
    *,
    draft_id: int,
    artifact_id: int,
    user: User,
) -> None:
    artifact, membership = _get_artifact_with_membership(
        db,
        draft_id=draft_id,
        artifact_id=artifact_id,
        user_id=user.id,
    )
    if artifact.created_by != user.id:
        require_role(
            membership.role,
            WORKSPACE_MANAGEMENT_ROLES,
            "Only the artifact creator or workspace managers can delete helper artifacts.",
        )

    record_audit_log(
        db,
        brand_id=artifact.draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="draft_helper_artifact",
        entity_id=artifact.id,
        action="helper_artifact.deleted",
        metadata={"draft_id": draft_id, "tool_name": artifact.tool_name},
    )
    db.delete(artifact)
    db.commit()
