from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import CommentEntityType
from app.core.permissions import COLLABORATION_WRITE_ROLES, require_role
from app.models.collaboration_comment import CollaborationComment
from app.models.mention import Mention
from app.models.user import User
from app.schemas.collaboration_comment import CollaborationCommentCreate, CollaborationCommentRead
from app.services.audit import record_audit_log
from app.services.collaboration import (
    create_comment_mentions,
    get_campaign_collaboration_context,
    get_draft_collaboration_context,
    serialize_comment_tree,
)


def list_campaign_comments(db: Session, *, campaign_id: int, user: User) -> list[CollaborationCommentRead]:
    campaign, _ = get_campaign_collaboration_context(db, campaign_id=campaign_id, user=user)
    comments = db.scalars(
        select(CollaborationComment)
        .options(
            joinedload(CollaborationComment.author),
            selectinload(CollaborationComment.mentions).joinedload(Mention.mentioned_user),
        )
        .where(
            CollaborationComment.entity_type == CommentEntityType.CAMPAIGN,
            CollaborationComment.campaign_id == campaign.id,
        )
        .order_by(CollaborationComment.created_at.asc())
    ).all()
    return serialize_comment_tree(comments)


def create_campaign_comment(
    db: Session,
    *,
    campaign_id: int,
    payload: CollaborationCommentCreate,
    user: User,
) -> list[CollaborationCommentRead]:
    campaign, membership = get_campaign_collaboration_context(db, campaign_id=campaign_id, user=user)
    require_role(
        membership.role,
        COLLABORATION_WRITE_ROLES,
        "You do not have permission to comment on this campaign.",
    )
    _validate_parent_comment(
        db,
        entity_type=CommentEntityType.CAMPAIGN,
        entity_id=campaign.id,
        parent_comment_id=payload.parent_comment_id,
    )

    comment = CollaborationComment(
        brand_id=campaign.project.brand_id,
        entity_type=CommentEntityType.CAMPAIGN,
        entity_id=campaign.id,
        campaign_id=campaign.id,
        draft_id=None,
        parent_comment_id=payload.parent_comment_id,
        author_user_id=user.id,
        body=payload.body.strip(),
    )
    db.add(comment)
    db.flush()
    create_comment_mentions(db, brand_id=campaign.project.brand_id, author_user_id=user.id, comment=comment)
    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="collaboration_comment",
        entity_id=comment.id,
        action="campaign.comment_created",
        metadata={
            "campaign_id": campaign.id,
            "parent_comment_id": comment.parent_comment_id,
        },
    )
    db.commit()
    return list_campaign_comments(db, campaign_id=campaign.id, user=user)


def list_draft_comments(db: Session, *, draft_id: int, user: User) -> list[CollaborationCommentRead]:
    draft, _ = get_draft_collaboration_context(db, draft_id=draft_id, user=user)
    comments = db.scalars(
        select(CollaborationComment)
        .options(
            joinedload(CollaborationComment.author),
            selectinload(CollaborationComment.mentions).joinedload(Mention.mentioned_user),
        )
        .where(
            CollaborationComment.entity_type == CommentEntityType.DRAFT,
            CollaborationComment.draft_id == draft.id,
        )
        .order_by(CollaborationComment.created_at.asc())
    ).all()
    return serialize_comment_tree(comments)


def create_draft_comment(
    db: Session,
    *,
    draft_id: int,
    payload: CollaborationCommentCreate,
    user: User,
) -> list[CollaborationCommentRead]:
    draft, membership = get_draft_collaboration_context(db, draft_id=draft_id, user=user)
    require_role(
        membership.role,
        COLLABORATION_WRITE_ROLES,
        "You do not have permission to comment on this draft.",
    )
    _validate_parent_comment(
        db,
        entity_type=CommentEntityType.DRAFT,
        entity_id=draft.id,
        parent_comment_id=payload.parent_comment_id,
    )

    comment = CollaborationComment(
        brand_id=draft.campaign.project.brand_id,
        entity_type=CommentEntityType.DRAFT,
        entity_id=draft.id,
        campaign_id=draft.campaign_id,
        draft_id=draft.id,
        parent_comment_id=payload.parent_comment_id,
        author_user_id=user.id,
        body=payload.body.strip(),
    )
    db.add(comment)
    db.flush()
    create_comment_mentions(db, brand_id=draft.campaign.project.brand_id, author_user_id=user.id, comment=comment)
    record_audit_log(
        db,
        brand_id=draft.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="collaboration_comment",
        entity_id=comment.id,
        action="draft.comment_created",
        metadata={
            "campaign_id": draft.campaign_id,
            "draft_id": draft.id,
            "parent_comment_id": comment.parent_comment_id,
        },
    )
    db.commit()
    return list_draft_comments(db, draft_id=draft.id, user=user)


def _validate_parent_comment(
    db: Session,
    *,
    entity_type: CommentEntityType,
    entity_id: int,
    parent_comment_id: int | None,
) -> None:
    if parent_comment_id is None:
        return

    parent = db.scalar(select(CollaborationComment).where(CollaborationComment.id == parent_comment_id))
    if parent is None:
        raise LookupError("Parent comment not found.")
    if parent.entity_type != entity_type or parent.entity_id != entity_id:
        raise ValueError("Replies must stay inside the same collaboration thread.")
