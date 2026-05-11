from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from core import schemas
from core.database import get_db
from services.flow_service import *
from services.flow_router_service import FlowRouterService
from services.db_langflow_service import LangFlowService

# Dependency to get the router service from the app state
def get_flow_router_service(request: Request) -> FlowRouterService:
    return request.app.state.flow_router_service

router = APIRouter(
    prefix="/flows",
    tags=["⚙️ Flows"],
)

# Support both "/flows" and "/flows/" to avoid redirect issues
@router.post("", response_model=schemas.FlowRead, status_code=status.HTTP_201_CREATED)
@router.post("/", response_model=schemas.FlowRead, status_code=status.HTTP_201_CREATED)
def create_or_update_flow(
    flow: schemas.FlowCreate, 
    db: Session = Depends(get_db),
    router_service: FlowRouterService = Depends(get_flow_router_service)
):
    """
    Create a new LangFlow or update an existing one.
    - If a `flow_id` exists, updates that flow.
    - Else if an `endpoint` name exists, updates that flow.
    - Otherwise, creates a new flow.
    - If `context` or `contexts` is provided, updates mapping table to expose the flow only to those fronts.
    """
    return upsert_flow(
        db=db,
        flow_create_schema=flow,
        router_service=router_service,
    )

@router.get("", response_model=List[schemas.FlowRead])
@router.get("/", response_model=List[schemas.FlowRead])
def read_all_flows(
    db: Session = Depends(get_db)
):
    """
    Retrieve all registered LangFlows from the database.
    """
    # This endpoint doesn't need to change, it just reads from the DB.
    flows = LangFlowService.get_all_flows(db)
    return flows


@router.get("/{id}", response_model=schemas.FlowRead)
def read_flow_by_id(
    id: int,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific LangFlow by its ID.
    """
    flow = LangFlowService.get_flow_by_id(
        db=db, 
        id=id,
    )
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with ID {id} not found."
        )
    return flow


@router.get("/langflow/{flow_id}", response_model=schemas.FlowRead)
def read_flow_by_flow_id(
    flow_id: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific LangFlow by its flow_id.
    """
    flow = LangFlowService.get_flow_by_flow_id(
        db=db, 
        flow_id=flow_id,
    )
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with flow_id {flow_id} not found."
        )
    return flow


@router.get("/endpoint/{name}", response_model=schemas.FlowRead)
def read_flow_by_endpoint(
    name: str,
    db: Session = Depends(get_db)
):
    """
    Retrieve a specific LangFlow by its endpoint name.
    """
    flow = LangFlowService.get_flows_by_endpoint(
        db=db, 
        name=name,
    )
    if flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with endpoint '{name}' not found."
        )
    return flow

@router.delete("/langflow/{flow_id}", response_model=schemas.FlowRead)
def remove_flow_by_flow_id(
    flow_id: str,
    db: Session = Depends(get_db),
    router_service: FlowRouterService = Depends(get_flow_router_service)
):
    """
    Delete a registered LangFlow by its flow_id (Langflow) and deactivate its dynamic endpoint.
    """
    deleted_flow = delete_and_unregister_flow_by_flow_id(
        db=db,
        flow_id=flow_id,
        router_service=router_service,
    )
    
    if deleted_flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with Flow ID {flow_id} not found."
        )
        
    return deleted_flow


@router.delete("/{id}", response_model=schemas.FlowRead)
def remove_flow_by_id(
    id: int,
    db: Session = Depends(get_db),
    router_service: FlowRouterService = Depends(get_flow_router_service)
):
    """
    Delete a registered LangFlow by its ID and deactivate its dynamic endpoint.
    """
    deleted_flow = delete_and_unregister_flow_by_id(
        db=db,
        id=id,
        router_service=router_service,
    )
    
    if deleted_flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with ID {id} not found."
        )
        
    return deleted_flow
