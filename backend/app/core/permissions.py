from collections.abc import Iterable

from app.core.enums import BrandRole

BRAND_MANAGEMENT_ROLES = {BrandRole.OWNER, BrandRole.ADMIN}
BRAND_OWNER_ONLY_ROLES = {BrandRole.OWNER}
WORKSPACE_MANAGEMENT_ROLES = {BrandRole.OWNER, BrandRole.ADMIN, BrandRole.EDITOR}
REVIEW_WORKFLOW_ROLES = {BrandRole.OWNER, BrandRole.ADMIN, BrandRole.REVIEWER}


def require_role(role: BrandRole, allowed_roles: Iterable[BrandRole], message: str) -> None:
    if role not in set(allowed_roles):
        raise PermissionError(message)
