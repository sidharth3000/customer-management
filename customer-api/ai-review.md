# AI Code Review — Customer Management API

**Reviewed:** April 3, 2026
**Files reviewed:** All files under `customer-api/app/`, `Dockerfile`, `docker-compose.yml`, `requirements.txt`

---

## 1. Layer Separation (DAO ↔ Service)

**Verdict: Clean** ✅

- **DAO** — contains only SQLAlchemy queries, no business decisions. The `_active_filter()` helper and `datetime.now(timezone.utc)` in `soft_delete` are data-layer concerns, not business logic. Good.
- **Service** — has zero SQLAlchemy imports, never touches the session. All DB interaction goes through `self.dao`. Good.
- **Router** — thin HTTP glue, no logic beyond calling service methods. Good.

**No issues found.**

---

## 2. Async/Await Correctness

**Verdict: Clean** ✅

- All DB operations (`execute`, `commit`, `refresh`, `close`) are properly `await`ed.
- `_active_filter()` is a sync helper that just builds a SQLAlchemy clause — doesn't need `async`. Correct.
- `conn.run_sync(Base.metadata.create_all)` in the lifespan is the proper way to run sync DDL through an async engine.
- No blocking calls (`time.sleep`, sync file I/O, sync HTTP) anywhere.

**No issues found.**

---

## 3. DB Session Lifecycle

**Verdict: Good, one minor note** ✅

- `get_db()` yields the session inside `try/finally` → `session.close()` always runs, even on exceptions. Correct.
- Lifespan calls `engine.dispose()` on shutdown → connections are cleaned up. Correct.
- `expire_on_commit=False` is set → ORM attributes are readable after commit without hitting the DB again. Correct.

### ⚠️ Minor: Per-method commits in DAO

Each DAO method (`create`, `update`, `soft_delete`) calls `commit()` independently. This means if a service method ever needs to orchestrate **two writes atomically**, they can't — the first one is already committed. Right now this isn't a problem since each service method does exactly one write. But if you ever add a service method like "transfer customer ownership" that needs two writes, you'd need to move commit responsibility to the service layer or use a unit-of-work pattern.

**Not a bug today, just something to be aware of.**

---

## 4. Custom Exception Coverage

**Verdict: Two gaps** ⚠️

### What's covered:
| Exception             | HTTP | Used where          |
|----------------------|------|---------------------|
| `CustomerNotFoundError` | 404  | service: get, update, delete |
| `DuplicateEmailError`   | 409  | service: create, update      |
| `DatabaseError`          | 500  | **never used**               |

### Gap 1: `DatabaseError` is defined but never raised

No code catches SQLAlchemy exceptions and wraps them in `DatabaseError`. If the DB goes down or a query fails unexpectedly, the user gets FastAPI's default 500 response (which in `DEBUG=True` mode includes a stack trace) instead of your clean `{"detail": "..."}` format.

**Fix:** Add a catch-all for `Exception` in the exception handler:

```python
def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred"},
        )
```

### Gap 2: IntegrityError from race conditions is unhandled

If two requests try to create a customer with the same email simultaneously, both pass the `get_by_email` check, and one of the `INSERT` statements hits the DB unique constraint. This throws `asyncpg.UniqueViolationError` / SQLAlchemy `IntegrityError` — which isn't caught anywhere.

**Fix:** Catch `IntegrityError` in the DAO `create` method or add a handler that maps it to `DuplicateEmailError`.

---

## 5. Security

**Verdict: Solid, one concern** ✅

### What's safe:
- **SQL injection** — impossible. All queries use SQLAlchemy ORM with parameterized statements. No raw SQL. ✅
- **Stack traces** — custom exception handler returns `{"detail": "..."}` only. ✅
- **Non-root Docker** — app runs as `appuser`. ✅
- **No secrets in code** — all config from `.env`. ✅

### ⚠️ Concern: Unhandled exceptions in DEBUG mode

When `DEBUG=True`, FastAPI's default exception handler returns verbose tracebacks for unhandled errors (anything that isn't an `AppException`). This could leak internals like DB connection strings, table names, or file paths.

**Fix:** Same as Gap 1 above — add a catch-all exception handler so nothing unhandled reaches the client.

---

## 6. Type Hints

**Verdict: Two missing** ⚠️

| Location | What's missing |
|----------|---------------|
| `dao/customer_dao.py` → `_active_filter()` | Missing return type. Should be `-> ColumnElement[bool]` (from `sqlalchemy.sql.expression`) |
| `main.py` → `health_check()` | Missing return type. Should be `-> dict[str, str]` |

Everything else is properly typed — DAO, service, schemas, router, config.

---

## 7. Soft Delete Leaks

**Verdict: One real bug** 🐛

### What's protected:
- `get_by_id` — filtered ✅
- `get_by_email` — filtered ✅
- `get_all` — filtered ✅
- `update` — filtered (can't update a deleted customer) ✅
- `soft_delete` — filtered (can't double-delete) ✅

### 🐛 Bug: DB unique constraint conflicts with soft delete

The `Customer` model has `unique=True` on the `email` column:

```python
email: Mapped[str] = mapped_column(String(255), unique=True)
```

This is a **database-level** constraint that applies to **all rows, including soft-deleted ones**.

**Scenario:**
1. Create customer with `email=sid@test.com` → works
2. Soft delete that customer → `deleted_at` is set, row still in DB
3. Create a new customer with `email=sid@test.com` → `get_by_email` returns `None` (correct, filters soft-deleted), but `INSERT` fails with `UniqueViolationError` because the DB still has that email in the table

**Fix:** Replace the simple unique constraint with a partial unique index that only covers active records:

```python
from sqlalchemy import Index

class Customer(Base):
    __tablename__ = "customers"
    # ... fields ...

    __table_args__ = (
        Index("uq_customers_email_active", "email", unique=True, postgresql_where=text("deleted_at IS NULL")),
    )
```

And remove `unique=True` from the email `mapped_column`.

---

## 8. Pydantic Validation

**Verdict: Two edge cases** ⚠️

### What's solid:
- `email` — validated via `EmailStr` ✅
- `credit_score` — constrained to 300–850 ✅
- `max_length` on all string fields ✅
- `CustomerUpdate` uses `exclude_unset=True` for partial updates ✅
- `from_attributes = True` on response schema ✅

### Edge Case 1: Empty strings allowed for names

`first_name` and `last_name` accept `""` (empty string). A customer with a blank name would pass validation.

**Fix:** Add `min_length=1`:

```python
first_name: str = Field(min_length=1, max_length=100)
last_name: str = Field(min_length=1, max_length=100)
```

### Edge Case 2: Future dates of birth accepted

`date_of_birth` accepts any date, including tomorrow. No business would have a customer born in 2030.

**Fix (optional):** Add a validator if you care:

```python
from pydantic import field_validator
from datetime import date

@field_validator("date_of_birth")
@classmethod
def dob_not_in_future(cls, v: date) -> date:
    if v > date.today():
        raise ValueError("Date of birth cannot be in the future")
    return v
```

### Edge Case 3: Empty update body

`CustomerUpdate` with `{}` (all fields omitted) is valid — `exclude_unset=True` produces an empty dict, and `dao.update` runs `UPDATE customers SET WHERE id = ...` with no columns. This won't error on Postgres but it's a wasted round-trip. Not a bug, just unnecessary.

---

## Summary

| Area | Status | Action needed |
|------|--------|---------------|
| Layer separation | ✅ Clean | None |
| Async/await | ✅ Clean | None |
| Session lifecycle | ✅ Good | Be aware of per-method commits |
| Exception coverage | ⚠️ Gaps | Add catch-all handler, handle IntegrityError |
| Security | ⚠️ One concern | Add catch-all handler to prevent trace leaks |
| Type hints | ⚠️ Two missing | Add return types to `_active_filter` and `health_check` |
| Soft delete leaks | 🐛 Bug | Replace unique constraint with partial index |
| Pydantic validation | ⚠️ Edge cases | Add `min_length=1` for names, optionally validate DOB |

### Priority fixes:
1. **Partial unique index on email** — this is a real bug that will surface in production
2. **Catch-all exception handler** — prevents stack trace leaks and handles DB errors gracefully
3. **`min_length=1` on names** — quick win, prevents bad data
