# -*- coding: utf-8 -*-
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.persona import Persona
from app.models.simulation import Simulation
from app.models.user import User
from app.schemas.simulation import (
    SimulationCreate,
    SimulationListResponse,
    SimulationResponse,
    TurnRequest,
)
from app.services.simulation_engine import generate_feedback, generate_opening, generate_reply

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationResponse, status_code=201)
def create_simulation(
    body: SimulationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = (
        db.query(Persona)
        .filter(Persona.id == body.persona_id, Persona.user_id == current_user.id)
        .first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다.")

    opening = generate_opening(persona.name, persona.profile_json, body.scenario_config)
    turns = [{"role": "assistant", "content": opening}]

    sim = Simulation(
        user_id=current_user.id,
        persona_id=persona.id,
        scenario_type=body.scenario_config.get("type", "free"),
        scenario_config=body.scenario_config,
        turns=turns,
        savepoints=[],
        feedback={},
    )
    db.add(sim)
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/{sim_id}/turn", response_model=SimulationResponse)
def send_turn(
    sim_id: str,
    body: TurnRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim = (
        db.query(Simulation)
        .filter(Simulation.id == sim_id, Simulation.user_id == current_user.id)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")

    persona = db.query(Persona).filter(Persona.id == sim.persona_id).first()

    turns = list(sim.turns)
    turns.append({"role": "user", "content": body.message})

    reply = generate_reply(persona.name, persona.profile_json, sim.scenario_config, turns)
    turns.append({"role": "assistant", "content": reply})

    sim.turns = turns
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/{sim_id}/savepoint", response_model=SimulationResponse, status_code=201)
def create_savepoint(
    sim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim = (
        db.query(Simulation)
        .filter(Simulation.id == sim_id, Simulation.user_id == current_user.id)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")

    savepoints = list(sim.savepoints)
    savepoints.append({
        "id": str(uuid4()),
        "turn_index": len(sim.turns),
        "label": f"세이브포인트 {len(savepoints) + 1}",
        "created_at": datetime.utcnow().isoformat(),
    })
    sim.savepoints = savepoints
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/{sim_id}/restore/{savepoint_id}", response_model=SimulationResponse)
def restore_savepoint(
    sim_id: str,
    savepoint_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim = (
        db.query(Simulation)
        .filter(Simulation.id == sim_id, Simulation.user_id == current_user.id)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")

    sp = next((s for s in sim.savepoints if s["id"] == savepoint_id), None)
    if not sp:
        raise HTTPException(status_code=404, detail="세이브포인트를 찾을 수 없습니다.")

    sim.turns = list(sim.turns)[: sp["turn_index"]]
    db.commit()
    db.refresh(sim)
    return sim


@router.post("/{sim_id}/feedback", response_model=SimulationResponse)
def get_feedback(
    sim_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sim = (
        db.query(Simulation)
        .filter(Simulation.id == sim_id, Simulation.user_id == current_user.id)
        .first()
    )
    if not sim:
        raise HTTPException(status_code=404, detail="시뮬레이션을 찾을 수 없습니다.")

    feedback = generate_feedback(sim.turns)
    sim.feedback = feedback
    db.commit()
    db.refresh(sim)
    return sim


@router.get("", response_model=SimulationListResponse)
def list_simulations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sims = (
        db.query(Simulation)
        .filter(Simulation.user_id == current_user.id)
        .order_by(Simulation.created_at.desc())
        .all()
    )
    return SimulationListResponse(simulations=sims, total=len(sims))
