from __future__ import annotations

import logging

from fastapi import Depends, FastAPI

from app.api.deps import get_current_user
from app.core.config import settings

logger = logging.getLogger(__name__)

HELPER_TOOL_TAG = "helper-tools"


def _build_helper_tool_app() -> FastAPI:
    from app.tools.api import router as helper_tools_router

    helper_tool_app = FastAPI(
        title=settings.mcp_server_name,
        description=settings.mcp_server_description,
    )
    helper_tool_app.include_router(
        helper_tools_router,
        prefix=f"{settings.api_prefix}/tools/helpers",
        tags=[HELPER_TOOL_TAG],
    )
    return helper_tool_app


def mount_mcp_server(app: FastAPI) -> None:
    if not settings.mcp_helpers_enabled:
        return

    try:
        from fastapi_mcp import AuthConfig, FastApiMCP
    except ImportError:
        logger.warning("fastapi-mcp is not installed; MCP helper exposure is disabled.")
        return

    helper_tool_app = _build_helper_tool_app()

    try:
        mcp = FastApiMCP(
            helper_tool_app,
            name=settings.mcp_server_name,
            description=settings.mcp_server_description,
            include_tags=[HELPER_TOOL_TAG],
            auth_config=AuthConfig(dependencies=[Depends(get_current_user)]),
        )
    except RecursionError:
        logger.warning(
            "fastapi-mcp could not initialize from the helper-tool schema; helper MCP exposure is disabled, but REST helper routes remain available."
        )
        return

    if settings.mcp_enable_http_transport:
        mcp.mount_http(router=app, mount_path=settings.mcp_mount_path)

    if settings.mcp_enable_sse_transport:
        mcp.mount_sse(router=app, mount_path=f"{settings.mcp_mount_path}/sse")
