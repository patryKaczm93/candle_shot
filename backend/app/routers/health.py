from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db import get_db

router = APIRouter()


class HealthOut(BaseModel):
    status: str


@router.get("/health")
def health(db: Annotated[Session, Depends(get_db)]) -> HealthOut:
    try:
        db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=503, detail="Baza danych niedostępna") from exc
    return HealthOut(status="ok")
