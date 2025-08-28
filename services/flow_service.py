from sqlalchemy.orm import Session

from core import schemas
from services.db_service import LangFlowService
from services.flow_router_service import FlowRouterService

# Instantiate the service to use its methods
langflow_db_service = LangFlowService()

def create_and_register_flow(
    db: Session, 
    flow_create_schema: schemas.FlowCreate, 
    router_service: FlowRouterService
) -> schemas.FlowRead:
    """
    Saves the flow to the DB and dynamically adds its API route.
    """
    # 1. Save to DB using the refactored service
    flow_body_dict = flow_create_schema.flow_body.model_dump() if hasattr(flow_create_schema.flow_body, 'model_dump') else flow_create_schema.flow_body.dict()

    db_flow = langflow_db_service.create_flow(
        db=db, 
        name=flow_create_schema.endpoint,
        description=flow_create_schema.description,
        flow_data=flow_body_dict,
        flow_id=flow_create_schema.flow_id,
        context=flow_create_schema.context  # Add context to the flow creation
    )
    
    if not db_flow:
        return None

    # 2. Convert DB model to API schema
    flow_read_schema = schemas.FlowRead.from_orm(db_flow)
    
    # 3. Dynamically add the route
    router_service.add_flow_route(flow_read_schema)
    
    return flow_read_schema

def delete_and_unregister_flow(
    db: Session, 
    flow_id: int, 
    router_service: FlowRouterService
) -> schemas.FlowRead | None:
    """
    Deletes (soft) the flow from the DB and deactivates its API route.
    """
    # 1. Delete from DB using the refactored service
    db_flow = langflow_db_service.delete_flow_by_id(db=db, flow_id=flow_id)
    
    if not db_flow:
        return None

    # 2. Convert to schema for response
    flow_read_schema = schemas.FlowRead.from_orm(db_flow)
    
    # 3. Deactivate the route
    router_service.remove_flow_route(flow_read_schema.endpoint)
    
    return flow_read_schema
