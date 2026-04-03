# Customer Management API — Design Doc

## Folder Structure

```
app/
customer-api/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── models/
│   │   ├── __init__.py
│   │   └── customer.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── customer.py
│   ├── dao/
│   │   ├── __init__.py
│   │   └── customer_dao.py
│   ├── services/
│   │   ├── __init__.py
│   │   └── customer_service.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── customer_router.py
│   └── exceptions/
│       ├── __init__.py
│       └── handlers.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env
├── .env.example
└── README.md
```

---

## Layer Architecture

```
Request
  │
  ▼
┌─────────┐   Pydantic schema in   ┌───────────┐   domain objects   ┌───────┐   SQLAlchemy queries   ┌────┐
│  Router  │ ───────────────────▶  │  Service   │ ────────────────▶ │  DAO  │ ─────────────────────▶ │ DB │
│ (HTTP)   │                        │ (Business) │                   │(Data) │                        └────┘
└─────────┘ ◀─────────────────── └───────────┘ ◀──────────────── └───────┘
  Pydantic schema out              raises exceptions              returns ORM models
```

| Layer | Responsibility | Knows about |
|-------|---------------|-------------|
| **Router** | Parse HTTP request, validate via Pydantic, call service, return response + status code | Schemas, Service |
| **Service** | Business rules (duplicate checks, soft-delete logic, field transforms) | DAO, Exceptions, Schemas/Models |
| **DAO** | Execute DB queries, return ORM model instances or None | SQLAlchemy models, AsyncSession |
| **DB (database.py)** | Engine, session factory, `get_session` async generator | Nothing above it |

**Rule:** Each layer only imports the one directly below it. Router never touches DAO or SQLAlchemy directly.

---

## Dependency Injection Flow

FastAPI's `Depends()` wires everything together — no global singletons.

```python
# database.py
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session

# dependencies.py
def get_customer_dao(session: AsyncSession = Depends(get_session)) -> CustomerDAO:
    return CustomerDAO(session)

def get_customer_service(dao: CustomerDAO = Depends(get_customer_dao)) -> CustomerService:
    return CustomerService(dao)

# routers/customer.py
@router.post("/customers", status_code=201)
async def create_customer(
    body: CustomerCreate,
    service: CustomerService = Depends(get_customer_service),
) -> CustomerResponse:
    return await service.create(body)
```

**Chain:** `get_session` → `get_customer_dao(session)` → `get_customer_service(dao)` → router handler.

Each request gets its own session + DAO + service instance. Session is committed/rolled-back in the service layer and closed automatically when the `get_session` generator exits.

---

## Custom Exceptions

```
AppException (base)                     → status 500
├── CustomerNotFoundException           → status 404, "Customer with id {id} not found"
├── DuplicateCustomerEmailException     → status 409, "Email already registered"
└── InvalidCustomerDataException        → status 422, "..."  (for business-rule violations beyond Pydantic)
```

```python
# exceptions/base.py
class AppException(Exception):
    status_code: int = 500
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail

# exceptions/customer.py
class CustomerNotFoundException(AppException):
    status_code = 404
    detail = "Customer not found"

# exceptions/handlers.py  — registered in main.py
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
```

Service layer raises these; router never catches manually — the global handler does it.

---

## Soft Delete

The `Customer` model carries two columns for soft delete:

```python
class Customer(Base):
    __tablename__ = "customers"

    id:           Mapped[int]              = mapped_column(primary_key=True)
    name:         Mapped[str]              = mapped_column(String(255))
    email:        Mapped[str]              = mapped_column(String(255), unique=True)
    phone:        Mapped[str | None]       = mapped_column(String(50))
    is_deleted:   Mapped[bool]             = mapped_column(default=False)       # soft-delete flag
    created_at:   Mapped[datetime]         = mapped_column(server_default=func.now())
    updated_at:   Mapped[datetime | None]  = mapped_column(onupdate=func.now())
```

**How it works across layers:**

| Operation | DAO behaviour |
|-----------|--------------|
| **GET (list/single)** | Adds `.where(Customer.is_deleted == False)` to every SELECT |
| **DELETE** | `UPDATE customers SET is_deleted = true WHERE id = :id` — never issues a real DELETE |
| **POST (create)** | Before insert, checks for existing soft-deleted row with same email; if found, service can choose to reactivate or reject |
| **Unique email** | DAO duplicate-check query also filters `is_deleted == False` so a deleted customer's email can be reused |

The DAO has a private helper `_base_query()` that always appends the soft-delete filter so you can't accidentally leak deleted records.

---

## Request / Response Flow — `POST /customers`

Concrete walkthrough, not abstract:

```
1.  CLIENT → POST /customers
    Body: {"name": "Sid", "email": "sid@example.com", "phone": "1234567890"}

2.  ROUTER  (routers/customer.py :: create_customer)
    • FastAPI auto-validates body against CustomerCreate schema (Pydantic v2)
    • If validation fails → 422 returned automatically, flow stops
    • Calls: customer = await service.create(body)

3.  SERVICE  (services/customer.py :: CustomerService.create)
    • Calls: existing = await self.dao.get_by_email(body.email)
    • If existing → raises DuplicateCustomerEmailException (409)
    • Converts schema → dict: data = body.model_dump()
    • Calls: customer = await self.dao.create(data)
    • Returns ORM model instance back to router

4.  DAO  (dao/customer.py :: CustomerDAO.create)
    • Builds: new_customer = Customer(**data)
    • self.session.add(new_customer)
    • await self.session.commit()
    • await self.session.refresh(new_customer)   ← gets DB-generated id, created_at
    • Returns the ORM model instance

5.  ROUTER  (back in create_customer)
    • FastAPI serializes ORM model through CustomerResponse schema (response_model)
    • Returns 201 + JSON:
      {
        "id": 1,
        "name": "Sid",
        "email": "sid@example.com",
        "phone": "1234567890",
        "created_at": "2026-04-02T10:30:00Z"
      }

── ERROR PATH ──
    • If service raised DuplicateCustomerEmailException
      → Global exception handler catches it
      → Returns 409 + {"detail": "Email already registered"}
```

```
Sequence (happy path):

Client ──▶ Router ──▶ Service ──▶ DAO ──▶ PostgreSQL
                                            │
Client ◀── Router ◀── Service ◀── DAO ◀────┘
 201         schema     model      model   INSERT + RETURNING
```

---

**That's the full blueprint. Next step: scaffold the folders and start coding `database.py` → models → DAO → service → router, bottom-up.**
