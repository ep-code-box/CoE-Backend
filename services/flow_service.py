from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session
from fastapi import HTTPException, status
import logging

from core import schemas
from core.database import LangFlow, LangflowToolMapping
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
    Creates a new flow or updates an existing one based on flow_id or endpoint name.
    Saves the flow to the DB and adds/updates its API route.
    """
    flow_body_dict = flow_create_schema.flow_body.model_dump() if hasattr(flow_create_schema.flow_body, 'model_dump') else flow_create_schema.flow_body.dict()
    contexts: list[str] = []
    context_to_groups: Dict[str, Set[Optional[str]]] = {}

    def _record_context(ctx: Optional[str]) -> Optional[str]:
        if ctx is None:
            return None
        cleaned = str(ctx).strip()
        if not cleaned:
            return None
        if cleaned not in contexts:
            contexts.append(cleaned)
        return cleaned

    def _add_mapping(ctx: Optional[str], groups: Optional[List[str]] = None) -> None:
        cleaned_ctx = _record_context(ctx)
        if not cleaned_ctx:
            return
        bucket = context_to_groups.setdefault(cleaned_ctx, set())
        if not groups:
            bucket.add(None)
            return
        for raw in groups:
            name = (raw or "").strip()
            if not name:
                bucket.add(None)
            else:
                bucket.add(name.lower())

    # contexts 필드(복수) 우선, 없으면 단수 context 사용
    try:
        if getattr(flow_create_schema, 'contexts', None):
            contexts = list(
                dict.fromkeys([
                    (c.strip() if isinstance(c, str) else str(c).strip())
                    for c in flow_create_schema.contexts
                    if c and (str(c).strip())
                ])
            )
        elif getattr(flow_create_schema, 'context', None):
            raw = flow_create_schema.context
            if isinstance(raw, list):
                contexts = list(
                    dict.fromkeys([
                        (c.strip() if isinstance(c, str) else str(c).strip())
                        for c in raw
                        if c and (str(c).strip())
                    ])
                )
            else:
                c = (raw.strip() if isinstance(raw, str) else str(raw).strip()) if raw else None
                contexts = [c] if c else []
    except Exception:
        contexts = []

    for ctx in contexts:
        _add_mapping(ctx)

    if getattr(flow_create_schema, "context_groups", None):
        for cfg in flow_create_schema.context_groups:
            try:
                ctx = cfg.context
                groups = cfg.group_names or []
                _add_mapping(ctx, groups)
            except Exception:
                continue

    # Determine upsert strategy: by flow_id first, then by endpoint name
    # 1) If a flow with the given flow_id exists, update it
    db_flow = db.query(LangFlow).filter(LangFlow.flow_id == flow_create_schema.flow_id).first()
    if db_flow:
        logger.info(f"Updating existing flow by flow_id '{flow_create_schema.flow_id}'")
        db_flow.name = flow_create_schema.endpoint
        db_flow.description = flow_create_schema.description
        db_flow.flow_data = flow_body_dict
        db.commit()
        db.refresh(db_flow)
    else:
        # 2) Else if a flow with the same endpoint (name) exists, update it
        existing_by_name = langflow_db_service.get_flow_by_name(db, name=flow_create_schema.endpoint)
        if existing_by_name:
            logger.info(f"Updating existing flow by endpoint '{flow_create_schema.endpoint}'")
            updated = langflow_db_service.update_flow(
                db=db,
                name=flow_create_schema.endpoint,
                flow_data=flow_body_dict,
                description=flow_create_schema.description,
            )
            if not updated:
                raise HTTPException(status_code=404, detail=f"Flow '{flow_create_schema.endpoint}' not found for update.")
            db_flow = updated
        else:
            # 3) Otherwise, create a new flow
            logger.info(f"Creating new flow for endpoint '{flow_create_schema.endpoint}'")
            db_flow = langflow_db_service.create_flow(
                db=db, 
                name=flow_create_schema.endpoint,
                description=flow_create_schema.description,
                flow_data=flow_body_dict,
                flow_id=flow_create_schema.flow_id
            )
            if not db_flow:
                raise HTTPException(status_code=500, detail="Failed to create flow in database.")

    # Upsert context/group mappings if provided
    if context_to_groups:
        existing = db.query(LangflowToolMapping).filter(
            LangflowToolMapping.flow_id == db_flow.flow_id
        ).all()

        existing_pairs: Set[tuple[str, Optional[str]]] = {
            (m.context, m.group_name or None) for m in existing
        }

        desired_pairs: Set[tuple[str, Optional[str]]] = set()
        for ctx, groups in context_to_groups.items():
            if not groups:
                desired_pairs.add((ctx, None))
                continue
            for grp in groups:
                desired_pairs.add((ctx, grp))

        # add new mappings
        for ctx, grp in desired_pairs - existing_pairs:
            db.add(
                LangflowToolMapping(
                    flow_id=db_flow.flow_id,
                    context=ctx,
                    group_name=grp if grp is not None else None,
                    description=db_flow.description,
                )
            )

        # remove stale mappings
        for ctx, grp in existing_pairs - desired_pairs:
            query = db.query(LangflowToolMapping).filter(
                LangflowToolMapping.flow_id == db_flow.flow_id,
                LangflowToolMapping.context == ctx,
            )
            if grp is None:
                query = query.filter(LangflowToolMapping.group_name.is_(None))
            else:
                query = query.filter(LangflowToolMapping.group_name == grp)
            query.delete()

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

    # 2. (Deprecated) No separate tool mapping to remove
        
    # 3. Convert to schema for response
    flow_read_schema = schemas.FlowRead.from_orm(db_flow)
    
    # 4. Deactivate the route
    router_service.remove_flow_route(flow_read_schema.endpoint)
    
    return flow_read_schema
