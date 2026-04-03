import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.customer_dao import CustomerDAO
from app.database import get_db
from app.schemas.customer import CustomerCreate, CustomerResponse, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter(prefix="/customers", tags=["Customers"])


def get_service(db: AsyncSession = Depends(get_db)) -> CustomerService:
    return CustomerService(CustomerDAO(db))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=CustomerResponse)
async def create_customer(
    body: CustomerCreate,
    service: CustomerService = Depends(get_service),
) -> CustomerResponse:
    return await service.create_customer(body)


@router.get("", response_model=list[CustomerResponse])
async def get_customers(
    skip: int = 0,
    limit: int = 10,
    service: CustomerService = Depends(get_service),
) -> list[CustomerResponse]:
    return await service.get_all_customers(skip=skip, limit=limit)


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: uuid.UUID,
    service: CustomerService = Depends(get_service),
) -> CustomerResponse:
    return await service.get_customer(customer_id)


@router.put("/{customer_id}", response_model=CustomerResponse)
async def update_customer(
    customer_id: uuid.UUID,
    body: CustomerUpdate,
    service: CustomerService = Depends(get_service),
) -> CustomerResponse:
    return await service.update_customer(customer_id, body)


@router.delete("/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_customer(
    customer_id: uuid.UUID,
    service: CustomerService = Depends(get_service),
) -> None:
    await service.delete_customer(customer_id)
