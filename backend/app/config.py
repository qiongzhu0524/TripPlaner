"""应用程序配置，使用 pydantic-settings。

环境变量使用 __ 作为嵌套分隔符：
    LLM_OPENAI__API_KEY=sk-...
    AMAP__API_KEY=your_key
    DATABASE__DSN=postgresql+asyncpg://...
"""

import os
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMProviderConfig(BaseSettings):
    """单个 LLM 提供者的配置。"""

    api_key: str = ""
    base_url: str = ""
    model: str = "gpt-4o"
    max_tokens: int = 4096
    temperature: float = 0.7


class AmapConfig(BaseSettings):
    """高德地图 API 配置。"""

    api_key: str = ""


class DatabaseConfig(BaseSettings):
    """PostgreSQL 数据库配置。"""

    dsn: str = "postgresql+asyncpg://tripuser:tripsecret@localhost:5432/tripplaner"
    pool_size: int = 10
    max_overflow: int = 20


class MemoryConfig(BaseSettings):
    """记忆系统配置。"""

    model_config = SettingsConfigDict(extra="ignore")

    short_term_max_tokens: int = 4000
    long_term_enabled: bool = True


class Settings(BaseSettings):
    """根设置，从 .env 文件和环境变量加载。"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # 通用设置
    debug: bool = False
    log_level: str = "INFO"

    # LLM 提供者
    llm_openai: LLMProviderConfig = Field(default_factory=LLMProviderConfig)
    llm_anthropic: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(model="claude-sonnet-4-20250514")
    )
    llm_deepseek: LLMProviderConfig = Field(
        default_factory=lambda: LLMProviderConfig(
            base_url="https://api.deepseek.com",
            model="deepseek-chat",
        )
    )
    default_llm_provider: Literal["openai", "anthropic", "deepseek"] = "openai"

    # API 配置
    amap: AmapConfig = Field(default_factory=AmapConfig)

    # 数据库
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)

    # 记忆系统
    memory: MemoryConfig = Field(default_factory=MemoryConfig)

    # MCP 服务器（服务器配置列表，可通过环境变量或代码扩展）
    mcp_servers: list[dict] = [
        {
            "name": "amap",
            "command": ["uvx", "amap-mcp-server"],
            "env": {"AMAP_MAPS_API_KEY": "${amap.api_key}"},
        },
    ]


# 单例实例
settings = Settings()
