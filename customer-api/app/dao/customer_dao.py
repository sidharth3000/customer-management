import uuid
from datetime import datetime, timezone

from sqlalchemy import ColumnElement, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.exceptions.handlers import DuplicateEmailError
from app.models.customer import Customer


class CustomerDAO:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _active_filter(self) -> ColumnElement[bool]:
        return Customer.deleted_at.is_(None)

    async def create(self, data: dict) -> Customer:
        try:
            customer = Customer(**data)
            self.session.add(customer)
            await self.session.commit()
            await self.session.refresh(customer)
            return customer
        except IntegrityError:
            await self.session.rollback()
            raise DuplicateEmailError()

    async def get_by_id(self, customer_id: uuid.UUID) -> Customer | None:
        stmt = select(Customer).where(Customer.id == customer_id, self._active_filter())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Customer | None:
        stmt = select(Customer).where(Customer.email == email, self._active_filter())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all(self, skip: int = 0, limit: int = 100) -> list[Customer]:
        stmt = (
            select(Customer)
            .where(self._active_filter())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, customer_id: uuid.UUID, data: dict) -> Customer | None:
        stmt = (
            update(Customer)
            .where(Customer.id == customer_id, self._active_filter())
            .values(**data)
            .returning(Customer)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one_or_none()

    async def soft_delete(self, customer_id: uuid.UUID) -> bool:
        stmt = (
            update(Customer)
            .where(Customer.id == customer_id, self._active_filter())
            .values(deleted_at=datetime.now(timezone.utc))
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.rowcount > 0
