import uuid
from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.dao.customer_dao import CustomerDAO
from app.exceptions.handlers import DuplicateEmailError
from app.models.customer import AccountStatus


def sample_customer_data(**overrides) -> dict:
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
    return {**defaults, **overrides}


# ── create ───────────────────────────────────────────────────────────────────


async def test_create_customer(db_session: AsyncSession):
    """Should persist all fields and auto-generate id, created_at."""
    dao = CustomerDAO(db_session)
    customer = await dao.create(sample_customer_data())

    assert customer.id is not None
    assert customer.first_name == "John"
    assert customer.last_name == "Doe"
    assert customer.email == "john.doe@example.com"
    assert customer.credit_score == 700
    assert customer.account_status == AccountStatus.ACTIVE
    assert customer.created_at is not None
    assert customer.deleted_at is None


async def test_create_duplicate_email_raises(db_session: AsyncSession):
    """Should raise DuplicateEmailError when email is already taken by an active customer."""
    dao = CustomerDAO(db_session)
    await dao.create(sample_customer_data())

    with pytest.raises(DuplicateEmailError):
        await dao.create(sample_customer_data(first_name="Jane"))


async def test_create_duplicate_email_allowed_after_soft_delete(db_session: AsyncSession):
    """Should allow reusing an email after the original customer was soft-deleted."""
    dao = CustomerDAO(db_session)
    customer = await dao.create(sample_customer_data())
    await dao.soft_delete(customer.id)

    second = await dao.create(sample_customer_data(first_name="Jane"))
    assert second.email == "john.doe@example.com"
    assert second.id != customer.id


# ── get_by_id ────────────────────────────────────────────────────────────────


async def test_get_by_id_returns_customer(db_session: AsyncSession):
    """Should return the customer when a valid active id is provided."""
    dao = CustomerDAO(db_session)
    created = await dao.create(sample_customer_data())

    found = await dao.get_by_id(created.id)
    assert found is not None
    assert found.id == created.id


async def test_get_by_id_returns_none_for_nonexistent(db_session: AsyncSession):
    """Should return None when no customer exists with the given id."""
    dao = CustomerDAO(db_session)
    result = await dao.get_by_id(uuid.uuid4())
    assert result is None


async def test_get_by_id_returns_none_for_soft_deleted(db_session: AsyncSession):
    """Should return None for a customer that has been soft-deleted."""
    dao = CustomerDAO(db_session)
    customer = await dao.create(sample_customer_data())
    await dao.soft_delete(customer.id)

    result = await dao.get_by_id(customer.id)
    assert result is None


# ── get_by_email ─────────────────────────────────────────────────────────────


async def test_get_by_email_returns_customer(db_session: AsyncSession):
    """Should return the customer when an active customer has the given email."""
    dao = CustomerDAO(db_session)
    created = await dao.create(sample_customer_data())

    found = await dao.get_by_email(created.email)
    assert found is not None
    assert found.id == created.id


async def test_get_by_email_returns_none_for_nonexistent(db_session: AsyncSession):
    """Should return None when no customer has the given email."""
    dao = CustomerDAO(db_session)
    result = await dao.get_by_email("nobody@example.com")
    assert result is None


async def test_get_by_email_returns_none_for_soft_deleted(db_session: AsyncSession):
    """Should return None when the customer with that email was soft-deleted."""
    dao = CustomerDAO(db_session)
    customer = await dao.create(sample_customer_data())
    await dao.soft_delete(customer.id)

    result = await dao.get_by_email(customer.email)
    assert result is None


# ── get_all ──────────────────────────────────────────────────────────────────


async def test_get_all_returns_active_customers(db_session: AsyncSession):
    """Should return all active (non-deleted) customers."""
    dao = CustomerDAO(db_session)
    await dao.create(sample_customer_data(email="a@example.com"))
    await dao.create(sample_customer_data(email="b@example.com"))
    await dao.create(sample_customer_data(email="c@example.com"))

    results = await dao.get_all()
    assert len(results) == 3


async def test_get_all_excludes_soft_deleted(db_session: AsyncSession):
    """Should not include soft-deleted customers in the results."""
    dao = CustomerDAO(db_session)
    await dao.create(sample_customer_data(email="a@example.com"))
    to_delete = await dao.create(sample_customer_data(email="b@example.com"))
    await dao.soft_delete(to_delete.id)

    results = await dao.get_all()
    assert len(results) == 1
    assert results[0].email == "a@example.com"


async def test_get_all_pagination(db_session: AsyncSession):
    """Should respect skip and limit for paginated queries."""
    dao = CustomerDAO(db_session)
    for i in range(5):
        await dao.create(sample_customer_data(email=f"user{i}@example.com"))

    page = await dao.get_all(skip=2, limit=2)
    assert len(page) == 2


async def test_get_all_returns_empty_list_when_none_exist(db_session: AsyncSession):
    """Should return an empty list when no customers exist in the database."""
    dao = CustomerDAO(db_session)
    results = await dao.get_all()
    assert results == []


# ── update ───────────────────────────────────────────────────────────────────


async def test_update_customer(db_session: AsyncSession):
    """Should update specified fields and leave others unchanged."""
    dao = CustomerDAO(db_session)
    customer = await dao.create(sample_customer_data())

    updated = await dao.update(customer.id, {"first_name": "Jane", "credit_score": 800})
    assert updated is not None
    assert updated.first_name == "Jane"
    assert updated.credit_score == 800
    assert updated.last_name == "Doe"  # unchanged


async def test_update_returns_none_for_nonexistent(db_session: AsyncSession):
    """Should return None when trying to update a customer that doesn't exist."""
    dao = CustomerDAO(db_session)
    result = await dao.update(uuid.uuid4(), {"first_name": "Ghost"})
    assert result is None


async def test_update_returns_none_for_soft_deleted(db_session: AsyncSession):
    """Should return None when trying to update a soft-deleted customer."""
    dao = CustomerDAO(db_session)
    customer = await dao.create(sample_customer_data())
    await dao.soft_delete(customer.id)

    result = await dao.update(customer.id, {"first_name": "Jane"})
    assert result is None


async def test_update_duplicate_email_raises(db_session: AsyncSession):
    """Should raise DuplicateEmailError when updating email to one already taken."""
    dao = CustomerDAO(db_session)
    await dao.create(sample_customer_data(email="taken@example.com"))
    second = await dao.create(sample_customer_data(email="second@example.com"))

    with pytest.raises(DuplicateEmailError):
        await dao.update(second.id, {"email": "taken@example.com"})


# ── soft_delete ──────────────────────────────────────────────────────────────


async def test_soft_delete_returns_true(db_session: AsyncSession):
    """Should return True and set deleted_at when deleting an active customer."""
    dao = CustomerDAO(db_session)
    customer = await dao.create(sample_customer_data())

    result = await dao.soft_delete(customer.id)
    assert result is True


async def test_soft_delete_returns_false_for_nonexistent(db_session: AsyncSession):
    """Should return False when trying to delete a customer that doesn't exist."""
    dao = CustomerDAO(db_session)
    result = await dao.soft_delete(uuid.uuid4())
    assert result is False


async def test_soft_delete_returns_false_for_already_deleted(db_session: AsyncSession):
    """Should return False when trying to soft-delete an already deleted customer."""
    dao = CustomerDAO(db_session)
    customer = await dao.create(sample_customer_data())
    await dao.soft_delete(customer.id)

    result = await dao.soft_delete(customer.id)
    assert result is False


async def test_soft_delete_excludes_from_get_by_id_and_get_all(db_session: AsyncSession):
    """After soft-deleting, the customer should not appear in get_by_id or get_all."""
    dao = CustomerDAO(db_session)
    c1 = await dao.create(sample_customer_data(email="keep@example.com"))
    c2 = await dao.create(sample_customer_data(email="delete@example.com"))

    await dao.soft_delete(c2.id)

    assert await dao.get_by_id(c2.id) is None

    all_customers = await dao.get_all()
    assert len(all_customers) == 1
    assert all_customers[0].id == c1.id
