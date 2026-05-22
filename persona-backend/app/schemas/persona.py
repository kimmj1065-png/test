from datetime import datetime
from typing import List

from pydantic import BaseModel


class PersonaResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str
    profile_json: dict
    message_count: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonaListResponse(BaseModel):
    personas: List[PersonaResponse]
    total: int
