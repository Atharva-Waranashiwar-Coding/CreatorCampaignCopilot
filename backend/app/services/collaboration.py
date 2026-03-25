from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.core.enums import CommentEntityType, MembershipStatus
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.collaboration_comment import CollaborationComment
from app.models.content_draft import ContentDraft
from app.models.draft_review import DraftReview
from app.models.mention import Mention
from app.models.project import Project
from app.models.user import User
from app.schemas.collaboration_comment import CollaborationCommentRead, MentionRead
from app.services.brands import get_membership_for_brand

MENTION_PATTERN = re.compile(r"(?<!\w)@([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})")


def extract_mention_identifiers(value: str | None) -> list[str]:
    identifiers: list[str] = []

    for match in MENTION_PATTERN.findall(value or ""):
        normalized = match.strip().lower()
        if normalized not in identifiers:
            identifiers.append(normalized)

    return identifiers


def resolve_mentioned_users(db: Session, *, brand_id: int, value: str | None) -> list[User]:
    identifiers = extract_mention_identifiers(value)
    if not identifiers:
        return []

    rows = db.scalars(
        select(User)
        .join(BrandMembership, BrandMembership.user_id == User.id)
        .where(
            BrandMembership.brand_id == brand_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
            User.email.in_(identifiers),
        )
        .order_by(User.full_name.asc())
    ).all()
    return rows


def serialize_mention(mention: Mention) -> MentionRead:
    return MentionRead(
        id=mention.id,
        mentioned_user_id=mention.mentioned_user_id,
        mentioned_user_name=mention.mentioned_user.full_name if mention.mentioned_user else "",
        mentioned_user_email=mention.mentioned_user.email if mention.mentioned_user else mention.identifier,
        identifier=mention.identifier,
        created_at=mention.created_at,
    )


def serialize_comment_tree(comments: list[CollaborationComment]) -> list[CollaborationCommentRead]:
    nodes = {
        comment.id: CollaborationCommentRead(
            id=comment.id,
            brand_id=comment.brand_id,
            entity_type=comment.entity_type,
            entity_id=comment.entity_id,
            campaign_id=comment.campaign_id,
            draft_id=comment.draft_id,
            parent_comment_id=comment.parent_comment_id,
            author_user_id=comment.author_user_id,
            author_name=comment.author.full_name if comment.author else None,
            body=comment.body,
            mentions=[serialize_mention(mention) for mention in comment.mentions],
            created_at=comment.created_at,
            updated_at=comment.updated_at,
            replies=[],
        )
        for comment in comments
    }

    roots: list[CollaborationCommentRead] = []
    for comment in comments:
        node = nodes[comment.id]
        if comment.parent_comment_id and comment.parent_comment_id in nodes:
            nodes[comment.parent_comment_id].replies.append(node)
        else:
            roots.append(node)

    return roots


def create_comment_mentions(
    db: Session,
    *,
    brand_id: int,
    author_user_id: int,
    comment: CollaborationComment,
) -> list[Mention]:
    users = resolve_mentioned_users(db, brand_id=brand_id, value=comment.body)
    mentions: list[Mention] = []
    for mentioned_user in users:
        if mentioned_user.id == author_user_id:
            continue
        mention = Mention(
            brand_id=brand_id,
            author_user_id=author_user_id,
            mentioned_user_id=mentioned_user.id,
            identifier=mentioned_user.email.lower(),
            comment_id=comment.id,
            draft_review_id=None,
        )
        db.add(mention)
        mentions.append(mention)
    db.flush()
    return mentions


def create_review_mentions(
    db: Session,
    *,
    brand_id: int,
    author_user_id: int,
    review: DraftReview,
) -> list[Mention]:
    users = resolve_mentioned_users(db, brand_id=brand_id, value=review.comment)
    mentions: list[Mention] = []
    for mentioned_user in users:
        if mentioned_user.id == author_user_id:
            continue
        mention = Mention(
            brand_id=brand_id,
            author_user_id=author_user_id,
            mentioned_user_id=mentioned_user.id,
            identifier=mentioned_user.email.lower(),
            comment_id=None,
            draft_review_id=review.id,
        )
        db.add(mention)
        mentions.append(mention)
    db.flush()
    return mentions


def get_campaign_collaboration_context(
    db: Session,
    *,
    campaign_id: int,
    user: User,
) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .where(
            Campaign.id == campaign_id,
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this campaign.")
    return row[0], row[1]


def get_draft_collaboration_context(
    db: Session,
    *,
    draft_id: int,
    user: User,
) -> tuple[ContentDraft, BrandMembership]:
    row = db.execute(
        select(ContentDraft, BrandMembership)
        .join(Campaign, Campaign.id == ContentDraft.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .where(
            ContentDraft.id == draft_id,
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this draft.")
    return row[0], row[1]


def assert_brand_membership(
    db: Session,
    *,
    brand_id: int,
    user: User,
) -> BrandMembership:
    return get_membership_for_brand(db, brand_id=brand_id, user_id=user.id)


def resolve_comment_target_context(
    db: Session,
    *,
    entity_type: CommentEntityType,
    entity_id: int,
    user: User,
) -> tuple[int, int | None, int | None]:
    if entity_type == CommentEntityType.CAMPAIGN:
        campaign, _ = get_campaign_collaboration_context(db, campaign_id=entity_id, user=user)
        return campaign.project.brand_id, campaign.id, None

    draft, _ = get_draft_collaboration_context(db, draft_id=entity_id, user=user)
    return draft.campaign.project.brand_id, draft.campaign_id, draft.id
