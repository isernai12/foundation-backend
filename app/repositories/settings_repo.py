from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.settings import Settings
from backend.app.repositories.base import BaseRepository


class SettingsRepository(BaseRepository[Settings]):
    def __init__(self):
        super().__init__(Settings)

    def get_setting(self, db: Session, key: str, default: Optional[str] = None) -> Optional[str]:
        stmt = select(Settings.value).where(Settings.key == key)
        val = db.scalar(stmt)
        return val if val is not None else default

    def get_monthly_membership_fee(self, db: Session) -> int:
        """
        Dynamically retrieves the configured monthly membership fee from settings.
        Checks keys 'DEFAULT_MONTHLY_CONTRIBUTION' and 'membership.monthlyFee'.
        Defaults to 100 if unset. Never hardcoded in business calculation.
        """
        stmt = select(Settings).where(
            Settings.key.in_(["DEFAULT_MONTHLY_CONTRIBUTION", "membership.monthlyFee"])
        )
        settings = db.scalars(stmt).all()
        val = None
        for s in settings:
            if s.key == "DEFAULT_MONTHLY_CONTRIBUTION" and s.value:
                val = s.value
                break
            if s.key == "membership.monthlyFee" and s.value:
                val = s.value

        if not val:
            return 100
        try:
            fee = int(val.strip())
            return fee if fee > 0 else 100
        except ValueError:
            return 100

    def set_setting(
        self,
        db: Session,
        key: str,
        value: str,
        description: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> Settings:
        stmt = select(Settings).where(Settings.key == key)
        setting = db.scalars(stmt).first()
        if setting:
            setting.value = str(value).strip()
            if description:
                setting.description = description
            setting.updatedBy = user_id
        else:
            setting = Settings(
                key=key,
                value=str(value).strip(),
                description=description,
                createdBy=user_id,
            )
            db.add(setting)
        db.flush()
        return setting


settings_repo = SettingsRepository()
