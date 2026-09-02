import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, JSON, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from DB.database import Base


class GameSession(Base):
    __tablename__ = "games"

    session_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )

    status: Mapped[str] = mapped_column(
        String(20),
        default="active",
        nullable=False
    )
    
    ships: Mapped[list] = mapped_column(JSON, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )