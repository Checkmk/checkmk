#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the livestatus waits of :class:`tests.testlib.system.site.Site`.

An object reaches livestatus only once the monitoring core has re-read its
configuration, which happens after the activation that created it has returned. Only a
live site shows that gap, so the waits closing it are pinned here.
"""

import time
from collections.abc import Sequence

import pytest

from cmk.livestatus_client import MKLivestatusNotFoundError, MKLivestatusSocketError
from tests.testlib.system.site import Site

HOST = "notify-test"
SERVICE = "Check_MK"


class FakeLivestatus:
    """A core that learns about the queried object, host or service, after a few queries."""

    def __init__(self, unknown_for: int = 0, while_unknown: Exception | None = None) -> None:
        self._unknown_for = unknown_for
        self._while_unknown = while_unknown
        self.queries: list[str] = []
        self.commands: list[str] = []

    @property
    def knows_the_object(self) -> bool:
        return len(self.queries) > self._unknown_for

    def query(self, query: str) -> Sequence[Sequence[object]]:
        self.queries.append(query)
        if self.knows_the_object:
            return [["the object"]]
        if self._while_unknown is not None:
            raise self._while_unknown
        return []

    def query_value(self, query: str) -> object:
        self._require_the_object(query)
        return 0

    def query_row(self, query: str) -> Sequence[object]:
        self._require_the_object(query)
        return [time.time(), 2, "FAKE CRIT"]

    def command(self, command: str) -> None:
        self.commands.append(command)

    def _require_the_object(self, query: str) -> None:
        if not self.knows_the_object:
            raise MKLivestatusNotFoundError(f"No matching entries found for query: {query}")


@pytest.fixture(name="instant_polling")
def _instant_polling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Spend the wait budget without spending the wall clock."""
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)


def _site_talking_to(live: FakeLivestatus, monkeypatch: pytest.MonkeyPatch) -> Site:
    monkeypatch.setattr(Site, "live", property(lambda _self: live))

    site = Site.__new__(Site)  # a real site cannot be built without an installed Checkmk
    site.check_wait_timeout = 20
    return site


@pytest.mark.usefixtures("instant_polling")
def test_the_wait_returns_once_the_core_knows_the_service(monkeypatch: pytest.MonkeyPatch) -> None:
    live = FakeLivestatus(unknown_for=2)
    site = _site_talking_to(live, monkeypatch)

    site.wait_for_service_in_livestatus(HOST, SERVICE)

    assert live.knows_the_object


@pytest.mark.usefixtures("instant_polling")
def test_the_wait_asks_the_core_for_the_host(monkeypatch: pytest.MonkeyPatch) -> None:
    live = FakeLivestatus(unknown_for=2)
    site = _site_talking_to(live, monkeypatch)

    site.wait_for_host_in_livestatus(HOST)

    assert live.queries[-1].startswith("GET hosts\n")
    assert f"Filter: name = {HOST}" in live.queries[-1]


@pytest.mark.usefixtures("instant_polling")
def test_a_host_check_result_waits_for_the_host_instead_of_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = FakeLivestatus(unknown_for=2)
    site = _site_talking_to(live, monkeypatch)

    site.send_host_check_result(HOST, 2, "FAKE DOWN", expected_state=2)

    assert live.commands[-1].endswith(f"PROCESS_HOST_CHECK_RESULT;{HOST};2;FAKE DOWN")


@pytest.mark.usefixtures("instant_polling")
def test_a_broken_connection_counts_as_not_monitored_yet(monkeypatch: pytest.MonkeyPatch) -> None:
    """The livestatus socket vanishes for a moment while the core re-reads its config."""
    live = FakeLivestatus(unknown_for=2, while_unknown=MKLivestatusSocketError("socket gone"))
    site = _site_talking_to(live, monkeypatch)

    site.wait_for_service_in_livestatus(HOST, SERVICE)

    assert live.knows_the_object


@pytest.mark.usefixtures("instant_polling")
def test_the_wait_gives_up_when_the_service_never_appears(monkeypatch: pytest.MonkeyPatch) -> None:
    live = FakeLivestatus(unknown_for=10**6)
    site = _site_talking_to(live, monkeypatch)

    with pytest.raises(TimeoutError):
        site.wait_for_service_in_livestatus(HOST, SERVICE, timeout=0.01)


@pytest.mark.usefixtures("instant_polling")
def test_a_check_result_waits_for_the_service_instead_of_failing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The result used to be submitted right away and died on the service not being there."""
    live = FakeLivestatus(unknown_for=2)
    site = _site_talking_to(live, monkeypatch)

    site.send_service_check_result(HOST, SERVICE, 2, "FAKE CRIT")

    assert live.commands[-1].endswith(f"PROCESS_SERVICE_CHECK_RESULT;{HOST};{SERVICE};2;FAKE CRIT")
