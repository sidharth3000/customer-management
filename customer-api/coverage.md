# Test Coverage Report

**Total Coverage: 97.93%** (minimum threshold: 80%)

**59 tests passed** across 5 test files.

## Coverage by File

| File | Statements | Missed | Coverage | Missing Lines |
|---|---|---|---|---|
| app\config.py | 8 | 0 | 100% | — |
| app\dao\__init__.py | 0 | 0 | 100% | — |
| app\dao\customer_dao.py | 48 | 1 | 98% | 63 |
| app\database.py | 10 | 0 | 100% | — |
| app\exceptions\__init__.py | 0 | 0 | 100% | — |
| app\exceptions\handlers.py | 27 | 1 | 96% | 44 |
| app\main.py | 20 | 0 | 100% | — |
| app\models\__init__.py | 0 | 0 | 100% | — |
| app\models\customer.py | 25 | 0 | 100% | — |
| app\routers\__init__.py | 0 | 0 | 100% | — |
| app\routers\customer_router.py | 25 | 0 | 100% | — |
| app\schemas\__init__.py | 0 | 0 | 100% | — |
| app\schemas\customer.py | 46 | 3 | 93% | 40-42 |
| app\services\__init__.py | 0 | 0 | 100% | — |
| app\services\customer_service.py | 33 | 0 | 100% | — |
| **TOTAL** | **242** | **5** | **98%** | |

## Uncovered Lines

| File | Lines | Reason |
|---|---|---|
| customer_dao.py | 63 | `IntegrityError` catch in `soft_delete` — unreachable in practice since soft delete doesn't violate constraints |
| handlers.py | 44 | Generic `Exception` catch-all handler — only triggered by unexpected server errors |
| customer.py (schemas) | 40-42 | `CustomerUpdate.dob_not_in_future` validator — not exercised because no update test sends a future DOB |

## Test Breakdown

| Test File | Tests | Layer |
|---|---|---|
| test_customer_dao.py | 21 | Data access (direct DB operations) |
| test_customer_service.py | 13 | Business logic (service layer) |
| test_customer_router.py | 22 | API endpoints (HTTP level) |
| test_main.py | 2 | App startup (health check, lifespan) |
| test_database.py | 1 | Database session factory |

## Configuration

Coverage is configured in `pyproject.toml`:
- Runs automatically on `pytest` via `addopts`
- Reports: terminal with missing lines + HTML (`htmlcov/`)
- Minimum threshold: 80% (tests fail if coverage drops below)
- Excludes: `if __name__` guards
