# Prompts Log — Customer Management API

This file captures the full conversation history from the initial design session through implementation and review.

---

## Prompt 1: Design Doc

**User:**
> I'm building a customer management REST API for an assignment using FastAPI, async SQLAlchemy (asyncpg), PostgreSQL, Pydantic v2 and Docker. Before I start coding I want a short design doc covering: the folder structure and what each file does, the layer architecture (router → service → dao → db), how dependency injection flows across these layers, what kind of custom exceptions I should have, and how soft delete will be handled; also quickly outline the request/response flow for a typical POST /customers call from router till DB and back. Keep it practical not too theoretical and concise.

**Response:**
Created `DESIGN.md` covering:
- Folder structure with file descriptions
- Layer architecture diagram: Router (HTTP) → Service (Business) → DAO (Data) → DB
- Dependency injection chain via FastAPI's `Depends()`: `get_session` → `CustomerDAO(session)` → `CustomerService(dao)` → router handler
- Custom exceptions: `AppException` base, `CustomerNotFoundException` (404), `DuplicateCustomerEmailException` (409), `InvalidCustomerDataException` (422)
- Soft delete via `is_deleted` flag, with `_base_query()` helper filtering deleted records
- Full POST /customers walkthrough from HTTP request to DB insert and back

---

## Prompt 2: Create Folder Structure

**User:**
> Create the folder structure from design.md for this project, I have updated it don't revert it back.

**Response:**
Read the updated `DESIGN.md` (user changed structure to `customer-api/` root with renamed files like `customer_dao.py`, `customer_service.py`, `customer_router.py`). Created all directories and empty placeholder files:
- `customer-api/app/` — `__init__.py`, `main.py`, `config.py`, `database.py`
- `customer-api/app/models/` — `__init__.py`, `customer.py`
- `customer-api/app/schemas/` — `__init__.py`, `customer.py`
- `customer-api/app/dao/` — `__init__.py`, `customer_dao.py`
- `customer-api/app/services/` — `__init__.py`, `customer_service.py`
- `customer-api/app/routers/` — `__init__.py`, `customer_router.py`
- `customer-api/app/exceptions/` — `__init__.py`, `handlers.py`
- `customer-api/Dockerfile`, `docker-compose.yml`, `requirements.txt`, `.env.example`, `README.md`

---

## Prompt 3: Config with Pydantic Settings

**User:**
> I need a config.py that loads env variables using pydantic-settings. I need DATABASE_URL, APP_HOST, APP_PORT and a DEBUG flag. Keep it simple, just read from a .env file. Also create a .env.example file so someone cloning the repo knows what vars they need to set.

**Response:**
- `app/config.py` — `Settings` class using `BaseSettings` with `SettingsConfigDict(env_file=".env")`. `DATABASE_URL` required, others have defaults. Module-level `settings = Settings()` singleton.
- `.env.example` — template with all four vars and sample PostgreSQL connection string.

---

## Prompt 4: Requirements.txt

**User:**
> Generate a requirements.txt for my project. I'm using fastapi, uvicorn, sqlalchemy with async support, asyncpg, pydantic v2, pydantic-settings and python-dotenv. Pin the versions so it doesn't break later. Don't add anything extra that I won't use.

**Response:**
Created `requirements.txt` with pinned versions:
- fastapi==0.115.12, uvicorn==0.34.0, sqlalchemy==2.0.40, asyncpg==0.30.0, pydantic==2.10.6, pydantic-settings==2.8.1, python-dotenv==1.0.1

---

## Prompt 5: Database Setup

**User:**
> Now write the database.py file. I need async engine and async session setup using sqlalchemy and asyncpg. Create a get_db function that I can use as a FastAPI dependency — it should yield a session and make sure it closes properly even if something fails. I'm new to async sqlalchemy so keep it straightforward.

**Response:**
`app/database.py` with:
- `engine` — `create_async_engine` from `DATABASE_URL`, `echo=settings.DEBUG`
- `async_session` — `async_sessionmaker` with `expire_on_commit=False`
- `get_db()` — async generator yielding session inside `try/finally` for guaranteed cleanup

---

## Prompt 6: SQLAlchemy Customer Model

**User:**
> Write the customer SQLAlchemy model in models/customer.py. Fields: id (UUID, auto-generated), first_name (string, required), last_name (string, required), email (string, required, unique), phone_number (string, optional), date_of_birth (date, required), address (string, optional), account_status (enum ACTIVE/INACTIVE/SUSPENDED, default ACTIVE), credit_score (integer), created_at (datetime, auto set). Also a deleted_at field for soft delete — nullable, default None. Create AccountStatus as a separate Python enum class. Use mapped_column style.

**Response:**
`app/models/customer.py` with:
- `Base` declarative base
- `AccountStatus` enum (ACTIVE, INACTIVE, SUSPENDED)
- `Customer` model with all fields using `Mapped[]` + `mapped_column()`, UUID primary key via `uuid.uuid4`, `created_at` with `server_default=func.now()`, `deleted_at` nullable for soft delete

---

## Prompt 7: Pydantic Schemas

**User:**
> Create pydantic v2 schemas in schemas/customer.py. Three schemas — CustomerCreate for POST (all required except id, created_at, account_status defaults to ACTIVE), CustomerUpdate for PUT (all fields optional), and CustomerResponse (includes id and created_at). Add validation for email format, credit_score between 300 and 850. Keep validators simple.

**Response:**
`app/schemas/customer.py` with:
- `CustomerCreate` — required fields, `EmailStr` for email, `Field(ge=300, le=850)` for credit_score
- `CustomerUpdate` — all `Optional` with same validators
- `CustomerResponse` — full model with `model_config = {"from_attributes": True}`
- Noted need for `email-validator` package

---

## Prompt 8: Custom Exceptions

**User:**
> Create exceptions/handlers.py with exception classes — CustomerNotFoundError, DuplicateEmailError, and a generic DatabaseError. Each should have a meaningful default message. Write a FastAPI exception handler that catches these and returns proper HTTP responses — 404, 409, 500. Response should be JSON with detail field, never expose stack traces.

**Response:**
`app/exceptions/handlers.py` with:
- `AppException` base class with `status_code` and `detail`
- `CustomerNotFoundError` (404) — optionally takes `customer_id` for specific message
- `DuplicateEmailError` (409)
- `DatabaseError` (500)
- `register_exception_handlers(app)` — global `AppException` handler returning `{"detail": "..."}`

---

## Prompt 9: Customer DAO

**User:**
> Write the CustomerDAO class in dao/customer_dao.py. Takes AsyncSession in constructor. Methods: create, get_by_id, get_by_email, get_all (skip/limit), update, soft_delete. Every read method should filter out soft-deleted records. This class should ONLY do database queries — no business logic, no validation, no duplicate checking. Let exceptions bubble up.

**Response:**
`app/dao/customer_dao.py` with:
- `_active_filter()` — private helper returning `Customer.deleted_at.is_(None)`
- `create` — insert + commit + refresh
- `get_by_id` / `get_by_email` — filtered selects returning `Customer | None`
- `get_all` — paginated with `offset`/`limit`
- `update` — `UPDATE ... RETURNING` pattern
- `soft_delete` — sets `deleted_at` to UTC now, returns `bool`

---

## Prompt 10: Customer Service

**User:**
> Write the CustomerService class in services/customer_service.py. Constructor takes CustomerDAO. Methods: create_customer (check duplicate email first), get_customer (raise not found if None), get_all_customers (pass through), update_customer (raise not found if None), delete_customer (raise not found if False). This layer should never import SQLAlchemy or touch the session directly.

**Response:**
`app/services/customer_service.py` with all methods delegating to DAO and raising domain exceptions. Uses `model_dump()` and `model_dump(exclude_unset=True)` for schema-to-dict conversion.

---

## Prompt 11: Email Check on Update

**User:**
> In update_customer method, if the email field is being updated it should also check whether the new email is already taken by a different customer. Raise DuplicateEmailError if so. Don't touch anything else.

**Response:**
Added email uniqueness check in `update_customer`: if `data.email is not None`, checks via `dao.get_by_email` and compares `existing.id != customer_id` to avoid false conflict with self.

---

## Prompt 12: Customer Router

**User:**
> Write the FastAPI router in routers/customer_router.py. Endpoints: POST /customers (201), GET /customers (list), GET /customers/{id}, PUT /customers/{id}, DELETE /customers/{id} (204). For DI: get db session with Depends(get_db), create CustomerDAO with that session, create CustomerService with that DAO. Use proper response_model on each route.

**Response:**
`app/routers/customer_router.py` with:
- `get_service` dependency chaining `get_db → CustomerDAO → CustomerService`
- All 5 CRUD endpoints with proper status codes and `response_model`
- `skip`/`limit` query params on GET list

---

## Prompt 13: Main.py

**User:**
> Write main.py — create the FastAPI app, include the customer router, register exception handlers. Add a startup event that creates all database tables using the async engine (not using alembic). Make uvicorn run with host and port from config.

**Response:**
`app/main.py` with:
- `lifespan` async context manager — `create_all` on startup, `engine.dispose()` on shutdown
- Exception handlers registered, customer router included
- `uvicorn.run` with settings from config, reload enabled in debug mode

---

## Prompt 14: Run and Fix

**User:**
> Run the app and fix if any issue is there.

**Response:**
Fixed multiple issues:
1. Created venv, installed all requirements
2. Installed missing `email-validator` package (needed by `EmailStr`)
3. Installed missing `greenlet` package (needed by `conn.run_sync`)
4. Created `.env` with local Postgres user (`sidharthsaini`, no password)
5. Created `customer_db` database via `createdb`
6. Updated `requirements.txt` to include both new deps
7. Verified app running — health check, POST /customers, GET /customers all working

---

## Prompt 15: .gitignore and Health Check

**User:**
> Add a .gitignore file — Python stuff like pycache, .pyc, venv, .env etc. Also add .idea and .vscode folders. Also add a health check endpoint at GET / that returns {"status": "ok"} in main.py.

**Response:**
- Created `.gitignore` with Python, venv, .env, IDE ignores
- Added `GET /` health check returning `{"status": "ok"}` in `main.py`

---

## Prompt 16: Dockerfile and Docker Compose

**User:**
> Write a Dockerfile — multi-stage build, python:3.11-slim base, non-root user. Also docker-compose.yml with api + postgres 15 services. Named volume for postgres persistence. API depends on postgres. Env from .env file. Expose port 8000.

**Response:**
- `Dockerfile` — two-stage: builder installs deps with `--prefix`, runtime copies them, runs as `appuser`
- `docker-compose.yml` — `postgres` service with `${POSTGRES_*}` env vars and `pgdata` volume, `api` service depending on postgres
- Updated `.env.example` with `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`

---

## Prompt 17: Docker Connectivity Check

**User:**
> Check that everything connects properly — DATABASE_URL should use postgres service name as hostname, POSTGRES vars should match the connection string.

**Response:**
Verified all values align:
- `DATABASE_URL` host = `postgres` (service name) ✅
- User/password/db all match between connection string and `POSTGRES_*` vars ✅

---

## Prompt 18: Docker Compose Up

**User:**
> Run docker-compose up --build and see if it works. I want to hit localhost:8000/docs and see swagger UI.

**Response:**
- Initial build failed — corporate proxy (Zscaler) blocked `python:3.11-slim` pull
- Manually pulled the image with `docker pull python:3.11-slim`
- Re-ran `docker compose up --build` — both containers started
- Verified: health check 200, Swagger UI 200, POST /customers working with Docker DB

---

## Prompt 19: README

**User:**
> Write a README.md — what the project is, tech stack, how to run (docker-compose up --build), API endpoints, mention swagger docs at /docs. Keep it short and to the point.

**Response:**
Created `README.md` with project overview, tech stack, getting started (3 commands), endpoint table, swagger docs link, env vars section.

---

## Prompt 20: Full Code Review

**User:**
> Do a full review of the entire codebase. Check: (1) layer separation, (2) async/await correctness, (3) session lifecycle, (4) exception coverage, (5) security, (6) type hints, (7) soft delete leaks, (8) pydantic validation. Give me the review in markdown format as ai-review.md.

**Response:**
Created `ai-review.md` with findings:
- ✅ Layer separation — clean
- ✅ Async/await — correct
- ✅ Session lifecycle — good (noted per-method commits)
- ⚠️ Exceptions — `DatabaseError` never used, no catch-all handler, `IntegrityError` from race conditions unhandled
- ⚠️ Security — unhandled exceptions can leak stack traces in DEBUG mode
- ⚠️ Type hints — missing on `_active_filter()` and `health_check()`
- 🐛 Soft delete bug — DB `unique=True` on email blocks reuse after soft delete, needs partial index
- ⚠️ Validation — empty names accepted, future DOB accepted

---

## Prompt 21: Fix Review Issues

**User:**
> Fix whatever issues you found in the review. If anything was flagged about layer separation, session handling or missing validation go ahead and update those files.

**Response:**
Fixed 6 files:
1. **models/customer.py** — Replaced `unique=True` with partial unique index (`WHERE deleted_at IS NULL`). Changed timestamp columns to `DateTime(timezone=True)` to fix naive/aware mismatch.
2. **exceptions/handlers.py** — Added catch-all `Exception` handler returning generic error (no stack traces).
3. **schemas/customer.py** — Added `min_length=1` on names. Added `date_of_birth` validator rejecting future dates.
4. **dao/customer_dao.py** — Added `IntegrityError` catch in `create()` with rollback + `DuplicateEmailError`. Added return type on `_active_filter()`.
5. **main.py** — Added return type on `health_check()`.
6. **config.py** — Added `extra="ignore"` so Docker's `POSTGRES_*` vars don't cause validation errors.

Verified all fixes with tests:
- Soft delete + email reuse ✅
- Empty name rejected ✅
- Future DOB rejected ✅
- Duplicate email caught ✅
- Clean error responses (no stack traces) ✅
