import uuid

from app.dao.customer_dao import CustomerDAO
from app.exceptions.handlers import CustomerNotFoundError, DuplicateEmailError
from app.models.customer import Customer
from app.schemas.customer import CustomerCreate, CustomerUpdate


class CustomerService:
    def __init__(self, dao: CustomerDAO):
        self.dao = dao

    async def create_customer(self, data: CustomerCreate) -> Customer:
        existing = await self.dao.get_by_email(data.email)
        if existing:
            raise DuplicateEmailError()
        return await self.dao.create(data.model_dump())

    async def get_customer(self, customer_id: uuid.UUID) -> Customer:
        customer = await self.dao.get_by_id(customer_id)
        if not customer:
            raise CustomerNotFoundError(customer_id)
        return customer

    async def get_all_customers(self, skip: int = 0, limit: int = 100) -> list[Customer]:
        return await self.dao.get_all(skip=skip, limit=limit)

    async def update_customer(self, customer_id: uuid.UUID, data: CustomerUpdate) -> Customer:
        if data.email is not None:
            existing = await self.dao.get_by_email(data.email)
            if existing and existing.id != customer_id:
                raise DuplicateEmailError()
        updated = await self.dao.update(customer_id, data.model_dump(exclude_unset=True))
        if not updated:
            raise CustomerNotFoundError(customer_id)
        return updated

    async def delete_customer(self, customer_id: uuid.UUID) -> None:
        deleted = await self.dao.soft_delete(customer_id)
        if not deleted:
            raise CustomerNotFoundError(customer_id)
