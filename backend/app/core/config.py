from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(case_sensitive=False, env_file=".env", extra="ignore")

    project_name: str = "Creator Campaign Copilot API"
    api_prefix: str = "/api"
    mcp_server_name: str = "Creator Campaign Copilot Helper Tools"
    mcp_server_description: str = "Authenticated MCP exposure for internal campaign helper tools."
    mcp_mount_path: str = "/mcp"
    mcp_enable_http_transport: bool = True
    mcp_enable_sse_transport: bool = False
    mcp_helpers_enabled: bool = True
    database_url: str = "postgresql+psycopg://postgres:postgres@db:5432/creator_campaign_copilot"
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 120
    frontend_origin: str = "http://localhost:5173"


settings = Settings()
