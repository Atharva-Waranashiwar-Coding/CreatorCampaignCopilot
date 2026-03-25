from __future__ import annotations

import logging

from fastapi import Depends, FastAPI

from app.api.deps import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)

HELPER_TOOL_TAG = "helper-tools"


def mount_mcp_server(app: FastAPI) -> None:
    if not settings.mcp_helpers_enabled:
        return

    try:
        from fastapi_mcp import AuthConfig, FastApiMCP
    except ImportError:
        logger.warning("fastapi-mcp is not installed; MCP helper exposure is disabled.")
        return

    mcp = FastApiMCP(
        app,
        name=settings.mcp_server_name,
        description=settings.mcp_server_description,
        include_tags=[HELPER_TOOL_TAG],
        auth_config=AuthConfig(dependencies=[Depends(get_current_user)]),
    )

    if settings.mcp_enable_http_transport:
        mcp.mount_http(mount_path=settings.mcp_mount_path)

    if settings.mcp_enable_sse_transport:
        mcp.mount_sse(mount_path=f"{settings.mcp_mount_path}/sse")
