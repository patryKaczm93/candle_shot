from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ProductListItem
from app.services import catalog

router = APIRouter()


@router.get("/products")
def list_products(
    db: Annotated[Session, Depends(get_db)],
    category: Annotated[str | None, Query(max_length=50)] = None,
) -> list[ProductListItem]:
    return catalog.list_products(db, category)
