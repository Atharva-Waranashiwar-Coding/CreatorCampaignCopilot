from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.enums import MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.campaign import Campaign
from app.models.campaign_asset import CampaignAsset
from app.models.project import Project
from app.models.user import User
from app.schemas.campaign_asset import CampaignAssetCreate, CampaignAssetRead, CampaignAssetUpdate
from app.services.audit import record_audit_log


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


def _get_campaign_with_role(db: Session, *, campaign_id: int, user_id: int) -> tuple[Campaign, BrandMembership]:
    row = db.execute(
        select(Campaign, BrandMembership)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            selectinload(Campaign.project).selectinload(Project.brand),
            selectinload(Campaign.assets).joinedload(CampaignAsset.creator),
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


def _get_asset_with_role(db: Session, *, campaign_id: int, asset_id: int, user_id: int) -> tuple[CampaignAsset, BrandMembership]:
    row = db.execute(
        select(CampaignAsset, BrandMembership)
        .join(Campaign, Campaign.id == CampaignAsset.campaign_id)
        .join(Project, Project.id == Campaign.project_id)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(
            joinedload(CampaignAsset.creator),
            joinedload(CampaignAsset.campaign).joinedload(Campaign.project).joinedload(Project.brand),
        )
        .where(
            CampaignAsset.id == asset_id,
            CampaignAsset.campaign_id == campaign_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise LookupError("Asset not found.")
    return row[0], row[1]


def list_campaign_assets(db: Session, *, campaign_id: int, user: User) -> list[CampaignAssetRead]:
    campaign, _ = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    return [_serialize_asset(asset) for asset in campaign.assets]


def create_campaign_asset(
    db: Session,
    *,
    campaign_id: int,
    payload: CampaignAssetCreate,
    user: User,
) -> CampaignAssetRead:
    campaign, membership = _get_campaign_with_role(db, campaign_id=campaign_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign assets.",
    )

    asset = CampaignAsset(
        campaign_id=campaign.id,
        name=payload.name.strip(),
        asset_type=payload.asset_type.strip(),
        file_url=payload.file_url.strip(),
        thumbnail_url=payload.thumbnail_url.strip() if payload.thumbnail_url else None,
        mime_type=payload.mime_type.strip() if payload.mime_type else None,
        file_size_bytes=payload.file_size_bytes,
        notes=payload.notes.strip() if payload.notes else None,
        created_by=user.id,
    )
    db.add(asset)
    db.flush()

    record_audit_log(
        db,
        brand_id=campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="campaign_asset",
        entity_id=asset.id,
        action="asset.created",
        metadata={"campaign_id": campaign.id, "asset_type": asset.asset_type},
    )
    db.commit()
    db.refresh(asset)
    return _get_asset_read(db, campaign_id=campaign_id, asset_id=asset.id, user=user)


def _get_asset_read(db: Session, *, campaign_id: int, asset_id: int, user: User) -> CampaignAssetRead:
    asset, _ = _get_asset_with_role(db, campaign_id=campaign_id, asset_id=asset_id, user_id=user.id)
    return _serialize_asset(asset)


def update_campaign_asset(
    db: Session,
    *,
    campaign_id: int,
    asset_id: int,
    payload: CampaignAssetUpdate,
    user: User,
) -> CampaignAssetRead:
    asset, membership = _get_asset_with_role(db, campaign_id=campaign_id, asset_id=asset_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign assets.",
    )

    changes: dict[str, str | int | None] = {}
    for field, value in payload.model_dump(exclude_unset=True).items():
        normalized = value.strip() if isinstance(value, str) else value
        if getattr(asset, field) == normalized:
            continue
        setattr(asset, field, normalized)
        changes[field] = normalized

    if changes:
        record_audit_log(
            db,
            brand_id=asset.campaign.project.brand_id,
            actor_user_id=user.id,
            entity_type="campaign_asset",
            entity_id=asset.id,
            action="asset.updated",
            metadata={"campaign_id": asset.campaign_id, "changes": {key: str(value) for key, value in changes.items()}},
        )

    db.commit()
    db.refresh(asset)
    return _serialize_asset(asset)


def delete_campaign_asset(db: Session, *, campaign_id: int, asset_id: int, user: User) -> None:
    asset, membership = _get_asset_with_role(db, campaign_id=campaign_id, asset_id=asset_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to manage campaign assets.",
    )

    record_audit_log(
        db,
        brand_id=asset.campaign.project.brand_id,
        actor_user_id=user.id,
        entity_type="campaign_asset",
        entity_id=asset.id,
        action="asset.deleted",
        metadata={"campaign_id": asset.campaign_id, "asset_type": asset.asset_type},
    )
    db.delete(asset)
    db.commit()
