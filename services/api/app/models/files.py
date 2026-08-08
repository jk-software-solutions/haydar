from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.identity import utc_now


class StoredFile(Base):
    __tablename__ = "stored_files"
    __table_args__ = (
        ForeignKeyConstraint(
            ["company_id", "uploaded_by_membership_id"],
            ["company_memberships.company_id", "company_memberships.id"],
            name="fk_stored_files_company_uploader",
        ),
        Index("ix_stored_files_company_created", "company_id", "created_at"),
        UniqueConstraint("company_id", "id", name="uq_stored_files_company_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    company_id: Mapped[UUID] = mapped_column(ForeignKey("companies.id"), nullable=False)
    uploaded_by_membership_id: Mapped[UUID] = mapped_column(nullable=False)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(120), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    content: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
