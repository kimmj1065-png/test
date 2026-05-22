# -*- coding: utf-8 -*-
from typing import List

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.deps import get_current_user
from app.database import get_db
from app.models.persona import Persona
from app.models.user import User
from app.schemas.persona import PersonaListResponse, PersonaResponse
from app.services.kakao_parser import (
    extract_speakers,
    filter_by_sender,
    parse_kakao_export,
)

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("/upload", response_model=List[PersonaResponse], status_code=201)
async def upload_kakao_file(
    file: UploadFile = File(...),
    my_name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    content = (await file.read()).decode("utf-8")
    messages = parse_kakao_export(content)

    if not messages:
        raise HTTPException(status_code=400, detail="파싱 가능한 메시지가 없습니다.")

    speakers = extract_speakers(messages)
    if my_name not in speakers:
        raise HTTPException(status_code=400, detail=f"'{my_name}' 발화자를 찾을 수 없습니다.")

    created_personas = []

    my_messages = filter_by_sender(messages, my_name)
    self_persona = Persona(
        user_id=current_user.id,
        name=my_name,
        type="self",
        message_count=len(my_messages),
        profile_json={},
    )
    db.add(self_persona)
    created_personas.append(self_persona)

    for speaker in speakers:
        if speaker == my_name:
            continue
        their_messages = filter_by_sender(messages, speaker)
        acquaintance_persona = Persona(
            user_id=current_user.id,
            name=speaker,
            type="acquaintance",
            message_count=len(their_messages),
            profile_json={},
        )
        db.add(acquaintance_persona)
        created_personas.append(acquaintance_persona)

    db.commit()
    for p in created_personas:
        db.refresh(p)

    return created_personas


@router.get("", response_model=PersonaListResponse)
def list_personas(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    personas = (
        db.query(Persona)
        .filter(Persona.user_id == current_user.id, Persona.status == "active")
        .all()
    )
    return PersonaListResponse(personas=personas, total=len(personas))


@router.get("/{persona_id}", response_model=PersonaResponse)
def get_persona(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = (
        db.query(Persona)
        .filter(Persona.id == persona_id, Persona.user_id == current_user.id)
        .first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다.")
    return persona


@router.delete("/{persona_id}", status_code=204)
def delete_persona(
    persona_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    persona = (
        db.query(Persona)
        .filter(Persona.id == persona_id, Persona.user_id == current_user.id)
        .first()
    )
    if not persona:
        raise HTTPException(status_code=404, detail="페르소나를 찾을 수 없습니다.")
    db.delete(persona)
    db.commit()
