import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.customer_dao import CustomerDAO
from app.exceptions.handlers import CustomerNotFoundError, DuplicateEmailError
from app.models.customer import AccountStatus
from app.schemas.customer import CustomerCreate, CustomerUpdate
from app.services.customer_service import CustomerService


def make_create_data(**overrides) -> CustomerCreate:
    defaults = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "1234567890",
        "date_of_birth": date(1990, 5, 15),
        "address": "123 Main St",
        "account_status": AccountStatus.ACTIVE,
        "credit_score": 700,
    }
    return CustomerCreate(**{**defaults, **overrides})


def make_service(db_session: AsyncSession) -> CustomerService:
    return CustomerService(CustomerDAO(db_session))


# ── create_customer ──────────────────────────────────────────────────────────


async def test_create_customer(db_session: AsyncSession):
    """Should create and return a customer with all fields persisted."""
    service = make_service(db_session)
    customer = await service.create_customer(make_create_data())

    assert customer.id is not None
    assert customer.email == "john.doe@example.com"
    assert customer.first_name == "John"
    assert customer.created_at is not None


async def test_create_customer_duplicate_email_raises(db_session: AsyncSession):
    """Should raise DuplicateEmailError when the email is already in use."""
    service = make_service(db_session)
    await service.create_customer(make_create_data())

    with pytest.raises(DuplicateEmailError):
        await service.create_customer(make_create_data(first_name="Jane"))


# ── get_customer ─────────────────────────────────────────────────────────────


async def test_get_customer(db_session: AsyncSession):
    """Should return the correct customer by id."""
    service = make_service(db_session)
    created = await service.create_customer(make_create_data())

    found = await service.get_customer(created.id)
    assert found.id == created.id


async def test_get_customer_not_found_raises(db_session: AsyncSession):
    """Should raise CustomerNotFoundError when the id doesn't exist."""
    service = make_service(db_session)

    with pytest.raises(CustomerNotFoundError):
        await service.get_customer(uuid.uuid4())


# ── get_all_customers ────────────────────────────────────────────────────────


async def test_get_all_customers(db_session: AsyncSession):
    """Should return all active customers."""
    service = make_service(db_session)
    await service.create_customer(make_create_data(email="a@example.com"))
    await service.create_customer(make_create_data(email="b@example.com"))

    results = await service.get_all_customers()
    assert len(results) == 2


async def test_get_all_customers_empty(db_session: AsyncSession):
    """Should return an empty list when no customers exist."""
    service = make_service(db_session)
    results = await service.get_all_customers()
    assert results == []


# ── update_customer ──────────────────────────────────────────────────────────


async def test_update_customer(db_session: AsyncSession):
    """Should update the given fields and return the updated customer."""
    service = make_service(db_session)
    customer = await service.create_customer(make_create_data())

    updated = await service.update_customer(
        customer.id, CustomerUpdate(first_name="Jane", credit_score=800)
    )
    assert updated.first_name == "Jane"
    assert updated.credit_score == 800
    assert updated.last_name == "Doe"  # unchanged


async def test_update_email_to_duplicate_raises(db_session: AsyncSession):
    """Should raise DuplicateEmailError when changing email to one owned by another customer."""
    service = make_service(db_session)
    await service.create_customer(make_create_data(email="taken@example.com"))
    second = await service.create_customer(make_create_data(email="second@example.com"))

    with pytest.raises(DuplicateEmailError):
        await service.update_customer(
            second.id, CustomerUpdate(email="taken@example.com")
        )


async def test_update_email_to_own_email_allowed(db_session: AsyncSession):
    """Should allow updating email to the same value the customer already has."""
    service = make_service(db_session)
    customer = await service.create_customer(make_create_data())

    updated = await service.update_customer(
        customer.id, CustomerUpdate(email="john.doe@example.com")
    )
    assert updated.email == "john.doe@example.com"


async def test_update_customer_not_found_raises(db_session: AsyncSession):
    """Should raise CustomerNotFoundError when the customer id doesn't exist."""
    service = make_service(db_session)

    with pytest.raises(CustomerNotFoundError):
        await service.update_customer(
            uuid.uuid4(), CustomerUpdate(first_name="Ghost")
        )


async def test_update_partial_does_not_null_other_fields(db_session: AsyncSession):
    """Should only update provided fields; unset fields must remain unchanged."""
    service = make_service(db_session)
    customer = await service.create_customer(make_create_data())

    updated = await service.update_customer(
        customer.id, CustomerUpdate(first_name="Jane")
    )
    assert updated.first_name == "Jane"
    assert updated.email == "john.doe@example.com"
    assert updated.credit_score == 700
    assert updated.phone_number == "1234567890"


# ── delete_customer ──────────────────────────────────────────────────────────


async def test_delete_customer(db_session: AsyncSession):
    """Should soft-delete the customer so it's no longer retrievable."""
    service = make_service(db_session)
    customer = await service.create_customer(make_create_data())

    await service.delete_customer(customer.id)

    with pytest.raises(CustomerNotFoundError):
        await service.get_customer(customer.id)


async def test_delete_customer_not_found_raises(db_session: AsyncSession):
    """Should raise CustomerNotFoundError when deleting a nonexistent customer."""
    service = make_service(db_session)

    with pytest.raises(CustomerNotFoundError):
        await service.delete_customer(uuid.uuid4())
