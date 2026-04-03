import enum
import uuid
from datetime import date, datetime

from sqlalchemy import DateTime, Index, String, func, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class AccountStatus(enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255))
    phone_number: Mapped[str | None] = mapped_column(String(20), default=None)
    date_of_birth: Mapped[date]
    address: Mapped[str | None] = mapped_column(String(500), default=None)
    account_status: Mapped[AccountStatus] = mapped_column(default=AccountStatus.ACTIVE)
    credit_score: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    __table_args__ = (
        Index("uq_customers_email_active", "email", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )
