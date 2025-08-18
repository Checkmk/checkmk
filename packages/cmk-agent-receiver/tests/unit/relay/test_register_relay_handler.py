import uuid
from collections.abc import Iterator

import pytest

from cmk.agent_receiver.relay_backend.api.routers.relays.handlers.register_relay import (
    RegisterRelayHandler,
    RelayAlreadyRegisteredError,
)
from cmk.agent_receiver.relay_backend.lib.relays_repository import RelaysRepository


@pytest.fixture()
def relays_repository() -> Iterator[RelaysRepository]:
    repository = RelaysRepository()
    yield repository


@pytest.fixture()
def register_relay_handler(relays_repository: RelaysRepository) -> Iterator[RegisterRelayHandler]:
    handler = RegisterRelayHandler(relays_repository=relays_repository)
    yield handler


def test_process_adds_new_relay_id_to_registry(
    register_relay_handler: RegisterRelayHandler,
) -> None:
    relay_id = str(uuid.uuid4())
    register_relay_handler.process(relay_id)
    assert register_relay_handler.relays_repository.has_relay(relay_id)
    assert register_relay_handler.relays_repository.get_relay_tasks(relay_id) == []


def test_process_existing_relay_id_returns_error(
    register_relay_handler: RegisterRelayHandler,
) -> None:
    relay_id = str(uuid.uuid4())
    register_relay_handler.process(relay_id)
    with pytest.raises(RelayAlreadyRegisteredError):
        register_relay_handler.process(relay_id)


def test_add_multiple_relays(register_relay_handler: RegisterRelayHandler) -> None:
    relay_ids = [str(uuid.uuid4()) for _ in range(5)]
    for relay_id in relay_ids:
        register_relay_handler.process(relay_id)
        assert register_relay_handler.relays_repository.has_relay(relay_id)
        assert register_relay_handler.relays_repository.get_relay_tasks(relay_id) == []
