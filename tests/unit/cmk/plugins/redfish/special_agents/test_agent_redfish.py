#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: SLF001  # Private member accessed - tests exercise the emission helpers directly.
"""Streaming/resilience tests for the Redfish special agent: each section must
reach stdout as soon as it's gathered, and one failing endpoint must not abort
the rest of the run."""

import io
import sys
import time
from typing import Any
from unittest import mock

import pytest

from cmk.plugins.redfish.special_agents import agent_redfish
from cmk.special_agents.v0_unstable.agent_common import CannotRecover


def _make_redfishobj(debug: bool = False) -> agent_redfish.RedfishData:
    return agent_redfish.RedfishData(
        hostname="testhost_443",
        use_cache=False,
        redfish_connection=None,  # type: ignore[arg-type]
        debug=debug,
    )


def test_process_result_writes_header_and_payload(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    redfishobj.section_data["Memory"] = [{"Id": "DIMM.A1"}]
    agent_redfish.process_result(redfishobj)

    out = capsys.readouterr().out
    assert "<<<redfish_memory:sep(0)>>>" in out
    assert '"Id": "DIMM.A1"' in out
    assert "Memory" in redfishobj.emitted_sections


def test_process_result_is_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    redfishobj.section_data["Memory"] = [{"Id": "DIMM.A1"}]
    agent_redfish.process_result(redfishobj)
    agent_redfish.process_result(redfishobj)

    out = capsys.readouterr().out
    # Header appears exactly once even if process_result is called twice.
    assert out.count("<<<redfish_memory:sep(0)>>>") == 1


def test_process_result_writes_every_collected_section(
    capsys: pytest.CaptureFixture[str],
) -> None:
    redfishobj = _make_redfishobj()
    redfishobj.section_data = {
        "Memory": [{"Id": "DIMM.A1"}],
        "Processors": [{"Id": "CPU.1"}],
        "Drives": [{"Id": "Disk.0"}],
    }
    agent_redfish.process_result(redfishobj)

    out = capsys.readouterr().out
    for header in (
        "<<<redfish_memory:sep(0)>>>",
        "<<<redfish_processors:sep(0)>>>",
        "<<<redfish_drives:sep(0)>>>",
    ):
        assert header in out


def test_phase_swallows_exception_and_flushes(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    redfishobj.section_data["Memory"] = [{"Id": "DIMM.A1"}]

    with agent_redfish._phase(redfishobj, "systems"):
        redfishobj.section_data["Processors"] = [{"Id": "CPU.1"}]
        raise RuntimeError("simulated mid-flow failure")

    # `_phase` swallows the exception (see its except/finally), so the code
    # below is reached and the already-collected sections were flushed.
    out = capsys.readouterr().out
    assert "<<<redfish_memory:sep(0)>>>" in out
    assert "<<<redfish_processors:sep(0)>>>" in out


def test_phase_reraises_when_debug(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj(debug=True)
    redfishobj.section_data["Memory"] = [{"Id": "DIMM.A1"}]

    with pytest.raises(RuntimeError, match="simulated"):
        with agent_redfish._phase(redfishobj, "systems"):
            raise RuntimeError("simulated mid-flow failure")

    # `finally` flushes even when the exception propagates.
    out = capsys.readouterr().out
    assert "<<<redfish_memory:sep(0)>>>" in out


def test_fetch_sections_continues_when_one_section_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redfishobj = _make_redfishobj()

    def fake_fetch_data(
        _client: Any, url: str, _component: object, timeout: int | None = None
    ) -> Any:
        if "Memory" in url:
            raise RuntimeError("Memory endpoint blew up")
        return {
            "@odata.type": "#Collection",
            "Members@odata.count": 1,
            "Members": [{"@odata.id": f"{url}/Item1"}],
        }

    def fake_fetch_collection(_client: Any, _data: Any, component: object) -> list[dict[str, str]]:
        return [{"Id": f"item-of-{component}"}]

    monkeypatch.setattr(agent_redfish, "fetch_data", fake_fetch_data)
    monkeypatch.setattr(agent_redfish, "fetch_collection", fake_fetch_collection)

    data = {
        "Memory": {"@odata.id": "/Memory"},
        "Processors": {"@odata.id": "/Processors"},
        "EthernetInterfaces": {"@odata.id": "/EthernetInterfaces"},
    }
    sections = {"Memory", "Processors", "EthernetInterfaces"}

    agent_redfish.fetch_sections(redfishobj, list(sections), sections, data)

    assert "Memory" not in redfishobj.section_data
    assert "Processors" in redfishobj.section_data
    assert "EthernetInterfaces" in redfishobj.section_data


def test_fetch_sections_reraises_when_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _make_redfishobj(debug=True)

    def fake_fetch_data(*_a: Any, **_kw: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(agent_redfish, "fetch_data", fake_fetch_data)

    with pytest.raises(RuntimeError, match="boom"):
        agent_redfish.fetch_sections(
            redfishobj,
            ["Memory"],
            {"Memory"},
            {"Memory": {"@odata.id": "/Memory"}},
        )


def test_fetch_list_of_elements_continues_when_one_section_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redfishobj = _make_redfishobj()

    def fake_fetch_data(
        _client: Any, url: str, _component: object, timeout: int | None = None
    ) -> Any:
        if "drive" in url.lower():
            raise RuntimeError("Drive endpoint blew up")
        return {"@odata.type": "#Volume.Volume", "Id": "vol-1"}

    monkeypatch.setattr(agent_redfish, "fetch_data", fake_fetch_data)

    data = {
        "Drives": [{"@odata.id": "/redfish/v1/Systems/1/Storage/0/Drives/0"}],
        "Volumes": [{"@odata.id": "/redfish/v1/Systems/1/Storage/0/Volumes/0"}],
    }
    sections = {"Drives", "Volumes"}

    agent_redfish.fetch_list_of_elements(redfishobj, list(sections), sections, data)

    # Drives blew up; Volumes must still have been collected.
    assert "Drives" not in redfishobj.section_data
    assert "Volumes" in redfishobj.section_data


def test_fetch_list_of_elements_reraises_when_debug(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _make_redfishobj(debug=True)

    def fake_fetch_data(*_a: Any, **_kw: Any) -> Any:
        raise RuntimeError("boom")

    monkeypatch.setattr(agent_redfish, "fetch_data", fake_fetch_data)

    with pytest.raises(RuntimeError, match="boom"):
        agent_redfish.fetch_list_of_elements(
            redfishobj,
            ["Drives"],
            {"Drives"},
            {"Drives": [{"@odata.id": "/redfish/v1/Systems/1/Storage/0/Drives/0"}]},
        )


def test_process_result_handles_non_list_payload(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    redfishobj.section_data["FirmwareInventory"] = {"Current": {"Foo": "1.0"}}
    agent_redfish.process_result(redfishobj)

    out = capsys.readouterr().out
    assert "<<<redfish_firmwareinventory:sep(0)>>>" in out
    assert '"Current":' in out


def test_process_result_flushes_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _make_redfishobj()
    redfishobj.section_data["Memory"] = [{"Id": "DIMM.A1"}]
    stream = io.StringIO()
    flush = mock.Mock(wraps=stream.flush)
    monkeypatch.setattr(stream, "flush", flush)
    monkeypatch.setattr(sys, "stdout", stream)

    agent_redfish.process_result(redfishobj)

    # Streaming depends on flushing, else a later abort could lose buffered data.
    assert flush.call_count >= 1


# --- _fetch_systems: retry transient /redfish/v1/Systems failures, then abort ---------


def _systems_obj(retries: int) -> agent_redfish.RedfishData:
    redfishobj = _make_redfishobj()
    redfishobj.redfish_connection = object()  # type: ignore[assignment]  # fetch_data is mocked
    redfishobj.systems_retries = retries
    redfishobj.systems_retry_delay = 0.0
    return redfishobj


def test_fetch_systems_retries_then_aborts(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _systems_obj(retries=2)
    calls = {"fetch": 0}

    def fake_fetch_data(*_a: Any, **_kw: Any) -> Any:
        calls["fetch"] += 1
        return {"error": "System data could not be fetched\n"}

    sleep = mock.Mock()
    monkeypatch.setattr(agent_redfish, "fetch_data", fake_fetch_data)
    monkeypatch.setattr(agent_redfish, "fetch_collection", lambda *_a, **_k: [])
    monkeypatch.setattr(time, "sleep", sleep)

    with pytest.raises(CannotRecover):
        agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")

    assert calls["fetch"] == 3  # initial attempt + 2 retries
    assert sleep.call_count == 2


def test_fetch_systems_succeeds_on_later_attempt(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _systems_obj(retries=3)
    sequence = iter(
        [
            ({"error": "x"}, []),
            ({"error": "x"}, []),
            ({"@odata.type": "#ComputerSystemCollection"}, [{"Id": "System.Embedded.1"}]),
        ]
    )
    current: dict[str, Any] = {}

    def fake_fetch_data(*_a: Any, **_kw: Any) -> Any:
        current["col"], current["data"] = next(sequence)
        return current["col"]

    sleep = mock.Mock()
    monkeypatch.setattr(agent_redfish, "fetch_data", fake_fetch_data)
    monkeypatch.setattr(agent_redfish, "fetch_collection", lambda *_a, **_k: current["data"])
    monkeypatch.setattr(time, "sleep", sleep)

    result = agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")

    assert result == [{"Id": "System.Embedded.1"}]
    assert sleep.call_count == 2


def test_fetch_systems_zero_retries_aborts_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _systems_obj(retries=0)
    sleep = mock.Mock()
    monkeypatch.setattr(agent_redfish, "fetch_data", lambda *_a, **_k: {"error": "x"})
    monkeypatch.setattr(agent_redfish, "fetch_collection", lambda *_a, **_k: [])
    monkeypatch.setattr(time, "sleep", sleep)

    with pytest.raises(CannotRecover):
        agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")

    assert sleep.call_count == 0


def test_fetch_systems_healthy_no_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _systems_obj(retries=3)
    sleep = mock.Mock()
    monkeypatch.setattr(agent_redfish, "fetch_data", lambda *_a, **_k: {"@odata.type": "#x"})
    monkeypatch.setattr(agent_redfish, "fetch_collection", lambda *_a, **_k: [{"Id": "S1"}])
    monkeypatch.setattr(time, "sleep", sleep)

    result = agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")

    assert result == [{"Id": "S1"}]
    assert sleep.call_count == 0


def test_fetch_systems_mixed_members_not_aborted(monkeypatch: pytest.MonkeyPatch) -> None:
    # One good system + one errored member => still usable, must not abort.
    redfishobj = _systems_obj(retries=3)
    sleep = mock.Mock()
    monkeypatch.setattr(agent_redfish, "fetch_data", lambda *_a, **_k: {"@odata.type": "#x"})
    monkeypatch.setattr(
        agent_redfish,
        "fetch_collection",
        lambda *_a, **_k: [{"Id": "S1"}, {"error": "x"}],
    )
    monkeypatch.setattr(time, "sleep", sleep)

    result = agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")

    assert any(isinstance(s, dict) and "Id" in s for s in result)
    assert sleep.call_count == 0
