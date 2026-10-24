from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas import ProductDetail, ProductListItem
from app.services import catalog

router = APIRouter()


@router.get("/products")
def list_products(
    db: Annotated[Session, Depends(get_db)],
    category: Annotated[str | None, Query(max_length=50)] = None,
) -> list[ProductListItem]:
    return catalog.list_products(db, category)


@router.get("/products/{slug}")
def get_product(
    db: Annotated[Session, Depends(get_db)],
    slug: Annotated[str, Path(max_length=100)],
) -> ProductDetail:
    product = catalog.get_product(db, slug)
    if product is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono produktu")
    return product
