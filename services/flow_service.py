from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from core import schemas
from core.database import LangflowToolMapping
from services.db_langflow_service import LangFlowService
from services.flow_router_service import FlowRouterService

# Instantiate the service to use its methods
langflow_db_service = LangFlowService()

def create_and_register_flow(
    db: Session, 
    flow_create_schema: schemas.FlowCreate, 
    router_service: FlowRouterService
) -> schemas.FlowRead:
    """
    Saves the flow to the DB, creates a tool mapping if a front_tool_name is provided,
    and dynamically adds its API route.
    """
    # 1. Save to DB using the refactored service
    flow_body_dict = flow_create_schema.flow_body.model_dump() if hasattr(flow_create_schema.flow_body, 'model_dump') else flow_create_schema.flow_body.dict()

    db_flow = langflow_db_service.create_flow(
        db=db, 
        name=flow_create_schema.endpoint,
        description=flow_create_schema.description,
        flow_data=flow_body_dict,
        flow_id=flow_create_schema.flow_id
    )
    
    if not db_flow:
        return None

    # 2. Create tool mapping if front_tool_name is provided
    if flow_create_schema.front_tool_name:
        existing_mapping = db.query(LangflowToolMapping).filter(LangflowToolMapping.front_tool_name == flow_create_schema.front_tool_name).first()
        if existing_mapping:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Tool name '{flow_create_schema.front_tool_name}' is already registered."
            )
        
        tool_mapping = LangflowToolMapping(
            flow_id=db_flow.flow_id,
            front_tool_name=flow_create_schema.front_tool_name,
            description=flow_create_schema.description
        )
        db.add(tool_mapping)
        db.commit()

    # 3. Convert DB model to API schema
    flow_read_schema = schemas.FlowRead.from_orm(db_flow)
    
    # 4. Dynamically add the route
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
