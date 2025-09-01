import asyncio
from sqlalchemy.orm import Session

import asyncio
from sqlalchemy.orm import Session

from services.flow_router_service import FlowRouterService
from services.db_langflow_service import LangFlowService
from core.database import SessionLocal
from core import schemas

# Instantiate the DB service to use its methods
langflow_db_service = LangFlowService()

class SchedulerService:
    """Manages the periodic synchronization of routes from the database."""

    def __init__(self, router_service: FlowRouterService):
        self.router_service = router_service
        self._is_running = False
        self._task: asyncio.Task | None = None

    def sync_routes_from_db(self):
        """Fetches all active flows from DB and ensures they are routed."""
        print("⚙️ Syncing routes from database...")
        db: Session = SessionLocal()
        try:
            # DB에서 모든 활성 flow를 가져옵니다.
            flows_from_db = langflow_db_service.get_all_flows(db)
            active_flows_in_db = {schemas.FlowRead.from_orm(flow).endpoint for flow in flows_from_db if flow.is_active}

            # 현재 라우팅되고 있는 엔드포인트를 가져옵니다.
            routed_endpoints = {endpoint.replace("/flows/run/", "") for endpoint in self.router_service.dynamic_routers.keys()}

            # DB에 추가되어야 할 라우트를 찾습니다.
            to_add = active_flows_in_db - routed_endpoints
            for flow_model in flows_from_db:
                flow_schema = schemas.FlowRead.from_orm(flow_model)
                if flow_schema.endpoint in to_add:
                    print(f"[Scheduler] Found new flow to add: {flow_schema.endpoint}")
                    self.router_service.add_flow_route(flow_schema)

            # DB에서 삭제되어야 할 라우트를 찾습니다.
            to_remove = routed_endpoints - active_flows_in_db
            for endpoint_name in to_remove:
                print(f"[Scheduler] Found stale flow to remove: {endpoint_name}")
                self.router_service.remove_flow_route(endpoint_name)

            print(f"✅ Sync complete. Total active routes: {len(self.router_service.dynamic_routers)}")

        finally:
            db.close()

    async def run(self, interval_seconds: int = 60):
        """Runs the sync task periodically."""
        self._is_running = True
        print(f"🔄 Starting periodic route synchronization (every {interval_seconds}s).")
        while self._is_running:
            try:
                self.sync_routes_from_db()
            except Exception as e:
                print(f"❌ Error during route synchronization: {e}")
            await asyncio.sleep(interval_seconds)

    def start(self, interval_seconds: int = 60):
        """Starts the background synchronization task."""
        if self._task is None:
            self._task = asyncio.create_task(self.run(interval_seconds))
            print("Scheduler task created.")

    def stop(self):
        """Stops the background synchronization task."""
        self._is_running = False
        if self._task:
            self._task.cancel()
            self._task = None
        print("🛑 Stopped periodic route synchronization.")
