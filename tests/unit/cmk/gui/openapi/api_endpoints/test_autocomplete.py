#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.gui.autocompleters import autocompleter_registry
from cmk.gui.config import Config
from cmk.web.utils.choices import Choice
from tests.testlib.unit.rest_api_client import ClientRegistry

IDENT = "test_truncating_autocompleter"


@pytest.fixture(name="truncating_autocompleter")
def fixture_truncating_autocompleter() -> Iterator[None]:
    def autocompleter(config: Config, value: str, params: dict[str, object]) -> list[Choice]:  # noqa: ARG001
        return [(None, "(Max suggestions reached, be more specific)"), ("linux01", "linux01")]

    autocompleter_registry.register_autocompleter(IDENT, autocompleter)
    try:
        yield
    finally:
        autocompleter_registry.unregister(IDENT)


@pytest.mark.usefixtures("truncating_autocompleter")
def test_a_choice_without_an_id_is_served(clients: ClientRegistry) -> None:
    """An autocompleter reports a truncated result list as a choice with no id.

    `CmkSuggestions` renders those as a hint the user cannot select. Dropping
    them here leaves the user with a silently shortened list and no way to tell
    that narrowing the search would show more.
    """
    response = clients.AutoComplete.invoke(IDENT, {}, "lin")

    assert response.json["choices"] == [
        {"id": None, "value": "(Max suggestions reached, be more specific)"},
        {"id": "linux01", "value": "linux01"},
    ]
