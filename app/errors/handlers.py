from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.errors.python_exceptions import (
    CarIsAlreadyParkedException,
    CarIsNotParkedException,
    CarNotFoundException,
)
from app.errors.schemas import ErrorResponse


def build_error_response(error: str, message: str, status_code: int) -> JSONResponse:
    payload = ErrorResponse(error=error, message=message)
    return JSONResponse(status_code=status_code, content=payload.model_dump())


async def car_not_found_handler(request: Request, exc: Exception) -> JSONResponse:
    return build_error_response(
        error="car_not_found",
        message=str(exc),
        status_code=status.HTTP_404_NOT_FOUND,
    )


async def car_allready_parked_handler(request: Request, exc: Exception) -> JSONResponse:
    return build_error_response(
        error="car_allready_parked",
        message=str(exc),
        status_code=status.HTTP_409_CONFLICT,
    )


async def car_is_not_parked_handler(request: Request, exc: Exception) -> JSONResponse:
    return build_error_response(
        error="car_is_not_parked",
        message=str(exc),
        status_code=status.HTTP_400_BAD_REQUEST,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(CarNotFoundException, car_not_found_handler)
    app.add_exception_handler(CarIsAlreadyParkedException, car_allready_parked_handler)
    app.add_exception_handler(CarIsNotParkedException, car_is_not_parked_handler)
