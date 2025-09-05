#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import uuid
from collections.abc import Iterator

import pytest

from cmk.agent_receiver.relay.api.routers.relays.handlers.register_relay import (
    RegisterRelayHandler,
    RelayAlreadyRegisteredError,
)
from cmk.agent_receiver.relay.lib.relays_repository import RelaysRepository
from cmk.agent_receiver.relay.lib.shared_types import RelayID


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
    relay_id = RelayID(str(uuid.uuid4()))
    register_relay_handler.process(relay_id, alias="test")
    assert register_relay_handler.relays_repository.has_relay(relay_id)


def test_process_existing_relay_id_returns_error(
    register_relay_handler: RegisterRelayHandler,
) -> None:
    relay_id = RelayID(str(uuid.uuid4()))
    register_relay_handler.process(relay_id)
    with pytest.raises(RelayAlreadyRegisteredError):
        register_relay_handler.process(relay_id)


def test_add_multiple_relays(
    register_relay_handler: RegisterRelayHandler,
) -> None:
    relay_ids = [RelayID(str(uuid.uuid4())) for _ in range(5)]
    for relay_id in relay_ids:
        register_relay_handler.process(relay_id)
        assert register_relay_handler.relays_repository.has_relay(relay_id)


def test_register_relay_with_duplicate_id(register_relay_handler: RegisterRelayHandler) -> None:
    relay_id = RelayID(str(uuid.uuid4()))
    register_relay_handler.process(relay_id)
    with pytest.raises(RelayAlreadyRegisteredError):
        register_relay_handler.process(relay_id)
