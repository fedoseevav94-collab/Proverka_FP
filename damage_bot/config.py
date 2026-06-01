from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = Field(alias="BOT_TOKEN")
    fp_chat_id: int = Field(default=1001905865504, alias="FP_CHAT_ID")
    pv_chat_id: int = Field(default=1001941984098, alias="PV_CHAT_ID")
    supervisor_username: str = Field(default="fedos_av", alias="SUPERVISOR_USERNAME")
    database_url: str = Field(default="sqlite+aiosqlite:///bot.db", alias="DATABASE_URL")
    cars_excel_path: str = Field(default="Парковые авто.xlsx", alias="CARS_EXCEL_PATH")
    reminder_first_delay_minutes: int = Field(default=10, alias="REMINDER_FIRST_DELAY_MINUTES")
    reminder_interval_minutes: int = Field(default=30, alias="REMINDER_INTERVAL_MINUTES")
    max_reminders: int = Field(default=3, alias="MAX_REMINDERS")
    admin_user_ids: str = Field(default="", alias="ADMIN_USER_IDS")
    admin_chat_id: int | None = Field(default=None, alias="ADMIN_CHAT_ID")
    fp_ignored_usernames: str = Field(default="Norblacksmith", alias="FP_IGNORED_USERNAMES")

    @property
    def admins(self) -> set[int]:
        return {int(item.strip()) for item in self.admin_user_ids.split(",") if item.strip()}

    @property
    def ignored_fp_usernames(self) -> set[str]:
        return {item.strip().lstrip("@").lower() for item in self.fp_ignored_usernames.split(",") if item.strip()}
