# backend/app/core/errors.py
from __future__ import annotations
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ValidationError)
    async def pydantic_validation_handler(request: Request, exc: ValidationError):
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    try:
        from bson.errors import InvalidId  # type: ignore
    except Exception:
        InvalidId = Exception  # fallback

    @app.exception_handler(InvalidId)
    async def bson_invalid_id_handler(request: Request, exc: Exception):
        return JSONResponse(status_code=400, content={"detail": "Invalid object id"})

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    @app.exception_handler(Exception)
    async def unhandled_handler(request: Request, exc: Exception):
        # Last resort to avoid HTML tracebacks
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
