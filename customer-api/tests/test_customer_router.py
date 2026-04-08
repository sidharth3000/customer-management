import uuid

from httpx import AsyncClient


def sample_payload(**overrides) -> dict:
    defaults = {
        "first_name": "John",
        "last_name": "Doe",
        "email": "john.doe@example.com",
        "phone_number": "1234567890",
        "date_of_birth": "1990-05-15",
        "address": "123 Main St",
        "account_status": "ACTIVE",
        "credit_score": 700,
    }
    return {**defaults, **overrides}


async def _create_customer(client: AsyncClient, **overrides) -> dict:
    resp = await client.post("/customers", json=sample_payload(**overrides))
    assert resp.status_code == 201
    return resp.json()


# ── POST /customers ──────────────────────────────────────────────────────────


async def test_create_customer(client: AsyncClient):
    """POST /customers with valid data should return 201 with the created customer."""
    resp = await client.post("/customers", json=sample_payload())

    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "john.doe@example.com"
    assert body["first_name"] == "John"
    assert body["credit_score"] == 700
    assert "id" in body
    assert "created_at" in body


async def test_create_customer_optional_fields_omitted(client: AsyncClient):
    """POST /customers without phone_number and address should default them to null."""
    payload = sample_payload()
    del payload["phone_number"]
    del payload["address"]

    resp = await client.post("/customers", json=payload)

    assert resp.status_code == 201
    body = resp.json()
    assert body["phone_number"] is None
    assert body["address"] is None


async def test_create_customer_duplicate_email(client: AsyncClient):
    """POST /customers with an already-used email should return 409 Conflict."""
    await _create_customer(client)

    resp = await client.post("/customers", json=sample_payload(first_name="Jane"))
    assert resp.status_code == 409


async def test_create_customer_missing_required_field(client: AsyncClient):
    """POST /customers without a required field (email) should return 422."""
    payload = sample_payload()
    del payload["email"]

    resp = await client.post("/customers", json=payload)
    assert resp.status_code == 422


async def test_create_customer_invalid_email(client: AsyncClient):
    """POST /customers with a malformed email should return 422."""
    resp = await client.post("/customers", json=sample_payload(email="not-an-email"))
    assert resp.status_code == 422


async def test_create_customer_credit_score_below_min(client: AsyncClient):
    """POST /customers with credit_score below 300 should return 422."""
    resp = await client.post("/customers", json=sample_payload(credit_score=100))
    assert resp.status_code == 422


async def test_create_customer_credit_score_above_max(client: AsyncClient):
    """POST /customers with credit_score above 850 should return 422."""
    resp = await client.post("/customers", json=sample_payload(credit_score=900))
    assert resp.status_code == 422


async def test_create_customer_dob_in_future(client: AsyncClient):
    """POST /customers with a future date_of_birth should return 422."""
    resp = await client.post("/customers", json=sample_payload(date_of_birth="2099-01-01"))
    assert resp.status_code == 422


# ── GET /customers ───────────────────────────────────────────────────────────


async def test_get_customers(client: AsyncClient):
    """GET /customers should return all active customers."""
    await _create_customer(client, email="a@example.com")
    await _create_customer(client, email="b@example.com")
    await _create_customer(client, email="c@example.com")

    resp = await client.get("/customers")

    assert resp.status_code == 200
    assert len(resp.json()) == 3


async def test_get_customers_empty(client: AsyncClient):
    """GET /customers with no data should return an empty list."""
    resp = await client.get("/customers")

    assert resp.status_code == 200
    assert resp.json() == []


async def test_get_customers_pagination(client: AsyncClient):
    """GET /customers with skip and limit should return the correct page."""
    for i in range(5):
        await _create_customer(client, email=f"user{i}@example.com")

    resp = await client.get("/customers", params={"skip": 2, "limit": 2})

    assert resp.status_code == 200
    assert len(resp.json()) == 2


# ── GET /customers/{customer_id} ─────────────────────────────────────────────


async def test_get_customer_by_id(client: AsyncClient):
    """GET /customers/{id} should return the customer matching the given id."""
    created = await _create_customer(client)

    resp = await client.get(f"/customers/{created['id']}")

    assert resp.status_code == 200
    assert resp.json()["id"] == created["id"]


async def test_get_customer_not_found(client: AsyncClient):
    """GET /customers/{id} with a nonexistent id should return 404."""
    resp = await client.get(f"/customers/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_get_customer_invalid_uuid(client: AsyncClient):
    """GET /customers/{id} with an invalid UUID format should return 422."""
    resp = await client.get("/customers/not-a-uuid")
    assert resp.status_code == 422


# ── PUT /customers/{customer_id} ─────────────────────────────────────────────


async def test_update_customer(client: AsyncClient):
    """PUT /customers/{id} should update the specified fields and return 200."""
    created = await _create_customer(client)

    resp = await client.put(
        f"/customers/{created['id']}",
        json={"first_name": "Jane", "credit_score": 800},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "Jane"
    assert body["credit_score"] == 800


async def test_update_customer_partial(client: AsyncClient):
    """PUT /customers/{id} with one field should leave all other fields unchanged."""
    created = await _create_customer(client)

    resp = await client.put(
        f"/customers/{created['id']}",
        json={"first_name": "Jane"},
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["first_name"] == "Jane"
    assert body["email"] == "john.doe@example.com"  # unchanged
    assert body["credit_score"] == 700  # unchanged


async def test_update_customer_duplicate_email(client: AsyncClient):
    """PUT /customers/{id} changing email to one already taken should return 409."""
    await _create_customer(client, email="taken@example.com")
    second = await _create_customer(client, email="second@example.com")

    resp = await client.put(
        f"/customers/{second['id']}",
        json={"email": "taken@example.com"},
    )

    assert resp.status_code == 409


async def test_update_customer_not_found(client: AsyncClient):
    """PUT /customers/{id} with a nonexistent id should return 404."""
    resp = await client.put(
        f"/customers/{uuid.uuid4()}",
        json={"first_name": "Ghost"},
    )

    assert resp.status_code == 404


async def test_update_customer_invalid_credit_score(client: AsyncClient):
    """PUT /customers/{id} with credit_score out of range should return 422."""
    created = await _create_customer(client)

    resp = await client.put(
        f"/customers/{created['id']}",
        json={"credit_score": 100},
    )

    assert resp.status_code == 422


# ── DELETE /customers/{customer_id} ──────────────────────────────────────────


async def test_delete_customer(client: AsyncClient):
    """DELETE /customers/{id} should return 204 on success."""
    created = await _create_customer(client)

    resp = await client.delete(f"/customers/{created['id']}")
    assert resp.status_code == 204


async def test_delete_customer_not_found(client: AsyncClient):
    """DELETE /customers/{id} with a nonexistent id should return 404."""
    resp = await client.delete(f"/customers/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_deleted_customer_not_retrievable(client: AsyncClient):
    """After DELETE, GET /customers/{id} for the same customer should return 404."""
    created = await _create_customer(client)

    await client.delete(f"/customers/{created['id']}")

    resp = await client.get(f"/customers/{created['id']}")
    assert resp.status_code == 404
