from uuid import uuid4
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id"), nullable=False, index=True
    )
    persona_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("personas.id"), nullable=False
    )
    scenario_type: Mapped[str] = mapped_column(String, nullable=False)  # "template" | "free"
    scenario_config: Mapped[dict] = mapped_column(JSON, default=dict)
    turns: Mapped[list] = mapped_column(JSON, default=list)
    savepoints: Mapped[list] = mapped_column(JSON, default=list)
    feedback: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    persona: Mapped["Persona"] = relationship("Persona", back_populates="simulations")
