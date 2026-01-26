import uuid

from sqlalchemy import String, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.text.enums import SourceType, SummaryStatus, SummaryLevel


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    source_type: Mapped[SourceType] = mapped_column(
        SQLEnum(SourceType, native_enum=False, length=16),
        nullable=False,
        index=True
    )

    original_text: Mapped[str] = mapped_column(Text, nullable=False, default="")

    file_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    summaries: Mapped[list["Summary"]] = relationship(
        "Summary",
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))

    document_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )

    level: Mapped[SummaryLevel] = mapped_column(
        SQLEnum(SummaryLevel, native_enum=False, length=16),
        nullable=False,
        default=SummaryLevel.MEDIUM,
        index=True
    )

    status: Mapped[SummaryStatus] = mapped_column(
        SQLEnum(SummaryStatus, native_enum=False, length=16),
        nullable=False,
        default=SummaryStatus.PROCESSING,
        index=True
    )

    summary_text: Mapped[str] = mapped_column(Text, nullable=True)

    model: Mapped[str] = mapped_column(String(64), nullable=False, default="sonar-pro")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="summaries")