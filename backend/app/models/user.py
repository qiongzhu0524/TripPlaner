"""用户档案领域模型。"""

from datetime import datetime, timezone
from typing import Optional

from pydantic import BaseModel, Field


class UserProfile(BaseModel):
    """用于旅行偏好的持久化用户档案。"""

    user_id: str
    name: Optional[str] = None
    dietary_preferences: list[str] = Field(default_factory=list)
    budget_level: str = "midrange"
    travel_style: str = "balanced"
    interests: list[str] = Field(default_factory=list)
    past_destinations: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
