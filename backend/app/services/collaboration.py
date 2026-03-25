from __future__ import annotations

import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import CommentEntityType, MembershipStatus
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.content_draft import ContentDraft
from app.models.project import Project
from app.models.user import User
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
