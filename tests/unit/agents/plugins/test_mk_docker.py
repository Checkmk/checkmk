#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Regression tests for mk_docker.py's per-container multiprocessing.

Python 3.14 changed the default multiprocessing start method on POSIX from "fork" to
"forkserver". Under "fork", multiprocessing.Process(args=...) never needs to pickle its
arguments, since a forked child is a copy-on-write clone of the parent. Under
"forkserver" (and "spawn"), the arguments must be pickled to hand them to the child.
mk_docker.py used to pass the live, connected MKDockerClient into each per-container
worker process; that client wraps a requests.Session/UnixHTTPAdapter holding an
unpicklable lambda, so job.start() raised under forkserver and no piggybacked container
data was ever produced, while node-level sections (which don't go through
multiprocessing) kept working fine.
"""

import pickle
from types import ModuleType
from typing import NoReturn

import pytest

from tests.testlib.unit.utils import import_module_hack


@pytest.fixture(name="mk_docker")
def fixture_mk_docker(monkeypatch: pytest.MonkeyPatch) -> ModuleType:
    """Import mk_docker.py fresh, bypassing its "is this a docker host?" import guard.

    The plugin refuses to import unless it detects a docker host (the check right after
    the module docstring) -- correct for a shipped agent plugin, but it must not gate
    testing the plugin's own logic on a CI runner that has no docker daemon.
    """
    monkeypatch.setattr("os.path.isfile", lambda path: path == "/var/lib/docker")
    return import_module_hack("agents/plugins/mk_docker.py")


class _UnpicklableClient:
    """Stands in for a real MKDockerClient.

    A real docker.DockerClient can't be pickled -- its UnixHTTPAdapter holds a lambda
    closure -- so anything resembling it must never be handed to multiprocessing.Process.
    """

    def __init__(
        self, all_containers: dict[str, "_FakeContainer"], node_info: dict[str, str]
    ) -> None:
        self.all_containers = all_containers
        self.node_info = node_info
        self._unpicklable = lambda: None


class _FakeContainer:
    def __init__(self, real_id: str) -> None:
        self.id = real_id


def _capture_process_args(
    monkeypatch: pytest.MonkeyPatch, mk_docker: ModuleType
) -> list[tuple[object, tuple[object, ...]]]:
    """Patch multiprocessing.get_context("fork").Process so call_container_sections
    doesn't actually fork."""
    started: list[tuple[object, tuple[object, ...]]] = []

    class FakeProcess:
        def __init__(self, target: object, args: tuple[object, ...]) -> None:
            started.append((target, args))

        def start(self) -> None:
            pass

        def join(self) -> None:
            pass

    class FakeContext:
        Process = FakeProcess

    monkeypatch.setattr(mk_docker.multiprocessing, "get_context", lambda method=None: FakeContext())
    return started


def test_call_container_sections_never_passes_the_live_client(
    mk_docker: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = _capture_process_args(monkeypatch, mk_docker)
    client = _UnpicklableClient(
        all_containers={"c1": _FakeContainer("realid1"), "c2": _FakeContainer("realid2")},
        node_info={"Name": "node1"},
    )
    config = {"base_url": "unix://var/run/docker.sock", "container_id": "short"}

    mk_docker.call_container_sections(client, config)

    assert len(started) == 2
    for target, args in started:
        assert target is mk_docker._call_single_containers_sections
        assert client not in args
        pickle.dumps(args)  # must not raise -- this is what forkserver/spawn require


def test_call_container_sections_passes_display_id_and_real_docker_id(
    mk_docker: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """container_id: combined keys all_containers by "node_name", which Docker's API
    can't resolve -- the real, resolvable id has to travel to the worker separately."""
    started = _capture_process_args(monkeypatch, mk_docker)
    node_info = {"Name": "node1"}
    client = _UnpicklableClient(
        all_containers={"myhost_web": _FakeContainer("abcd1234fulldockerid")},
        node_info=node_info,
    )
    config = {"base_url": "unix://var/run/docker.sock", "container_id": "combined"}

    mk_docker.call_container_sections(client, config)

    [(_, args)] = started
    assert args == (config, node_info, "myhost_web", "abcd1234fulldockerid")


def test_for_container_scopes_client_to_one_container(
    mk_docker: ModuleType, monkeypatch: pytest.MonkeyPatch
) -> None:
    """for_container must look up the container by its real docker id, not the display
    key -- those two differ whenever container_id: combined is configured."""
    containers_by_real_id = {"abcd1234fulldockerid": object()}

    class _Containers:
        def get(self, real_id: str) -> object:
            return containers_by_real_id[real_id]

    # docker.DockerClient.containers is a read-only property (it builds a fresh
    # ContainerCollection per access), so it has to be replaced at the class level
    # rather than assigned on the instance.
    monkeypatch.setattr(
        mk_docker.docker.DockerClient, "__init__", lambda self, base_url, version=None: None
    )
    monkeypatch.setattr(
        mk_docker.docker.DockerClient, "containers", property(lambda self: _Containers())
    )
    node_info = {"Name": "node1"}

    client = mk_docker.MKDockerClient.for_container(
        {"base_url": "unix://var/run/docker.sock"}, "myhost_web", "abcd1234fulldockerid", node_info
    )

    assert client.node_info is node_info
    assert client.all_containers == {"myhost_web": containers_by_real_id["abcd1234fulldockerid"]}
    assert client._container_stats == {}
    assert client._device_map is None


def test_call_single_containers_sections_reports_and_returns_on_connect_failure(
    mk_docker: ModuleType, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """If a worker can't (re-)connect to the daemon, it must report and return -- not
    raise out of the worker process, which would just silently drop that container.

    Crucially, the report has to be written as a piggyback section for the container,
    not a plain node-level one -- otherwise the container's host just stops getting any
    data instead of showing a visible error."""
    monkeypatch.setattr(mk_docker, "DEBUG", False)

    def raising_for_container(*args: object, **kwargs: object) -> NoReturn:
        raise RuntimeError("boom")

    monkeypatch.setattr(mk_docker.MKDockerClient, "for_container", raising_for_container)

    mk_docker._call_single_containers_sections({}, {"Name": "node1"}, "c1", "realid1")

    out = capsys.readouterr().out
    assert "MKDockerClient.for_container" in out
    assert "boom" in out
    assert "<<<<c1>>>>" in out
    assert "<<<<>>>>" in out


def test_report_exception_to_server_defaults_to_node_level(
    mk_docker: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    """Node-level failures (call_node_sections) must stay un-piggybacked."""
    mk_docker.report_exception_to_server(RuntimeError("boom"), "some_section")

    out = capsys.readouterr().out
    assert "<<<<" not in out
    assert "boom" in out


def test_report_exception_to_server_piggybacks_when_given_a_target(
    mk_docker: ModuleType, capsys: pytest.CaptureFixture[str]
) -> None:
    mk_docker.report_exception_to_server(RuntimeError("boom"), "some_section", piggytarget="c1")

    out = capsys.readouterr().out
    assert "<<<<c1>>>>" in out
    assert "<<<<>>>>" in out
    assert "boom" in out
