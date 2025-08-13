from cmk.agent_receiver.relay_backend.lib.relays_repository import RelaysRepository


def get_relays_repository() -> RelaysRepository:
    return RelaysRepository()
