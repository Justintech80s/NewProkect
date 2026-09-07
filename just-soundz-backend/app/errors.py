from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .request_context import normalize_request_id


class AppError(Exception):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int,
        retryable: bool = False,
    ):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retryable = retryable


def error_payload(
    code: str,
    message: str,
    request_id: str,
    retryable: bool,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "retryable": retryable,
        }
    }


def _request_id(request: Request) -> str:
    return normalize_request_id(getattr(request.state, "request_id", None))


def _http_code(status_code: int) -> str:
    return {
        400: "bad_request",
        401: "authentication_required",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        429: "quota_exceeded",
        501: "not_implemented",
        503: "service_unavailable",
    }.get(status_code, "http_error")


def _safe_http_message(exc: StarletteHTTPException) -> str:
    if exc.status_code >= 500:
        return "The service is temporarily unavailable."
    if isinstance(exc.detail, str):
        return exc.detail
    if exc.status_code == 429:
        return "Generation quota exceeded."
    return "The request could not be completed."


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                exc.code,
                exc.message,
                _request_id(request),
                exc.retryable,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content=error_payload(
                "validation_error",
                "The request contains invalid input.",
                _request_id(request),
                False,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_http_error(request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=error_payload(
                _http_code(exc.status_code),
                _safe_http_message(exc),
                _request_id(request),
                exc.status_code in {429, 503},
            ),
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content=error_payload(
                "internal_error",
                "An unexpected server error occurred.",
                _request_id(request),
                True,
            ),
        )
