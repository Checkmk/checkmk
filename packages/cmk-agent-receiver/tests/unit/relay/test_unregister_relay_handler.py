import uuid
from collections.abc import Iterator

import pytest

from cmk.agent_receiver.relay.api.routers.relays.handlers.unregister_relay import (
    RelayNotFoundError,
    UnregisterRelayHandler,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository


@pytest.fixture()
def relays_repository() -> Iterator[RelaysRepository]:
    repository = RelaysRepository()
    yield repository


@pytest.fixture()
def unregister_relay_handler(
    relays_repository: RelaysRepository,
) -> Iterator[UnregisterRelayHandler]:
    handler = UnregisterRelayHandler(relays_repository=relays_repository)
    yield handler


def test_process_removes_relay_id_from_registry(
    relays_repository: RelaysRepository,
    unregister_relay_handler: UnregisterRelayHandler,
) -> None:
    relay_id = str(uuid.uuid4())
    relays_repository.add_relay(relay_id)
    assert relays_repository.has_relay(relay_id)
    unregister_relay_handler.process(relay_id)
    assert not relays_repository.has_relay(relay_id)


def test_process_removes_non_existent_relay_id(
    unregister_relay_handler: UnregisterRelayHandler,
) -> None:
    relay_id = str(uuid.uuid4())
    assert not unregister_relay_handler.relays_repository.has_relay(relay_id)
    with pytest.raises(RelayNotFoundError):
        unregister_relay_handler.process(relay_id)
    assert not unregister_relay_handler.relays_repository.has_relay(relay_id)
