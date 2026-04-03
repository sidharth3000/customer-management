# Customer Management API

A REST API for managing customers — built with FastAPI, async SQLAlchemy, and PostgreSQL. Runs in Docker.

## Tech Stack

- **FastAPI** — async web framework
- **SQLAlchemy 2.0** — async ORM with asyncpg driver
- **PostgreSQL 15** — database
- **Pydantic v2** — request/response validation
- **Docker & Docker Compose** — containerized setup

## Getting Started

```bash
# clone the repo
cd customer-api

# copy env file and adjust if needed
cp .env.example .env

# start everything
docker compose up --build
```

The API will be available at `http://localhost:8000`.

## API Endpoints

| Method | Endpoint               | Description                        |
|--------|------------------------|------------------------------------|
| GET    | `/`                    | Health check — returns `{"status": "ok"}` |
| POST   | `/customers`           | Create a new customer              |
| GET    | `/customers`           | List all customers (supports `skip` & `limit` query params) |
| GET    | `/customers/{id}`      | Get a single customer by UUID      |
| PUT    | `/customers/{id}`      | Update a customer (partial updates supported) |
| DELETE | `/customers/{id}`      | Soft delete a customer             |

## Swagger Docs

Once the app is running, open [http://localhost:8000/docs](http://localhost:8000/docs) for the interactive Swagger UI.

## Environment Variables

See `.env.example` for all required variables:

- `DATABASE_URL` — async PostgreSQL connection string
- `APP_HOST` / `APP_PORT` — server bind address
- `DEBUG` — enables SQL echo and hot reload
- `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` — used by the Postgres container
