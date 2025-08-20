from typing import Final

from fastapi import APIRouter

from cmk.agent_receiver.relay.api.routers.relays.endpoints import router

RELAY_ROUTER: Final = APIRouter(prefix="/relays")

RELAY_ROUTER.include_router(router)
