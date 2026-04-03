import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


class AppException(Exception):
    status_code: int = 500
    detail: str = "An unexpected error occurred"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.__class__.detail


class CustomerNotFoundError(AppException):
    status_code = 404
    detail = "Customer not found"

    def __init__(self, customer_id: uuid.UUID | None = None):
        msg = f"Customer with id '{customer_id}' not found" if customer_id else self.__class__.detail
        super().__init__(msg)


class DuplicateEmailError(AppException):
    status_code = 409
    detail = "A customer with this email already exists"


class DatabaseError(AppException):
    status_code = 500
    detail = "A database error occurred"


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
