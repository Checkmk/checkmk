#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import json
import shutil
import tarfile
import uuid
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import NamedTuple

import pytest
import requests

import cmk.livestatus_client as livestatus
import cmk.utils.paths
from cmk.base import diagnostics
from cmk.ccc.version import Edition
from cmk.crash import make_crash_report_base_path
from cmk.diagnostics.internal import (
    CollectContext,
    CollectError,
    CollectInfo,
    CollectWarning,
    DiagnosticsPlugin,
    DumpItem,
    GeneratedContent,
    Help,
    Sensitivity,
    VerbatimCopy,
)
from tests.testlib.common.empty_config import EMPTY_CONFIG


def _make_context(tmp_path: Path, logger: diagnostics.ConsoleLogger) -> CollectContext:
    return CollectContext(
        omd_root=tmp_path,
        omd_config={},
        all_parameters={},
        core_performance_settings={},
        resolve_checkmk_server_host=lambda: "checkmk_server",
        site_internal_auth_header=lambda: "InternalToken deadbeef",
        log=logger,
    )


def _make_plugin(
    name: str,
    handler: Callable[[CollectContext], Iterable[DumpItem]],
) -> DiagnosticsPlugin:
    return DiagnosticsPlugin(
        name=name,
        description=Help("A test plugin"),
        sensitivity=Sensitivity.LOW,
        topic=diagnostics._TOPIC_GENERAL,
        handler=handler,
    )


def _make_dump(
    tmp_path: Path, plugins: Sequence[DiagnosticsPlugin]
) -> tuple[diagnostics.DiagnosticsDump, diagnostics.ConsoleLogger]:
    logger = diagnostics.ConsoleLogger()
    dump = diagnostics.DiagnosticsDump(
        plugins=plugins,
        context=_make_context(tmp_path, logger),
        logger=logger,
        diagnostics_dir=tmp_path / "var/check_mk/diagnostics",
        omd_root=tmp_path,
    )
    return dump, logger


def _tar_names(dump: diagnostics.DiagnosticsDump) -> Sequence[str]:
    with tarfile.open(dump.tarfile_path) as tar:
        return tar.getnames()


def _full_catalogue(tmp_path: Path) -> Mapping[str, DiagnosticsPlugin]:
    return diagnostics._load_plugin_catalogue(
        edition=Edition.COMMUNITY,
        loaded_config=EMPTY_CONFIG,
        core_performance_settings=lambda x: {},
        omd_config={},
        tmp_parent=tmp_path,
        logger=diagnostics.ConsoleLogger(),
    )


def _adapter_catalogue(tmp_path: Path) -> Mapping[str, DiagnosticsPlugin]:
    return diagnostics._adapter_plugin_catalogue(
        edition=Edition.COMMUNITY,
        loaded_config=EMPTY_CONFIG,
        core_performance_settings=lambda x: {},
        omd_config={},
        tmp_parent=tmp_path,
    )


@pytest.fixture(autouse=True)
def reset_collector_caches() -> None:
    # diagnostics.get_omd_config.cache_clear()
    diagnostics.verify_checkmk_server_host.cache_clear()


@pytest.fixture()
def _fake_local_connection(host_list: Sequence[Sequence[str]]) -> Callable:
    class FakeLocalConnection:
        def query(self, query: str) -> Sequence[Sequence[str]]:
            return host_list

    def _wrapper(host_list: Sequence[Sequence[str]]) -> type[FakeLocalConnection]:
        return FakeLocalConnection

    return _wrapper


#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def test_adapter_catalogue_names(tmp_path: Path) -> None:
    assert set(_adapter_catalogue(tmp_path)) == {
        "bi_runtime_data",
        "core_performance_metrics",
        "latest_crash_reports",
        "metric_backend_state",
        "mkp_inventory",
        "otel_license_counts",
    }


def test_diagnostics_dump_create(tmp_path: Path) -> None:
    catalogue = _full_catalogue(tmp_path)
    dump, _logger = _make_dump(tmp_path, [catalogue["environment_variables"]])

    assert dump.dump_folder.exists()
    assert dump.dump_folder.name == "diagnostics"
    assert dump.tarfile_created

    tarfiles = list(dump.dump_folder.iterdir())
    assert len(tarfiles) == 1
    assert all(t.suffix == ".gz" for t in tarfiles)
    assert "environment.json" in _tar_names(dump)


def test_dump_packs_generated_and_verbatim_content(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("verbatim content")

    def handler(_context: CollectContext) -> Iterable[DumpItem]:
        yield DumpItem(PurePosixPath("generated/a.json"), GeneratedContent(b'{"key": "value"}'))
        yield DumpItem(PurePosixPath("copied/source.txt"), VerbatimCopy(source))

    dump, _logger = _make_dump(tmp_path, [_make_plugin("test_plugin", handler)])

    with tarfile.open(dump.tarfile_path) as tar:
        names = tar.getnames()
        assert "generated/a.json" in names
        assert "copied/source.txt" in names
        generated = tar.extractfile("generated/a.json")
        assert generated is not None and generated.read() == b'{"key": "value"}'
        copied = tar.extractfile("copied/source.txt")
        assert copied is not None and copied.read() == b"verbatim content"


def test_dump_arcname_collision_first_wins(tmp_path: Path) -> None:
    def handler_one(_context: CollectContext) -> Iterable[DumpItem]:
        yield DumpItem(PurePosixPath("shared.txt"), GeneratedContent(b"one"))

    def handler_two(_context: CollectContext) -> Iterable[DumpItem]:
        yield DumpItem(PurePosixPath("shared.txt"), GeneratedContent(b"two"))

    dump, logger = _make_dump(
        tmp_path,
        [_make_plugin("one", handler_one), _make_plugin("two", handler_two)],
    )

    with tarfile.open(dump.tarfile_path) as tar:
        shared = tar.extractfile("shared.txt")
        assert shared is not None and shared.read() == b"one"
    assert "already collected by 'one'" in logger.content()


def test_dump_rejects_invalid_arcnames(tmp_path: Path) -> None:
    def handler(_context: CollectContext) -> Iterable[DumpItem]:
        yield DumpItem(PurePosixPath("/absolute.txt"), GeneratedContent(b"nope"))
        yield DumpItem(PurePosixPath("../escape.txt"), GeneratedContent(b"nope"))

    dump, logger = _make_dump(tmp_path, [_make_plugin("test_plugin", handler)])

    assert not dump.tarfile_created
    assert not dump.tarfile_path.exists()
    assert "invalid file path" in logger.content()


@pytest.mark.parametrize(
    ["exception", "marker"],
    [
        (CollectInfo("nothing to do"), "INFO"),
        (CollectWarning("something odd"), "WARNING"),
        (CollectError("it broke"), "ERROR"),
        (RuntimeError("unexpected"), "RuntimeError"),
    ],
)
def test_dump_logs_collect_exceptions(tmp_path: Path, exception: Exception, marker: str) -> None:
    def handler(_context: CollectContext) -> Iterable[DumpItem]:
        yield DumpItem(PurePosixPath("before.txt"), GeneratedContent(b"kept"))
        raise exception

    dump, logger = _make_dump(tmp_path, [_make_plugin("test_plugin", handler)])

    # files yielded before the exception stay in the dump
    assert "before.txt" in _tar_names(dump)
    assert str(exception) in logger.content() or marker in logger.content()


def test_resolve_cli_selection(tmp_path: Path) -> None:
    catalogue = _full_catalogue(tmp_path)

    # no options: only 'always' plugins run (empty explicit selection)
    assert diagnostics._resolve_cli_selection(catalogue, {}).plugins == []

    selection = diagnostics._resolve_cli_selection(
        catalogue,
        {
            "all-topics": "low",
            "plugins": "latest_crash_reports",
            "checkmk-server-host": "my_server",
        },
    )
    assert selection.checkmk_server_host == "my_server"
    assert "mkp_inventory" in selection.plugins  # low via --all-topics
    assert "environment_variables" not in selection.plugins  # medium exceeds the threshold
    assert "latest_crash_reports" in selection.plugins  # explicitly selected


def test_resolve_cli_selection_rejects_unknown(tmp_path: Path) -> None:
    catalogue = _full_catalogue(tmp_path)
    with pytest.raises(Exception, match="Unknown plugin"):
        diagnostics._resolve_cli_selection(catalogue, {"plugins": "nope"})
    with pytest.raises(Exception, match="Invalid sensitivity"):
        diagnostics._resolve_cli_selection(catalogue, {"all-topics": "extreme"})


def test_legacy_selection() -> None:
    selected, host = diagnostics._legacy_selection(
        {
            "local-files": True,
            "checkmk-crashes": True,
            "checkmk-overview": "my_server",
        }
    )
    assert selected == {
        # implicitly selected: unconditional in the old engine
        "core_performance_metrics",
        "environment_variables",
        "network_state",
        "processes_and_logins",
        # explicitly selected
        "mkp_inventory",
        "latest_crash_reports",
        "checkmk_overview",
    }
    assert host == "my_server"


def test_diagnostics_cleanup_dump_folder(tmp_path: Path) -> None:
    dump, _logger = _make_dump(tmp_path, [])
    # Fake existing tarfiles
    for nr in range(10):
        dump.dump_folder.joinpath("dummy-%s.tar.gz" % nr).touch()

    dump._cleanup_dump_folder(tmp_path)

    tarfiles = list(dump.dump_folder.iterdir())
    assert len(tarfiles) == dump._keep_num_dumps
    assert all(t.suffixes[-1] == ".gz" for t in tarfiles)


# .
#   .--elements------------------------------------------------------------.
#   |                   _                           _                      |
#   |               ___| | ___ _ __ ___   ___ _ __ | |_ ___                |
#   |              / _ \ |/ _ \ '_ ` _ \ / _ \ '_ \| __/ __|               |
#   |             |  __/ |  __/ | | | | |  __/ | | | |_\__ \               |
#   |              \___|_|\___|_| |_| |_|\___|_| |_|\__|___/               |
#   |                                                                      |
#   '----------------------------------------------------------------------'


def test_diagnostics_element_perfdata() -> None:
    diagnostics_element = diagnostics.PerfDataDiagnosticsElement(
        EMPTY_CONFIG,
        core_performance_settings=lambda x: {},
    )
    assert diagnostics_element.filename == "perfdata.json"
    assert diagnostics_element.title == "Metrics"
    assert diagnostics_element.description == (
        "Metrics related to sizing, e.g. number of helpers, hosts, services"
    )


def test_legacy_file_list_served_by_native_plugins(tmp_path: Path) -> None:
    """The old wire's explicit file lists are served by the native file plugins"""
    config_dir = tmp_path / "etc/check_mk/test"
    config_dir.mkdir(parents=True)
    (config_dir / "test.conf").write_text("testvar = testvalue")

    catalogue = _full_catalogue(tmp_path)
    legacy_plugins = diagnostics._legacy_file_plugins(
        {"checkmk-config-files": ["test/test.conf", "no/such/file.mk"]},
        catalogue=catalogue,
        edition=Edition.COMMUNITY,
        tmp_parent=tmp_path,
    )
    assert [p.name for p in legacy_plugins] == ["config_files"]

    dump, logger = _make_dump(tmp_path, list(legacy_plugins))

    assert "etc/check_mk/test/test.conf" in _tar_names(dump)
    assert "No such files: no/such/file.mk" in logger.content()


@pytest.mark.parametrize(
    "host_list, status_code, text, content, warning, error",
    [
        # no Checkmk server
        ([], 123, "", b"", "No Checkmk server found", None),
        ([], 200, "<html>foo bar</html>", b"", "No Checkmk server found", None),
        ([], 200, "", b"", "No Checkmk server found", None),
        ([], 200, "", b"%PDF-", "No Checkmk server found", None),
        # Checkmk server
        ([["checkmk-server-name"]], 123, "", b"", None, "HTTP error - 123 ()"),
        (
            [["checkmk-server-name"]],
            200,
            "<html>foo bar</html>",
            b"",
            None,
            "Login failed - Invalid automation user or secret",
        ),
        (
            [["checkmk-server-name"]],
            200,
            "",
            b"",
            None,
            "Verification of PDF document header failed",
        ),
    ],
)
def test_diagnostics_element_performance_graphs_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    _fake_local_connection: Callable,
    host_list: Sequence[Sequence[str]],
    status_code: int,
    text: str,
    content: str,
    warning: str | None,
    error: str | None,
) -> None:
    omd_config = {
        "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
        "CONFIG_APACHE_TCP_PORT": "5000",
    }
    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement("", omd_config=omd_config)

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    class FakeResponse(NamedTuple):
        status_code: int
        text: str
        content: str

    monkeypatch.setattr(
        requests, "post", lambda *arg, **kwargs: FakeResponse(status_code, text, content)
    )

    automation_dir = cmk.utils.paths.var_dir / "web/automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    with automation_dir.joinpath("automation.secret").open("w") as f:
        f.write("my-123-password")

    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)

    if warning:
        with pytest.raises(diagnostics.DiagnosticsElementWarning) as w:
            next(
                diagnostics_element.add_or_get_files(
                    omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder
                )
            )
            assert warning == str(w)

    if error:
        with pytest.raises(diagnostics.DiagnosticsElementError) as e:
            next(
                diagnostics_element.add_or_get_files(
                    omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder
                )
            )
            assert error == str(e)

    shutil.rmtree(str(automation_dir))


@pytest.mark.parametrize(
    "host_list, status_code, text, content",
    [
        ([["checkmk-server-name"]], 200, "", b"%PDF-"),
    ],
)
def test_diagnostics_element_performance_graphs_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    _fake_local_connection: Callable,
    host_list: Sequence[Sequence[str]],
    status_code: int,
    text: str,
    content: str,
) -> None:
    omd_config = {
        "CONFIG_APACHE_TCP_ADDR": "127.0.0.1",
        "CONFIG_APACHE_TCP_PORT": "5000",
    }
    diagnostics_element = diagnostics.PerformanceGraphsDiagnosticsElement("", omd_config=omd_config)

    monkeypatch.setattr(livestatus, "LocalConnection", _fake_local_connection(host_list))

    class FakeResponse(NamedTuple):
        status_code: int
        text: str
        content: str

    monkeypatch.setattr(
        requests, "post", lambda *arg, **kwargs: FakeResponse(status_code, text, content)
    )

    automation_dir = cmk.utils.paths.var_dir / "web/automation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    with automation_dir.joinpath("automation.secret").open("w") as f:
        f.write("my-123-password")

    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    filepath = next(
        diagnostics_element.add_or_get_files(omd_root=tmp_path, tmp_dump_folder=tmp_dump_folder)
    )

    assert isinstance(filepath, Path)
    assert filepath == tmp_dump_folder.joinpath("performance_graphs.pdf")

    shutil.rmtree(str(automation_dir))


def test_diagnostics_element_crash_dumps_content(tmp_path: Path) -> None:
    omd_root = tmp_path.joinpath("omd_root")
    test_uuid = str(uuid.uuid4())
    category = "checks"
    test_crash_dir = make_crash_report_base_path(omd_root).joinpath(category).joinpath(test_uuid)
    test_crash_dir.mkdir(parents=True, exist_ok=True)
    test_crash_filepath = test_crash_dir.joinpath("info.json")
    with test_crash_filepath.open("w", encoding="utf-8") as f:
        f.write('{ "testvar": "testvalue"}')

    diagnostics_element = diagnostics.CrashDumpsDiagnosticsElement()
    tmp_dump_folder = tmp_path.joinpath("tmp")
    tmp_dump_folder.mkdir(parents=True, exist_ok=True)
    filepath = next(
        diagnostics_element.add_or_get_files(omd_root=omd_root, tmp_dump_folder=tmp_dump_folder)
    )

    relative_path = make_crash_report_base_path(omd_root).relative_to(omd_root)
    test_filename = f"{test_uuid}.tar.gz"
    assert filepath == tmp_dump_folder.joinpath(relative_path).joinpath(
        f"{category}/{test_filename}"
    )

    import tarfile

    assert tarfile.is_tarfile(filepath)
    with tarfile.open(filepath, "r") as tar:
        tar.extractall(path=tmp_path, filter="data")
        with tmp_path.joinpath("info.json").open("r", encoding="utf-8") as f:
            content = f.read()

    assert json.loads(content)["testvar"] == "testvalue"
