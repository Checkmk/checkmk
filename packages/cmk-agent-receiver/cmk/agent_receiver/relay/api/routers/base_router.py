from typing import Final

from fastapi import APIRouter

from cmk.agent_receiver.relay.api.routers import relays, tasks

RELAY_ROUTER: Final = APIRouter(prefix="/relays")

RELAY_ROUTER.include_router(relays.router)
RELAY_ROUTER.include_router(tasks.router)
