from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


def get_relays_repository() -> RelaysRepository:
    return RelaysRepository()
