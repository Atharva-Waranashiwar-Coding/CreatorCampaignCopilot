from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.content_template import ContentTemplate
from app.models.user import User
from app.schemas.content_template import ContentTemplateCreate, ContentTemplateRead, ContentTemplateUpdate
from app.services.access import assert_brand_feature_access, assert_brand_limit_available
from app.services.audit import record_audit_log


def _serialize_template(template: ContentTemplate) -> ContentTemplateRead:
    return ContentTemplateRead(
        id=template.id,
        brand_id=template.brand_id,
        brand_name=template.brand.name,
        name=template.name,
        description=template.description,
        template_type=template.template_type,
        platform=template.platform,
        content_type=template.content_type,
        body=template.body,
        created_by=template.created_by,
        creator_name=template.creator.full_name if template.creator else None,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def _get_template_with_role(
    db: Session,
    *,
    template_id: int,
    user_id: int,
) -> tuple[ContentTemplate, BrandMembership]:
    row = db.execute(
        select(ContentTemplate, BrandMembership)
        .join(BrandMembership, BrandMembership.brand_id == ContentTemplate.brand_id)
        .options(
            selectinload(ContentTemplate.brand),
            joinedload(ContentTemplate.creator),
        )
        .where(
            ContentTemplate.id == template_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this template.")
    return row[0], row[1]


def list_templates(
    db: Session,
    *,
    user: User,
    brand_id: int | None = None,
    template_type: str | None = None,
    search: str | None = None,
) -> list[ContentTemplateRead]:
    query = (
        select(ContentTemplate)
        .join(BrandMembership, BrandMembership.brand_id == ContentTemplate.brand_id)
        .options(selectinload(ContentTemplate.brand), joinedload(ContentTemplate.creator))
        .where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
        .order_by(ContentTemplate.updated_at.desc())
    )
    if brand_id is not None:
        query = query.where(ContentTemplate.brand_id == brand_id)
    if template_type:
        query = query.where(ContentTemplate.template_type.ilike(template_type.strip()))
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(
                ContentTemplate.name.ilike(term),
                ContentTemplate.description.ilike(term),
                ContentTemplate.body.ilike(term),
            )
        )

    templates = db.scalars(query).all()
    return [_serialize_template(template) for template in templates]


def get_template(db: Session, *, template_id: int, user: User) -> ContentTemplateRead:
    template, _ = _get_template_with_role(db, template_id=template_id, user_id=user.id)
    return _serialize_template(template)


def create_template(db: Session, *, payload: ContentTemplateCreate, user: User) -> ContentTemplateRead:
    context = assert_brand_feature_access(
        db,
        brand_id=payload.brand_id,
        user_id=user.id,
        feature_key="template_library",
        message="Templates are not available on this brand plan.",
    )
    require_role(
        context.membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to create templates.",
    )
    assert_brand_limit_available(
        db,
        brand_id=payload.brand_id,
        user_id=user.id,
        metric_key="templates",
        message="This brand has reached the template limit for its current plan.",
    )

    template = ContentTemplate(
        brand_id=payload.brand_id,
        name=payload.name.strip(),
        description=payload.description,
        template_type=payload.template_type.strip(),
        platform=payload.platform.strip() if payload.platform else None,
        content_type=payload.content_type.strip() if payload.content_type else None,
        body=payload.body.strip(),
        created_by=user.id,
    )
    db.add(template)
    db.flush()

    record_audit_log(
        db,
        brand_id=payload.brand_id,
        actor_user_id=user.id,
        entity_type="content_template",
        entity_id=template.id,
        action="template.created",
        metadata={
            "name": template.name,
            "template_type": template.template_type,
            "platform": template.platform,
        },
    )

    db.commit()
    db.refresh(template)
    return get_template(db, template_id=template.id, user=user)


def update_template(db: Session, *, template_id: int, payload: ContentTemplateUpdate, user: User) -> ContentTemplateRead:
    template, membership = _get_template_with_role(db, template_id=template_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to update templates.",
    )

    changes: dict[str, str | None] = {}
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        normalized = value.strip() if isinstance(value, str) else value
        if getattr(template, field) == normalized:
            continue
        setattr(template, field, normalized)
        changes[field] = normalized if normalized is None or isinstance(normalized, str) else str(normalized)

    if changes:
        record_audit_log(
            db,
            brand_id=template.brand_id,
            actor_user_id=user.id,
            entity_type="content_template",
            entity_id=template.id,
            action="template.updated",
            metadata={"changes": changes},
        )

    db.commit()
    db.refresh(template)
    return _serialize_template(template)


def delete_template(db: Session, *, template_id: int, user: User) -> None:
    template, membership = _get_template_with_role(db, template_id=template_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to delete templates.",
    )

    record_audit_log(
        db,
        brand_id=template.brand_id,
        actor_user_id=user.id,
        entity_type="content_template",
        entity_id=template.id,
        action="template.deleted",
        metadata={"name": template.name, "template_type": template.template_type},
    )
    db.delete(template)
    db.commit()
