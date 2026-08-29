from pydantic import BaseModel
from datetime import datetime


class HealthCheckResponse(BaseModel):
    message: str
    date_time: datetime
