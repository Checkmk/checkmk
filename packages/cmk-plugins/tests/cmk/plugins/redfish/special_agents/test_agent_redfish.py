#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# ruff: noqa: ARG001  # Unused fixtures are needed for setup side effects

# mypy: disable-error-code="explicit-any"

"""Streaming/resilience tests for the Redfish special agent: each section must
reach stdout as soon as it's gathered, and one failing endpoint must not abort
the rest of the run."""

import io
import json
import sys
import time
from collections.abc import Mapping, Sequence
from http import HTTPStatus
from pathlib import Path
from typing import Any
from unittest import mock

import pytest
from redfish.rest.v1 import SessionCreationError  # type: ignore[import-not-found]

from cmk.password_store.v1 import Obfuscator, Secret
from cmk.plugins.redfish.special_agents import agent_redfish
from cmk.server_side_programs.v1 import ObfuscatedStorage, Storage

_ILO_NOT_READY = {
    "error": {
        "code": "iLO.0.10.ExtendedInfo",
        "message": "See @Message.ExtendedInfo for more information.",
        "@Message.ExtendedInfo": [
            {"MessageArgs": ["5, (84,00,00)"], "MessageId": "iLO.2.25.ResourceNotReadyRetry"}
        ],
    }
}

_STORAGE = "/redfish/v1/Systems/1/Storage/DE07A000"
_FIRMWARE = "/redfish/v1/UpdateService/FirmwareInventory"


def _make_redfishobj(debug: bool = False) -> agent_redfish.RedfishData:
    return agent_redfish.RedfishData(
        hostname="testhost_443",
        use_cache=False,
        redfish_connection=None,  # type: ignore[arg-type]
        debug=debug,
    )


def test_emit_section_writes_header_and_payload(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    agent_redfish._emit_section(redfishobj, "Memory", [{"Id": "DIMM.A1"}])  # noqa: SLF001

    out = capsys.readouterr().out
    assert "<<<redfish_memory:sep(0)" in out
    assert '"Id": "DIMM.A1"' in out
    assert "Memory" in redfishobj.emitted_sections


def test_emit_section_is_idempotent(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    agent_redfish._emit_section(redfishobj, "Memory", [{"Id": "DIMM.A1"}])  # noqa: SLF001
    agent_redfish._emit_section(redfishobj, "Memory", [{"Id": "DIMM.A1"}])  # noqa: SLF001

    out = capsys.readouterr().out
    # Header appears exactly once even if the helper is called twice.
    assert out.count("<<<redfish_memory:sep(0)") == 1


def test_emit_pending_writes_every_collected_section(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    redfishobj.section_data = {
        "Memory": [{"Id": "DIMM.A1"}],
        "Processors": [{"Id": "CPU.1"}],
        "Drives": [{"Id": "Disk.0"}],
    }
    agent_redfish._emit_pending(redfishobj)  # noqa: SLF001

    out = capsys.readouterr().out
    for header in (
        "<<<redfish_memory:sep(0)",
        "<<<redfish_processors:sep(0)",
        "<<<redfish_drives:sep(0)",
    ):
        assert header in out


def test_phase_swallows_exception_and_flushes(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    redfishobj.section_data["Memory"] = [{"Id": "DIMM.A1"}]

    with agent_redfish._phase(redfishobj, "systems"):  # noqa: SLF001
        redfishobj.section_data["Processors"] = [{"Id": "CPU.1"}]
        raise RuntimeError("simulated mid-flow failure")

    # mypy's narrow control-flow analysis sees the `with` body always raises and
    # marks subsequent statements unreachable; at runtime `_phase` swallows the
    # exception (see its `except`/`finally`), so the code below IS reached.
    out = capsys.readouterr().out  # type: ignore[unreachable]
    assert "<<<redfish_memory:sep(0)" in out
    assert "<<<redfish_processors:sep(0)" in out


def test_phase_reraises_when_debug(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj(debug=True)
    redfishobj.section_data["Memory"] = [{"Id": "DIMM.A1"}]

    with (
        pytest.raises(RuntimeError, match="simulated"),
        agent_redfish._phase(redfishobj, "systems"),  # noqa: SLF001
    ):
        raise RuntimeError("simulated mid-flow failure")

    # `finally` flushes even when the exception propagates.
    out = capsys.readouterr().out
    assert "<<<redfish_memory:sep(0)" in out


@pytest.mark.usefixtures("capsys")
def test_fetch_sections_continues_when_one_section_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _make_redfishobj()

    def fake_fetch_data(
        _client: Any,
        url: str,
        _component: object,
        timeout: int | None = None,
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


def test_fetch_list_of_elements_continues_when_one_section_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redfishobj = _make_redfishobj()

    def fake_fetch_data(
        _client: Any,
        url: str,
        _component: object,
        timeout: int | None = None,
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


def test_emit_section_handles_non_list_payload(capsys: pytest.CaptureFixture[str]) -> None:
    redfishobj = _make_redfishobj()
    agent_redfish._emit_section(redfishobj, "FirmwareInventory", {"Current": {"Foo": "1.0"}})  # noqa: SLF001

    out = capsys.readouterr().out
    assert "<<<redfish_firmwareinventory:sep(0)" in out
    assert '"Current":' in out


def test_stdout_flushed_after_each_section(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _make_redfishobj()
    stream = io.StringIO()
    flush = mock.Mock(wraps=stream.flush)
    monkeypatch.setattr(stream, "flush", flush)
    monkeypatch.setattr(sys, "stdout", stream)

    agent_redfish._emit_section(redfishobj, "Memory", [{"Id": "DIMM.A1"}])  # noqa: SLF001

    # Streaming depends on flushing, else a later abort could lose buffered data.
    assert flush.call_count >= 1


def _response(status: int, body: object = None) -> mock.Mock:
    return mock.Mock(status=status, dict={} if body is None else body)


def _client(*responses: mock.Mock) -> agent_redfish.RedfishClient:
    return agent_redfish.RedfishClient(mock.Mock(get=mock.Mock(side_effect=responses)))


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

    with pytest.raises(agent_redfish.CannotRecover):
        agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")  # noqa: SLF001

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

    result = agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")  # noqa: SLF001

    assert result == [{"Id": "System.Embedded.1"}]
    assert sleep.call_count == 2


def test_fetch_systems_zero_retries_aborts_immediately(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _systems_obj(retries=0)
    sleep = mock.Mock()
    monkeypatch.setattr(agent_redfish, "fetch_data", lambda *_a, **_k: {"error": "x"})
    monkeypatch.setattr(agent_redfish, "fetch_collection", lambda *_a, **_k: [])
    monkeypatch.setattr(time, "sleep", sleep)

    with pytest.raises(agent_redfish.CannotRecover):
        agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")  # noqa: SLF001

    assert sleep.call_count == 0


def test_fetch_systems_healthy_no_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    redfishobj = _systems_obj(retries=3)
    sleep = mock.Mock()
    monkeypatch.setattr(agent_redfish, "fetch_data", lambda *_a, **_k: {"@odata.type": "#x"})
    monkeypatch.setattr(agent_redfish, "fetch_collection", lambda *_a, **_k: [{"Id": "S1"}])
    monkeypatch.setattr(time, "sleep", sleep)

    result = agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")  # noqa: SLF001

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

    result = agent_redfish._fetch_systems(redfishobj, "/redfish/v1/Systems")  # noqa: SLF001

    assert any(isinstance(s, dict) and "Id" in s for s in result)
    assert sleep.call_count == 0


def _cached_obj(
    storage_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Storage, agent_redfish.RedfishData]:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(storage_path))
    redfishobj = _make_redfishobj()
    redfishobj.sections = {"Memory"}
    redfishobj.cache_per_section = {"Memory": 300}
    return Storage(agent_redfish.AGENT, redfishobj.hostname), redfishobj


@pytest.mark.parametrize("content", ["", '{"timestamp": 176'], ids=["empty", "half_written"])
def test_load_section_data_tolerates_truncated_cache(
    content: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, redfishobj = _cached_obj(tmp_path, monkeypatch)
    storage.write("Memory", content)

    result = agent_redfish.load_section_data(storage, redfishobj)

    assert "Memory" in result.sections
    assert "Memory" not in result.section_data
    assert storage.read("Memory", None) is None


def test_load_section_data_uses_intact_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    storage, redfishobj = _cached_obj(tmp_path, monkeypatch)
    storage.write(
        "Memory", json.dumps({"timestamp": int(time.time()), "data": [{"Id": "DIMM.A1"}]})
    )

    result = agent_redfish.load_section_data(storage, redfishobj)

    assert "Memory" not in result.sections
    assert result.section_data["Memory"] == [{"Id": "DIMM.A1"}]


@pytest.mark.parametrize(
    "response",
    [
        _response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY),
        _response(HTTPStatus.SERVICE_UNAVAILABLE),
        _response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {
                "error": {
                    "@Message.ExtendedInfo": [
                        {"MessageId": "Base.1.23.ServiceTemporarilyUnavailable"}
                    ]
                }
            },
        ),
        _response(
            HTTPStatus.INTERNAL_SERVER_ERROR,
            {"error": {"code": "Base.1.8.ServiceTemporarilyUnavailable"}},
        ),
        _response(
            HTTPStatus.BAD_REQUEST,
            {
                "error": {
                    "@Message.ExtendedInfo": [{"MessageId": "HpeCommon.2.1.ResourceNotReadyRetry"}]
                }
            },
        ),
    ],
    ids=[
        "ilo_not_ready",
        "http_503",
        "base_message_any_version",
        "code_without_extended_info",
        "hpecommon_not_ready",
    ],
)
def test_fetch_data_raises_on_temporarily_unavailable(response: mock.Mock) -> None:
    with pytest.raises(agent_redfish.TemporarilyUnavailable):
        agent_redfish.fetch_data(_client(response), "/redfish/v1/Systems/1/Storage/X", "Storage")


@pytest.mark.parametrize(
    "body",
    [
        {"error": {"@Message.ExtendedInfo": [{"MessageId": "Base.1.8.PropertyValueNotInList"}]}},
        {"error": {"code": "InternalError"}},
        {"error": {"code": ""}},
    ],
    ids=["base_message", "code_without_dot", "empty_code"],
)
def test_fetch_data_plain_bad_request_is_no_transient_failure(body: object) -> None:
    result = agent_redfish.fetch_data(
        _client(_response(HTTPStatus.BAD_REQUEST, body)), "/x", "Storage"
    )

    assert result == {"error": "Storage data could not be fetched\n"}


@pytest.mark.parametrize("debug", [False, True], ids=["normal", "debug"])
def test_fetch_sections_leaves_out_unavailable_section(debug: bool) -> None:
    redfishobj = _make_redfishobj(debug=debug)
    redfishobj.redfish_connection = _client(_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY))
    redfishobj.sections = {"Storage"}
    redfishobj.section_data["Storage"] = [{"Id": "of-an-earlier-system"}]

    agent_redfish.fetch_sections(
        redfishobj, ["Storage"], redfishobj.sections, {"Storage": {"@odata.id": "/Storage"}}
    )

    assert "Storage" not in redfishobj.section_data
    assert "Storage" not in redfishobj.sections


def test_fetch_list_of_elements_leaves_out_partially_fetched_section() -> None:
    redfishobj = _make_redfishobj()
    redfishobj.redfish_connection = _client(
        _response(HTTPStatus.OK, {"@odata.type": "#Drive.v1_18_0.Drive", "Id": "0"}),
        _response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY),
    )
    redfishobj.sections = {"Drives"}

    agent_redfish.fetch_list_of_elements(
        redfishobj,
        ["Drives"],
        redfishobj.sections,
        {"Drives": [{"@odata.id": "/Drives/0"}, {"@odata.id": "/Drives/2"}]},
    )

    assert "Drives" not in redfishobj.section_data


class _FakeDevice:
    """Answers each GET with the next response listed for its URL, repeating the last one"""

    def __init__(self, responses: Mapping[str, Sequence[mock.Mock | Exception]]) -> None:
        self._responses = {url: list(answers) for url, answers in responses.items()}

    def get(self, url: str, **_kwargs: object) -> mock.Mock:
        answers = self._responses[url]
        answer = answers.pop(0) if len(answers) > 1 else answers[0]
        if isinstance(answer, Exception):
            raise answer
        return answer


def _device_tree() -> dict[str, list[mock.Mock | Exception]]:
    return {
        "/redfish/v1": [
            _response(
                HTTPStatus.OK,
                {
                    "Systems": {"@odata.id": "/redfish/v1/Systems"},
                    "Chassis": {"@odata.id": "/redfish/v1/Chassis"},
                    "UpdateService": {"@odata.id": "/redfish/v1/UpdateService"},
                },
            )
        ],
        "/redfish/v1/Systems": [
            _response(HTTPStatus.OK, {"Members": [{"@odata.id": "/redfish/v1/Systems/1"}]})
        ],
        "/redfish/v1/Systems/1": [
            _response(
                HTTPStatus.OK,
                {"Id": "1", "Storage": {"@odata.id": "/redfish/v1/Systems/1/Storage"}},
            )
        ],
        "/redfish/v1/Systems/1/Storage": [
            _response(
                HTTPStatus.OK,
                {
                    "@odata.type": "#StorageCollection.StorageCollection",
                    "Members@odata.count": 1,
                    "Members": [{"@odata.id": _STORAGE}],
                },
            )
        ],
        _STORAGE: [
            _response(
                HTTPStatus.OK,
                {
                    "@odata.type": "#Storage.v1_15_0.Storage",
                    "Id": "DE07A000",
                    "Drives": [{"@odata.id": f"{_STORAGE}/Drives/0"}],
                },
            )
        ],
        f"{_STORAGE}/Drives/0": [
            _response(HTTPStatus.OK, {"@odata.type": "#Drive.v1_18_0.Drive", "Id": "0"})
        ],
        _FIRMWARE: [_response(HTTPStatus.OK, {"Members": [{"@odata.id": f"{_FIRMWARE}/BMC"}]})],
        f"{_FIRMWARE}/BMC": [_response(HTTPStatus.OK, {"Id": "BMC"})],
        "/redfish/v1/Chassis": [_response(HTTPStatus.OK, {"Members": []})],
    }


def _agent(
    responses: Mapping[str, Sequence[mock.Mock | Exception]], debug: bool = True
) -> agent_redfish.RedfishData:
    redfishobj = _make_redfishobj(debug=debug)
    redfishobj.redfish_connection = agent_redfish.RedfishClient(_FakeDevice(responses))
    redfishobj.sections = {"Storage", "Drives", "FirmwareInventory"}
    redfishobj.systems_retries = 0
    redfishobj.systems_retry_delay = 0.0
    return redfishobj


def _run(redfishobj: agent_redfish.RedfishData) -> None:
    agent_redfish.get_information(Storage(agent_redfish.AGENT, redfishobj.hostname), redfishobj)


def test_get_information_persists_fresh_sections(capsys: pytest.CaptureFixture[str]) -> None:
    _run(_agent(_device_tree()))

    assert "<<<redfish_storage:sep(0):persist(" in capsys.readouterr().out


def test_get_information_emits_empty_collection_and_its_dependents(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree["/redfish/v1/Systems/1/Storage"] = [
        _response(
            HTTPStatus.OK,
            {"@odata.type": "#StorageCollection.StorageCollection", "Members@odata.count": 0},
        )
    ]

    _run(_agent(tree))

    out = capsys.readouterr().out
    assert "<<<redfish_storage:sep(0):persist(" in out
    assert "<<<redfish_drives:sep(0):persist(" in out


@pytest.mark.parametrize(
    "sections",
    [{"Storage"}, {"Storage", "FirmwareInventory"}],
    ids=["storage_only", "drives_and_volumes_disabled"],
)
def test_get_information_emits_empty_sections_only_when_selected(
    sections: set[str], capsys: pytest.CaptureFixture[str]
) -> None:
    tree = _device_tree()
    tree["/redfish/v1/Systems/1/Storage"] = [
        _response(
            HTTPStatus.OK,
            {"@odata.type": "#StorageCollection.StorageCollection", "Members@odata.count": 0},
        )
    ]
    redfishobj = _agent(tree)
    redfishobj.sections = sections

    _run(redfishobj)

    out = capsys.readouterr().out
    assert "<<<redfish_storage:sep(0):persist(" in out
    assert "<<<redfish_drives" not in out
    assert "<<<redfish_volumes" not in out


def test_get_information_leaves_out_unavailable_storage_and_its_drives(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree[_STORAGE] = [_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY)]

    _run(_agent(tree))

    out = capsys.readouterr().out
    assert "<<<redfish_system:sep(0)>>>" in out
    assert "<<<redfish_storage" not in out
    assert "<<<redfish_drives" not in out


def test_get_information_does_not_persist_storage_with_error_entry(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree[_STORAGE] = [_response(HTTPStatus.NOT_FOUND)]

    _run(_agent(tree))

    assert "<<<redfish_storage:sep(0)>>>" in capsys.readouterr().out


def test_get_information_leaves_out_drives_of_storage_that_cannot_be_fetched(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree[_STORAGE] = [_response(HTTPStatus.NOT_FOUND)]

    _run(_agent(tree))

    out = capsys.readouterr().out
    assert "<<<redfish_storage:sep(0)>>>" in out
    assert "<<<redfish_drives" not in out


def test_get_information_does_not_persist_drives_next_to_storage_that_cannot_be_fetched(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree["/redfish/v1/Systems/1/Storage"] = [
        _response(
            HTTPStatus.OK,
            {
                "@odata.type": "#StorageCollection.StorageCollection",
                "Members@odata.count": 2,
                "Members": [{"@odata.id": _STORAGE}, {"@odata.id": f"{_STORAGE}-2"}],
            },
        )
    ]
    tree[f"{_STORAGE}-2"] = [_response(HTTPStatus.NOT_FOUND)]

    _run(_agent(tree))

    assert "<<<redfish_drives:sep(0)>>>" in capsys.readouterr().out


def test_get_information_does_not_persist_section_from_cache(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    redfishobj = _agent(_device_tree())
    redfishobj.cache_per_section = {"Storage": 300}
    cached_at = int(time.time())
    Storage(agent_redfish.AGENT, redfishobj.hostname).write(
        "Storage", json.dumps({"timestamp": cached_at, "data": [{"Id": "DE07A000"}]})
    )

    _run(redfishobj)

    assert f"<<<redfish_storage:sep(0):cached({cached_at},300)>>>" in capsys.readouterr().out


def test_get_information_leaves_out_unavailable_firmware_inventory(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree[_FIRMWARE] = [_response(HTTPStatus.SERVICE_UNAVAILABLE)]

    _run(_agent(tree))

    out = capsys.readouterr().out
    assert "<<<redfish_storage:sep(0):persist(" in out
    assert "<<<redfish_firmwareinventory" not in out


def test_get_information_leaves_out_firmware_inventory_that_cannot_be_fetched(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree[_FIRMWARE] = [_response(HTTPStatus.INTERNAL_SERVER_ERROR)]

    _run(_agent(tree))

    out = capsys.readouterr().out
    assert "<<<redfish_storage:sep(0):persist(" in out
    assert "<<<redfish_firmwareinventory" not in out


def test_get_information_leaves_out_expanded_firmware_inventory_that_cannot_be_fetched(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree["/redfish/v1"] = [
        _response(
            HTTPStatus.OK,
            {
                "Vendor": "Dell",
                "Systems": {"@odata.id": "/redfish/v1/Systems"},
                "Chassis": {"@odata.id": "/redfish/v1/Chassis"},
                "UpdateService": {"@odata.id": "/redfish/v1/UpdateService"},
            },
        )
    ]
    tree[f"{_FIRMWARE}?$expand=*($levels=1)"] = [_response(HTTPStatus.INTERNAL_SERVER_ERROR)]

    _run(_agent(tree))

    out = capsys.readouterr().out
    assert "<<<redfish_storage:sep(0):persist(" in out
    assert "<<<redfish_firmwareinventory" not in out


def test_get_information_retries_unavailable_systems(capsys: pytest.CaptureFixture[str]) -> None:
    tree = _device_tree()
    tree["/redfish/v1/Systems"].insert(0, _response(HTTPStatus.SERVICE_UNAVAILABLE))
    redfishobj = _agent(tree)
    redfishobj.systems_retries = 1

    _run(redfishobj)

    assert "<<<redfish_system:sep(0)>>>" in capsys.readouterr().out


def _two_systems_tree() -> dict[str, list[mock.Mock | Exception]]:
    """Systems/2 is temporarily unavailable"""
    tree = _device_tree()
    tree["/redfish/v1/Systems"] = [
        _response(
            HTTPStatus.OK,
            {
                "Members": [
                    {"@odata.id": "/redfish/v1/Systems/1"},
                    {"@odata.id": "/redfish/v1/Systems/2"},
                ]
            },
        )
    ]
    tree["/redfish/v1/Systems/2"] = [_response(HTTPStatus.SERVICE_UNAVAILABLE)]
    return tree


def test_get_information_keeps_systems_next_to_an_unavailable_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _two_systems_tree()

    _run(_agent(tree))

    assert '"Id": "DE07A000"' in capsys.readouterr().out


def test_get_information_does_not_persist_sections_next_to_an_unavailable_system(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _two_systems_tree()

    _run(_agent(tree))

    assert "<<<redfish_storage:sep(0)>>>" in capsys.readouterr().out


def test_get_information_leaves_out_sections_an_unavailable_system_may_supply(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _two_systems_tree()
    tree["/redfish/v1/Systems/1"] = [_response(HTTPStatus.OK, {"Id": "1"})]

    _run(_agent(tree))

    out = capsys.readouterr().out
    assert "<<<redfish_system:sep(0)>>>" in out
    assert "<<<redfish_storage" not in out


def test_get_information_aborts_on_unavailable_systems_without_retries() -> None:
    tree = _device_tree()
    tree["/redfish/v1/Systems"] = [_response(HTTPStatus.SERVICE_UNAVAILABLE)]

    with pytest.raises(agent_redfish.CannotRecover, match="could not be fetched after 0"):
        _run(_agent(tree))


def test_get_information_aborts_on_unavailable_chassis_collection() -> None:
    tree = _device_tree()
    tree["/redfish/v1/Chassis"] = [_response(HTTPStatus.SERVICE_UNAVAILABLE)]

    with pytest.raises(agent_redfish.TemporarilyUnavailable):
        _run(_agent(tree))


def _two_chassis_tree(second: mock.Mock) -> dict[str, list[mock.Mock | Exception]]:
    tree = _device_tree()
    tree["/redfish/v1/Chassis"] = [
        _response(
            HTTPStatus.OK,
            {
                "Members": [
                    {"@odata.id": "/redfish/v1/Chassis/1"},
                    {"@odata.id": "/redfish/v1/Chassis/2"},
                ]
            },
        )
    ]
    tree["/redfish/v1/Chassis/1"] = [
        _response(HTTPStatus.OK, {"Id": "1", "Power": {"@odata.id": "/redfish/v1/Chassis/1/Power"}})
    ]
    tree["/redfish/v1/Chassis/1/Power"] = [_response(HTTPStatus.OK, {"Id": "Power-1"})]
    tree["/redfish/v1/Chassis/2"] = [second]
    return tree


def test_get_information_skips_unavailable_chassis_member(
    capsys: pytest.CaptureFixture[str],
) -> None:
    redfishobj = _agent(_two_chassis_tree(_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY)))
    redfishobj.sections = {"Storage", "Drives", "Power"}

    _run(redfishobj)

    assert '"Id": "Power-1"' in capsys.readouterr().out


def test_get_information_does_not_persist_sections_next_to_a_skipped_chassis(
    capsys: pytest.CaptureFixture[str],
) -> None:
    redfishobj = _agent(_two_chassis_tree(_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY)))
    redfishobj.sections = {"Storage", "Drives", "Power"}

    _run(redfishobj)

    assert "<<<redfish_power:sep(0)>>>" in capsys.readouterr().out


def test_get_information_leaves_out_power_a_skipped_chassis_may_supply(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _two_chassis_tree(_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY))
    tree["/redfish/v1/Chassis/1"] = [_response(HTTPStatus.OK, {"Id": "1"})]
    redfishobj = _agent(tree)
    redfishobj.sections = {"Storage", "Drives", "Power"}

    _run(redfishobj)

    out = capsys.readouterr().out
    assert "<<<redfish_chassis:sep(0)>>>" in out
    assert "<<<redfish_power" not in out


def test_get_information_leaves_out_sections_of_a_chassis_that_cannot_be_fetched(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree["/redfish/v1/Chassis"] = [
        _response(HTTPStatus.OK, {"Members": [{"@odata.id": "/redfish/v1/Chassis/1"}]})
    ]
    tree["/redfish/v1/Chassis/1"] = [_response(HTTPStatus.NOT_FOUND)]
    redfishobj = _agent(tree)
    redfishobj.sections = {"Storage", "Drives", "Power"}

    _run(redfishobj)

    out = capsys.readouterr().out
    assert "<<<redfish_chassis:sep(0)>>>" in out
    assert "<<<redfish_power" not in out


def test_get_information_aborts_if_no_chassis_member_is_usable() -> None:
    tree = _two_chassis_tree(_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY))
    tree["/redfish/v1/Chassis/1"] = [_response(HTTPStatus.NOT_FOUND)]

    with pytest.raises(agent_redfish.TemporarilyUnavailable):
        _run(_agent(tree))


def _hp_device_tree(second_manager: mock.Mock) -> dict[str, list[mock.Mock | Exception]]:
    """An iLO 4: vendor "Hp" fetches the Managers collection without $expand"""
    smart_storage = "/redfish/v1/Systems/1/SmartStorage"
    tree = _device_tree()
    tree["/redfish/v1"] = [
        _response(
            HTTPStatus.OK,
            {
                "Oem": {"Hp": {}},
                "Managers": {"@odata.id": "/redfish/v1/Managers"},
                "Systems": {"@odata.id": "/redfish/v1/Systems"},
                "Chassis": {"@odata.id": "/redfish/v1/Chassis"},
            },
        )
    ]
    tree["/redfish/v1/Managers"] = [
        _response(
            HTTPStatus.OK,
            {
                "Members": [
                    {"@odata.id": "/redfish/v1/Managers/1"},
                    {"@odata.id": "/redfish/v1/Managers/2"},
                ]
            },
        )
    ]
    tree["/redfish/v1/Managers/1"] = [
        _response(HTTPStatus.OK, {"Oem": {"Hp": {}}, "FirmwareVersion": "iLO 4 v2.80"})
    ]
    tree["/redfish/v1/Managers/2"] = [second_manager]
    tree["/redfish/v1/Systems/1"] = [
        _response(
            HTTPStatus.OK,
            {"Id": "1", "Oem": {"Hp": {"Links": {"SmartStorage": {"@odata.id": smart_storage}}}}},
        )
    ]
    tree[smart_storage] = [
        _response(
            HTTPStatus.OK,
            {"Links": {"ArrayControllers": {"@odata.id": f"{smart_storage}/ArrayControllers"}}},
        )
    ]
    tree[f"{smart_storage}/ArrayControllers"] = [_response(HTTPStatus.OK, {"Id": "Controller-0"})]
    return tree


def test_get_information_skips_unavailable_manager_member(
    capsys: pytest.CaptureFixture[str],
) -> None:
    redfishobj = _agent(_hp_device_tree(_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY)))
    redfishobj.sections = {"SmartStorage", "ArrayControllers"}

    _run(redfishobj)

    # the HP specific SmartStorage is only fetched if the available manager identifies the model
    assert '"Id": "Controller-0"' in capsys.readouterr().out


def _hpe_device_tree() -> dict[str, list[mock.Mock | Exception]]:
    return {
        "/redfish/v1": [
            _response(
                HTTPStatus.OK,
                {
                    "Oem": {"Hpe": {}},
                    "Managers": {"@odata.id": "/redfish/v1/Managers"},
                    "Systems": {"@odata.id": "/redfish/v1/Systems"},
                    "Chassis": {"@odata.id": "/redfish/v1/Chassis"},
                },
            )
        ],
        "/redfish/v1/Managers?$expand=.": [
            _response(
                HTTPStatus.OK, {"Members": [{"Oem": {"Hpe": {}}, "FirmwareVersion": "iLO 5 v2.72"}]}
            )
        ],
        "/redfish/v1/Systems": [
            _response(HTTPStatus.OK, {"Members": [{"@odata.id": "/redfish/v1/Systems/1"}]})
        ],
        "/redfish/v1/Systems/1": [
            _response(
                HTTPStatus.OK,
                {
                    "Id": "1",
                    "Oem": {
                        "Hpe": {
                            "Links": {
                                "SmartStorage": {"@odata.id": "/redfish/v1/Systems/1/SmartStorage"}
                            }
                        }
                    },
                },
            )
        ],
        "/redfish/v1/Systems/1/SmartStorage": [_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY)],
        "/redfish/v1/Chassis": [_response(HTTPStatus.OK, {"Members": []})],
    }


def test_get_information_leaves_out_unavailable_hpe_smartstorage_and_its_drives(
    capsys: pytest.CaptureFixture[str],
) -> None:
    redfishobj = _agent(_hpe_device_tree())
    redfishobj.sections = {
        "SmartStorage",
        "ArrayControllers",
        "HostBusAdapters",
        "LogicalDrives",
        "PhysicalDrives",
    }

    _run(redfishobj)

    out = capsys.readouterr().out
    assert "<<<redfish_chassis:sep(0)>>>" in out
    assert "<<<redfish_arraycontrollers" not in out
    assert "<<<redfish_physicaldrives" not in out


def test_get_information_leaves_out_section_whose_fetch_failed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree[_STORAGE] = [TimeoutError("read timed out")]

    _run(_agent(tree, debug=False))

    out = capsys.readouterr().out
    assert "<<<redfish_system:sep(0)>>>" in out
    assert "<<<redfish_storage" not in out
    assert "<<<redfish_drives" not in out


def test_get_information_leaves_out_drives_whose_fetch_failed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree[f"{_STORAGE}/Drives/0"] = [TimeoutError("read timed out")]

    _run(_agent(tree, debug=False))

    out = capsys.readouterr().out
    assert "<<<redfish_storage:sep(0):persist(" in out
    assert "<<<redfish_drives" not in out


def test_get_information_does_not_cache_section_whose_fetch_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    tree = _device_tree()
    tree[_FIRMWARE] = [TimeoutError("read timed out")]
    redfishobj = _agent(tree, debug=False)
    redfishobj.cache_per_section = {"FirmwareInventory": 3600}

    _run(redfishobj)

    storage = Storage(agent_redfish.AGENT, redfishobj.hostname)
    assert storage.read("FirmwareInventory", None) is None


def test_get_information_emits_no_empty_sections_after_a_failed_phase(
    capsys: pytest.CaptureFixture[str],
) -> None:
    tree = _device_tree()
    tree["/redfish/v1/Chassis"] = [
        _response(HTTPStatus.OK, {"Members": [{"@odata.id": "/redfish/v1/Chassis/1"}]})
    ]
    tree["/redfish/v1/Chassis/1"] = [TimeoutError("read timed out")]
    redfishobj = _agent(tree, debug=False)
    redfishobj.sections = {"Storage", "Drives", "Power"}

    _run(redfishobj)

    out = capsys.readouterr().out
    assert "<<<redfish_storage:sep(0):persist(" in out
    assert "<<<redfish_power" not in out


def test_get_information_keeps_cached_dependents_of_unavailable_section(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path))
    tree = _device_tree()
    tree[_STORAGE] = [_response(HTTPStatus.BAD_REQUEST, _ILO_NOT_READY)]
    redfishobj = _agent(tree)
    redfishobj.cache_per_section = {"Drives": 300}
    cached_at = int(time.time())
    Storage(agent_redfish.AGENT, redfishobj.hostname).write(
        "Drives", json.dumps({"timestamp": cached_at, "data": [{"Id": "0"}]})
    )

    _run(redfishobj)

    assert f"<<<redfish_drives:sep(0):cached({cached_at},300)>>>" in capsys.readouterr().out


def _set_up_site_files(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SERVER_SIDE_PROGRAM_STORAGE_PATH", str(tmp_path / "storage"))
    key_file = tmp_path / "password_store.secret"
    key_file.write_bytes(b"a" * 32)
    monkeypatch.setenv("PASSWORD_STORE_SECRET_FILE", str(key_file))


def _stored_bytes(tmp_path: Path) -> bytes:
    """Everything the agent stored, whatever the key and format."""
    return b"".join(f.read_bytes() for f in (tmp_path / "storage").rglob("*") if f.is_file())


@pytest.fixture(name="secrets")
def _secrets(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> ObfuscatedStorage[Secret[str]]:
    _set_up_site_files(monkeypatch, tmp_path)
    return ObfuscatedStorage(agent_redfish.AGENT, "bmc-1", Obfuscator())


def test_client_session_loadf_ignores_empty_session_file(
    secrets: ObfuscatedStorage[Secret[str]],
) -> None:
    Storage(agent_redfish.AGENT, "bmc-1").write("session", "")

    assert agent_redfish.ClientSession.loadf(secrets) is None


class _SessionClient:
    """Logs in with a new session, and accepts only the session it handed out last."""

    def __init__(self, valid_key: str | None = None) -> None:
        self.logins = 0
        self._valid_key = valid_key
        self._key: str | None = None

    def login(self, **_kw: str) -> None:
        self.logins += 1
        self._key = self._valid_key = "secret-session-key"

    def get_session_location(self) -> str:
        return "/redfish/v1/SessionService/Sessions/1"

    def get_session_key(self) -> str | None:
        return self._key

    def set_session_location(self, location: str | None) -> None:
        pass

    def set_session_key(self, key: str | None) -> None:
        self._key = key

    def get(self, _url: str, _timeout: int | None) -> mock.Mock:
        ok = self._key is not None and self._key == self._valid_key
        return mock.Mock(status=HTTPStatus.OK if ok else HTTPStatus.UNAUTHORIZED)


def test_the_session_is_reused_by_the_next_run(secrets: ObfuscatedStorage[Secret[str]]) -> None:
    agent_redfish.RedfishClient(_SessionClient()).make_session(secrets, auth="session")
    client = _SessionClient(valid_key="secret-session-key")

    agent_redfish.RedfishClient(client).make_session(secrets, auth="session")

    assert client.logins == 0


def test_the_session_is_not_stored_in_plain_text(
    secrets: ObfuscatedStorage[Secret[str]], tmp_path: Path
) -> None:
    agent_redfish.RedfishClient(_SessionClient()).make_session(secrets, auth="session")

    stored = _stored_bytes(tmp_path)
    assert stored
    assert b"secret-session-key" not in stored


class _SessionRefusingClient:
    def login(self, **_kw: str) -> None:
        raise SessionCreationError("HTTP 404: Failed to create the session")


def test_refused_session_is_reported_as_login_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _set_up_site_files(monkeypatch, tmp_path)
    monkeypatch.setattr(agent_redfish, "redfish_client", lambda **_kw: _SessionRefusingClient())
    args = agent_redfish.parse_arguments(["-u", "user", "--password", "secret", "bmc"])

    with pytest.raises(agent_redfish.CannotRecover, match="Login failed"):
        agent_redfish.get_session(args)
