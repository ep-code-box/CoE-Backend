from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging

from core import schemas
from core.database import LangflowToolMapping, LangFlow
from services.db_langflow_service import LangFlowService
from services.flow_router_service import FlowRouterService

# Instantiate the service to use its methods
langflow_db_service = LangFlowService()
logger = logging.getLogger(__name__)

def upsert_flow(
    db: Session, 
    flow_create_schema: schemas.FlowCreate, 
    router_service: FlowRouterService
) -> schemas.FlowRead:
    """
    Creates a new flow or updates an existing one based on front_tool_name.
    Saves the flow to the DB, creates/updates a tool mapping, and adds/updates its API route.
    """
    flow_body_dict = flow_create_schema.flow_body.model_dump() if hasattr(flow_create_schema.flow_body, 'model_dump') else flow_create_schema.flow_body.dict()

    # Check for existing mapping by front_tool_name
    existing_mapping = None
    if flow_create_schema.front_tool_name:
        existing_mapping = db.query(LangflowToolMapping).filter(LangflowToolMapping.front_tool_name == flow_create_schema.front_tool_name).first()

    if existing_mapping:
        # --- UPDATE ---
        logger.info(f"Updating existing flow for context '{flow_create_schema.front_tool_name}'")
        db_flow = db.query(LangFlow).filter(LangFlow.flow_id == existing_mapping.flow_id).first()
        if not db_flow:
            # This case should ideally not happen if DB is consistent
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Flow with ID {existing_mapping.flow_id} linked to tool '{flow_create_schema.front_tool_name}' not found."
            )
        
        # Update flow details
        db_flow.name = flow_create_schema.endpoint
        db_flow.description = flow_create_schema.description
        db_flow.flow_data = flow_body_dict
        
        # Update mapping description
        existing_mapping.description = flow_create_schema.description
        
        db.commit()
        db.refresh(db_flow)
        
    else:
        # --- CREATE ---
        logger.info(f"Creating new flow for endpoint '{flow_create_schema.endpoint}'")
        # Check for duplicate endpoint name on create
        db_flow_by_name = langflow_db_service.get_flow_by_name(db, name=flow_create_schema.endpoint)
        if db_flow_by_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Endpoint '{flow_create_schema.endpoint}' already registered. Use a different endpoint name for new flows."
            )

        db_flow = langflow_db_service.create_flow(
            db=db, 
            name=flow_create_schema.endpoint,
            description=flow_create_schema.description,
            flow_data=flow_body_dict,
            flow_id=flow_create_schema.flow_id
        )
        
        if not db_flow:
            # create_flow should raise an error, but as a safeguard:
            raise HTTPException(status_code=500, detail="Failed to create flow in database.")

        # Create tool mapping if front_tool_name is provided
        if flow_create_schema.front_tool_name:
            tool_mapping = LangflowToolMapping(
                flow_id=db_flow.flow_id,
                front_tool_name=flow_create_schema.front_tool_name,
                description=flow_create_schema.description
            )
            db.add(tool_mapping)
            db.commit()

    # Convert DB model to API schema
    flow_read_schema = schemas.FlowRead.from_orm(db_flow)
    
    # Add or update the route
    router_service.add_flow_route(flow_read_schema)
    
    return flow_read_schema


def delete_and_unregister_flow(
    db: Session, 
    flow_id: int, 
    router_service: FlowRouterService
) -> schemas.FlowRead | None:
    """
    Deletes (soft) the flow from the DB, deactivates its API route, and removes the tool mapping.
    """
    # 1. Delete from DB using the refactored service
    db_flow = langflow_db_service.delete_flow_by_id(db=db, flow_id=flow_id)
    
    if not db_flow:
        return None

    # 2. Remove the corresponding tool mapping
    db.query(LangflowToolMapping).filter(LangflowToolMapping.flow_id == db_flow.flow_id).delete()
    db.commit()
        
    # 3. Convert to schema for response
    flow_read_schema = schemas.FlowRead.from_orm(db_flow)
    
    # 4. Deactivate the route
    router_service.remove_flow_route(flow_read_schema.endpoint)
    
    return flow_read_schema