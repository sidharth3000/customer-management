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

---

## Prompt 22: Test Setup — conftest.py and Dependencies

**User:**
> I need to add tests for my project. Set up a tests folder with conftest.py. I need a test database setup — create an async test session that uses a separate test database (not the main one). Use pytest and pytest-asyncio. Add all testing dependencies to requirements.txt — pytest, pytest-asyncio, httpx for testing FastAPI endpoints. Keep the conftest simple, I need a fixture that gives me a clean database for each test — create tables before and drop after.

**Response:**
Created test infrastructure:
- `tests/__init__.py` — package init
- `tests/conftest.py` — test database setup with `TEST_DATABASE_URL` derived from main URL (appends `_test`), `NullPool` engine, two fixtures:
  - `db_session` — creates tables before each test, yields `AsyncSession`, drops tables after
  - `client` — overrides `get_db` with test session, yields `httpx.AsyncClient`, clears overrides after
- `pytest.ini` — `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = function`
- Updated `requirements.txt` — added pytest==8.3.5, pytest-asyncio==0.25.3, httpx==0.28.1

---

## Prompt 23: Plan DAO Test Cases

**User:**
> Before writing any tests, tell me what test cases you think we should cover for the CustomerDAO. List them out so I can review before we write anything.

**Response:**
Proposed 20 test cases grouped by method:
- **create** (3): success, duplicate email raises, duplicate allowed after soft-delete
- **get_by_id** (3): found, nonexistent, soft-deleted
- **get_by_email** (3): found, nonexistent, soft-deleted
- **get_all** (4): all active, excludes deleted, pagination, empty
- **update** (4): success, nonexistent, soft-deleted, duplicate email
- **soft_delete** (3): success, nonexistent, already deleted

---

## Prompt 24: Write DAO Tests

**User:**
> Looks good but also add a case for soft delete — after soft deleting a customer both get_by_id and get_all should not return that customer. Go ahead and write all the tests in tests/test_customer_dao.py. Use a helper function to generate sample customer data so we don't repeat the same dict everywhere.

**Response:**
Created `tests/test_customer_dao.py` with 21 tests:
- `sample_customer_data(**overrides)` helper returning default customer dict
- All 20 planned cases plus the extra `test_soft_delete_excludes_from_get_by_id_and_get_all`

---

## Prompt 25: Confirm Test Session Usage

**User:**
> The tests need to use the test session from conftest not the real db session. Make sure each test creates the dao with the test async session fixture.

**Response:**
Confirmed tests already use the `db_session` fixture from conftest, which yields sessions from `TestSessionLocal` backed by `TEST_DATABASE_URL`. No changes needed.

---

## Prompt 26: Plan Service Test Cases

**User:**
> Same thing for the service layer — what test cases should we cover for CustomerService? List them out.

**Response:**
Proposed 13 test cases:
- **create_customer** (2): success, duplicate email raises
- **get_customer** (2): found, not found raises
- **get_all_customers** (2): returns list, empty
- **update_customer** (5): success, duplicate email raises, own email allowed, not found raises, partial update preserves fields
- **delete_customer** (2): success, not found raises

---

## Prompt 27: Write Service Tests

**User:**
> Yeah those cover it. Also make sure there's a case for updating email to one that another customer already has — should raise duplicate error. Write them in tests/test_customer_service.py.

**Response:**
Created `tests/test_customer_service.py` with 13 tests:
- `make_create_data(**overrides)` helper returning `CustomerCreate` schema
- `make_service(db_session)` helper building the full `CustomerService → CustomerDAO → session` chain
- All planned cases including duplicate email on update

---

## Prompt 28: Plan Router Test Cases

**User:**
> Now list out test cases for the API endpoints. Think about both happy path and error cases — invalid data, missing fields, not found, duplicate email etc.

**Response:**
Proposed 22 test cases:
- **POST /customers** (8): valid, optional fields omitted, duplicate email 409, missing field 422, invalid email 422, credit score too low/high 422, future DOB 422
- **GET /customers** (3): list, empty, pagination
- **GET /customers/{id}** (3): found, not found 404, invalid UUID 422
- **PUT /customers/{id}** (5): success, partial, duplicate email 409, not found 404, invalid credit score 422
- **DELETE /customers/{id}** (3): success 204, not found 404, deleted not retrievable

---

## Prompt 29: Write Router Tests

**User:**
> Good list. Write them in tests/test_customer_router.py using httpx AsyncClient. One thing — the client needs to use our test database not the real one so we'll need to override the get_db dependency.

**Response:**
Created `tests/test_customer_router.py` with 22 tests:
- `sample_payload(**overrides)` helper returning JSON-serializable dict
- `_create_customer(client, **overrides)` helper for quick setup
- All tests use the `client` fixture from conftest which already overrides `get_db`

---

## Prompt 30: Confirm Client Fixture Exists

**User:**
> Add a fixture in conftest.py for the async httpx client that overrides get_db with our test session. Make sure dependency override is cleaned up after tests are done.

**Response:**
Confirmed the `client` fixture already exists in conftest.py (lines 37-53). It overrides `get_db`, yields the `AsyncClient`, and calls `app.dependency_overrides.clear()` on cleanup.

---

## Prompt 31: Run Tests and Fix Failures

**User:**
> Run pytest -v and check if everything passes. Fix whatever fails.

**Response:**
Fixed three issues:
1. **conftest.py** — `DATABASE_URL` used Docker hostname `postgres` which doesn't resolve locally. Added `.replace("@postgres:", "@localhost:")` and `NullPool` to prevent connection pool issues across event loops.
2. **pytest.ini** — Added `asyncio_default_fixture_loop_scope = function` to suppress deprecation warning.
3. **customer_dao.py** — `update()` method was missing `IntegrityError` handling. Added `try/except IntegrityError` with rollback and `DuplicateEmailError`, matching the pattern in `create()`.

Result: **56 tests passed**.

---

## Prompt 32: Add Coverage

**User:**
> Add pytest-cov to requirements.txt. Configure pytest in pyproject.toml to run coverage on the app folder automatically, show missing lines in terminal, and also generate an HTML report. Set minimum coverage to 80% so tests fail if it drops below that.

**Response:**
- Added `pytest-cov==6.1.1` to `requirements.txt`
- Created `pyproject.toml` with pytest and coverage config:
  - `addopts = "--cov=app --cov-report=term-missing --cov-report=html --cov-fail-under=80"`
  - `exclude_lines = ["if __name__"]`
- Deleted `pytest.ini` (settings moved to `pyproject.toml`)
- Result: 56 tests, 93.85% coverage

---

## Prompt 33: Coverage Gaps

**User:**
> Run pytest with coverage and show me the report. If anything is below 80% tell me what's not covered and add tests for those.

**Response:**
Two files were below 80%:
- `database.py` (60%) — `get_db()` body never executed (overridden in tests)
- `main.py` (73%) — lifespan and health check uncovered

Added:
- `tests/test_database.py` — tests real `get_db` yields and closes a session
- `tests/test_main.py` — tests health check endpoint and lifespan (patched to use test engine)
- `pyproject.toml` — added `exclude_lines = ["if __name__"]` for the `__main__` guard

Result: **59 tests passed, 97.93% coverage**, all files above 80%.

---

## Prompt 34: Add Test Descriptions

**User:**
> Add small description above every test case so in future if any test fails we know what went wrong.

**Response:**
Added docstrings to all 59 tests across 5 files:
- `test_customer_dao.py` — 21 tests
- `test_customer_service.py` — 13 tests
- `test_customer_router.py` — 22 tests
- `test_main.py` — 2 tests
- `test_database.py` — 1 test

Each docstring describes what the test verifies (e.g., "Should raise DuplicateEmailError when email is already taken by an active customer"). All 59 tests still passing, 97.93% coverage.
