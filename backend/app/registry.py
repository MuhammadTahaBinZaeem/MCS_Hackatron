from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import select
from app.schema import departments, locations, categories

router = APIRouter(prefix='/api/v1')

class DepartmentDTO(BaseModel):
    code: str
    label: str

class LocationDTO(BaseModel):
    id: str
    parent_id: str | None
    department_id: str | None
    name: str
    demo: bool

class CategoryDTO(BaseModel):
    id: str
    parent_id: str | None
    code: str
    label: str

@router.get('/departments', response_model=list[DepartmentDTO])
def get_departments(request: Request):
    with request.app.state.engine.connect() as conn:
        return [dict(row) for row in conn.execute(select(departments.c.code,departments.c.label).order_by(departments.c.code)).mappings()]

@router.get('/locations', response_model=list[LocationDTO])
def get_locations(request: Request):
    columns = [locations.c.id,locations.c.parent_id,locations.c.department_id,locations.c.name,locations.c.demo]
    with request.app.state.engine.connect() as conn:
        return [dict(row) for row in conn.execute(select(*columns).where(locations.c.active.is_(True)).order_by(locations.c.canonical_path)).mappings()]

@router.get('/categories', response_model=list[CategoryDTO])
def get_categories(request: Request):
    columns = [categories.c.id,categories.c.parent_id,categories.c.code,categories.c.label]
    with request.app.state.engine.connect() as conn:
        return [dict(row) for row in conn.execute(select(*columns).where(categories.c.active.is_(True)).order_by(categories.c.code,categories.c.id)).mappings()]
