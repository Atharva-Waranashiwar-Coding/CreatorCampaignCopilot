from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import MembershipStatus
from app.core.permissions import WORKSPACE_MANAGEMENT_ROLES, require_role
from app.models.brand_membership import BrandMembership
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate
from app.services.audit import record_audit_log


def _serialize_project(project: Project) -> ProjectRead:
    return ProjectRead(
        id=project.id,
        brand_id=project.brand_id,
        brand_name=project.brand.name,
        name=project.name,
        description=project.description,
        status=project.status,
        created_by=project.created_by,
        created_at=project.created_at,
        updated_at=project.updated_at,
        campaign_count=len(project.campaigns),
    )


def _get_project_with_role(db: Session, *, project_id: int, user_id: int) -> tuple[Project, BrandMembership]:
    row = db.execute(
        select(Project, BrandMembership)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(selectinload(Project.brand), selectinload(Project.campaigns))
        .where(
            Project.id == project_id,
            BrandMembership.user_id == user_id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    ).first()
    if row is None:
        raise PermissionError("You do not have access to this project.")
    return row[0], row[1]


def list_projects(db: Session, *, user: User, brand_id: int | None = None) -> list[ProjectRead]:
    query = (
        select(Project)
        .join(BrandMembership, BrandMembership.brand_id == Project.brand_id)
        .options(selectinload(Project.brand), selectinload(Project.campaigns))
        .where(
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
        .order_by(Project.created_at.desc())
    )
    if brand_id is not None:
        query = query.where(Project.brand_id == brand_id)

    projects = db.scalars(query).all()
    return [_serialize_project(project) for project in projects]


def get_project(db: Session, *, project_id: int, user: User) -> ProjectRead:
    project, _ = _get_project_with_role(db, project_id=project_id, user_id=user.id)
    return _serialize_project(project)


def create_project(db: Session, *, payload: ProjectCreate, user: User) -> ProjectRead:
    membership = db.scalar(
        select(BrandMembership).where(
            BrandMembership.brand_id == payload.brand_id,
            BrandMembership.user_id == user.id,
            BrandMembership.status == MembershipStatus.ACTIVE,
        )
    )
    if membership is None:
        raise PermissionError("You do not have access to this brand.")
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to create projects.",
    )

    project = Project(
        brand_id=payload.brand_id,
        name=payload.name.strip(),
        description=payload.description,
        status=payload.status,
        created_by=user.id,
    )
    db.add(project)
    db.flush()

    record_audit_log(
        db,
        brand_id=payload.brand_id,
        actor_user_id=user.id,
        entity_type="project",
        entity_id=project.id,
        action="project.created",
        metadata={"name": project.name},
    )
    db.commit()
    db.refresh(project)
    return get_project(db, project_id=project.id, user=user)


def update_project(db: Session, *, project_id: int, payload: ProjectUpdate, user: User) -> ProjectRead:
    project, membership = _get_project_with_role(db, project_id=project_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to update projects.",
    )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(project, field, value.strip() if isinstance(value, str) else value)

    record_audit_log(
        db,
        brand_id=project.brand_id,
        actor_user_id=user.id,
        entity_type="project",
        entity_id=project.id,
        action="project.updated",
        metadata={"changes": {key: str(value) for key, value in data.items()}},
    )
    db.commit()
    db.refresh(project)
    return _serialize_project(project)


def delete_project(db: Session, *, project_id: int, user: User) -> None:
    project, membership = _get_project_with_role(db, project_id=project_id, user_id=user.id)
    require_role(
        membership.role,
        WORKSPACE_MANAGEMENT_ROLES,
        "You do not have permission to delete projects.",
    )
    db.delete(project)
    db.commit()
