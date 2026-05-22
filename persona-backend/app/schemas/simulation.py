# -*- coding: utf-8 -*-
from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel


class SimulationCreate(BaseModel):
    persona_id: str
    scenario_config: Dict[str, Any]


class TurnRequest(BaseModel):
    message: str


class SimulationResponse(BaseModel):
    id: str
    persona_id: str
    scenario_type: str
    scenario_config: dict
    turns: list
    savepoints: list
    feedback: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class SimulationListResponse(BaseModel):
    simulations: List[SimulationResponse]
    total: int
