"""用户档案领域模型。"""

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileData(BaseModel):
    """经用户确认后可作为权威信息保存的结构化档案。"""

    model_config = ConfigDict(extra="forbid")

    education: str | None = Field(default=None, max_length=100)
    major: str | None = Field(default=None, max_length=255)
    political_status: str | None = Field(default=None, max_length=100)
    fresh_graduate: bool | None = None
    work_experience_years: int | None = Field(default=None, ge=0, le=60)
    gender: str | None = Field(default=None, max_length=20)
    age: int | None = Field(default=None, ge=16, le=100)
    household_registration: str | None = Field(default=None, max_length=255)
    target_exam_type: str | None = Field(default=None, max_length=20)
    target_province: str | None = Field(default=None, max_length=50)
    target_city: str | None = Field(default=None, max_length=100)

    @field_validator("*", mode="before")
    @classmethod
    def normalize_blank_strings(cls, value: object) -> object:
        """去除字符串首尾空白，并把空字符串统一表示为未知。"""
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        return normalized or None

    @property
    def missing_fields(self) -> list[str]:
        """按 schema 声明顺序返回尚未提供的字段。"""
        return [name for name in type(self).model_fields if getattr(self, name) is None]
