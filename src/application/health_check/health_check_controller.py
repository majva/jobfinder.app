from datetime import datetime

from fastapi import APIRouter, status

from src.application.health_check.dtos.health_check_dto import HealthCheckResponse
from src.infrastructure.di.inject import inject
from src.infrastructure.utils.config_reader import ConfigReader


@inject
class HealthCheckController:

    def __init__(self, config_reader: ConfigReader):
        self._config = config_reader

    def api(self):
        router = APIRouter(
            prefix="",
            tags=["Health Check"],
            responses={404: {"description": "Not found"}},
        )

        @router.get(
            "/version",
            response_model=HealthCheckResponse,
            status_code=status.HTTP_200_OK,
            summary="Get service version",
        )
        async def health_check() -> HealthCheckResponse:
            version = self._config.get_app_version()
            return HealthCheckResponse(
                message=f"version: {version}",
                date_time=datetime.now(),
            )

        return router
