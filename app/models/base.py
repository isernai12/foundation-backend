import datetime
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, declared_attr


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.
    Automatically generates __tablename__ from class name in snake_case if omitted.
    """
    @declared_attr.directive
    def __tablename__(cls) -> str:
        name = cls.__name__
        # Convert PascalCase to snake_case
        return "".join(["_" + c.lower() if c.isupper() and i > 0 else c.lower() for i, c in enumerate(name)])


class TimestampMixin:
    """Mixin adding created_at and updated_at datetime tracking."""
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
