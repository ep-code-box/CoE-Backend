from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from core import schemas
from core.database import get_db
from services import flow_service
from services.flow_router_service import FlowRouterService
from services.db_langflow_service import LangFlowService

# Dependency to get the router service from the app state
def get_flow_router_service(request: Request) -> FlowRouterService:
    return request.app.state.flow_router_service

router = APIRouter(
    prefix="/flows",
    tags=["Flows Management"],
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
    return flow_service.upsert_flow(
        db=db, flow_create_schema=flow, router_service=router_service
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

@router.delete("/{flow_id}", response_model=schemas.FlowRead)
def remove_flow(
    flow_id: int,
    db: Session = Depends(get_db),
    router_service: FlowRouterService = Depends(get_flow_router_service)
):
    """
    Delete a registered LangFlow by its ID and deactivate its dynamic endpoint.
    """
    deleted_flow = flow_service.delete_and_unregister_flow(
        db=db, flow_id=flow_id, router_service=router_service
    )
    
    if deleted_flow is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flow with ID {flow_id} not found."
        )
        
    return deleted_flow
