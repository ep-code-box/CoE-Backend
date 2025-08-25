from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from core import schemas
from core.database import get_db
from services import flow_service
from services.flow_router_service import FlowRouterService
from services.db_service import LangFlowService

# Dependency to get the router service from the app state
def get_flow_router_service(request: Request) -> FlowRouterService:
    return request.app.state.flow_router_service

router = APIRouter(
    prefix="/flows",
    tags=["Flows Management"],
)

@router.post("/", response_model=schemas.FlowRead, status_code=status.HTTP_201_CREATED)
def create_new_flow(
    flow: schemas.FlowCreate, 
    db: Session = Depends(get_db),
    router_service: FlowRouterService = Depends(get_flow_router_service)
):
    """
    Register a new LangFlow, save it to the database, and dynamically expose its endpoint.
    """
    db_flow = LangFlowService.get_flow_by_name(db, name=flow.endpoint)
    if db_flow:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Endpoint '{flow.endpoint}' already registered."
        )
    
    return flow_service.create_and_register_flow(
        db=db, flow_create_schema=flow, router_service=router_service
    )

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
