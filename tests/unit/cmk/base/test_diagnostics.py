#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import tarfile
from collections.abc import Callable, Iterable, Mapping, Sequence
from pathlib import Path, PurePosixPath

import pytest

from cmk.base import diagnostics
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
    Topic,
    VerbatimCopy,
)


def _make_context(tmp_path: Path, logger: diagnostics.ConsoleLogger) -> CollectContext:
    return CollectContext(
        omd_root=tmp_path,
        omd_config={},
        site_id="mySite",
        all_parameters={},
        base_config={},
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
        topic=Topic("Test topic"),
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


def _catalogue() -> Mapping[str, DiagnosticsPlugin]:
    return diagnostics._load_plugin_catalogue(logger=diagnostics.ConsoleLogger())


@pytest.fixture(autouse=True)
def reset_collector_caches() -> None:
    # diagnostics.get_omd_config.cache_clear()
    diagnostics.verify_checkmk_server_host.cache_clear()


#   .--dump----------------------------------------------------------------.
#   |                         _                                            |
#   |                      __| |_   _ _ __ ___  _ __                       |
#   |                     / _` | | | | '_ ` _ \| '_ \                      |
#   |                    | (_| | |_| | | | | | | |_) |                     |
#   |                     \__,_|\__,_|_| |_| |_| .__/                      |
#   |                                          |_|                         |
#   '----------------------------------------------------------------------'


def test_diagnostics_dump_create(tmp_path: Path) -> None:
    catalogue = _catalogue()
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


def _make_cli_plugin(
    name: str, topic: Topic, sensitivity: Sensitivity, *, always: bool = False
) -> DiagnosticsPlugin:
    return DiagnosticsPlugin(
        name=name,
        description=Help("A test plugin"),
        sensitivity=sensitivity,
        topic=topic,
        always=always,
        handler=lambda _context: [],
    )


_CLI_TOPIC_A = Topic("Topic A")
_CLI_TOPIC_B = Topic("Topic B")

_CLI_CATALOGUE = {
    plugin.name: plugin
    for plugin in (
        _make_cli_plugin("always_one", _CLI_TOPIC_A, Sensitivity.LOW, always=True),
        _make_cli_plugin("a_low", _CLI_TOPIC_A, Sensitivity.LOW),
        _make_cli_plugin("a_medium", _CLI_TOPIC_A, Sensitivity.MEDIUM),
        _make_cli_plugin("b_high", _CLI_TOPIC_B, Sensitivity.HIGH),
    )
}


def test_resolve_cli_selection() -> None:
    # no options: only 'always' plugins run (empty explicit selection)
    assert diagnostics._resolve_cli_selection(_CLI_CATALOGUE, {}).plugins == []

    selection = diagnostics._resolve_cli_selection(
        _CLI_CATALOGUE,
        {
            "all-topics": "low",
            "plugins": "b_high",
            "checkmk-server-host": "my_server",
        },
    )
    assert selection.checkmk_server_host == "my_server"
    assert "a_low" in selection.plugins  # low via --all-topics
    assert "a_medium" not in selection.plugins  # medium exceeds the threshold
    assert "b_high" in selection.plugins  # explicitly selected
    assert "always_one" not in selection.plugins  # runs anyway, needs no selection


def test_resolve_cli_selection_rejects_unknown() -> None:
    with pytest.raises(Exception, match="Unknown plugin"):
        diagnostics._resolve_cli_selection(_CLI_CATALOGUE, {"plugins": "nope"})
    with pytest.raises(Exception, match="Invalid sensitivity"):
        diagnostics._resolve_cli_selection(_CLI_CATALOGUE, {"all-topics": "extreme"})


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


@pytest.mark.parametrize(
    "cl_parameters, expected_parameters",
    [
        ([], {}),
        # boolean
        (
            [
                "local-files",
                "omd-config",
                "checkmk-crashes",
                "metric-backend",
            ],
            {
                "local-files": True,
                "omd-config": True,
                "checkmk-crashes": True,
                "metric-backend": True,
            },
        ),
        # files
        (
            [
                "checkmk-config-files",
                "a,b",
                "checkmk-log-files",
                "a,b",
            ],
            {
                "checkmk-config-files": ["a", "b"],
                "checkmk-log-files": ["a", "b"],
            },
        ),
        # with host
        (
            [
                "performance-graphs",
                "myhost",
                "checkmk-overview",
                "myhost",
            ],
            {
                "performance-graphs": "myhost",
                "checkmk-overview": "myhost",
            },
        ),
    ],
)
def test_legacy_deserialize_cl_parameters(
    cl_parameters: Sequence[str],
    expected_parameters: Mapping[str, object],
) -> None:
    assert diagnostics.deserialize_cl_parameters(cl_parameters) == expected_parameters


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


def test_legacy_file_list_served_by_native_plugins(tmp_path: Path) -> None:
    """The old wire's explicit file lists are served by the native file plugins"""
    config_dir = tmp_path / "etc/check_mk/test"
    config_dir.mkdir(parents=True)
    (config_dir / "test.conf").write_text("testvar = testvalue")

    catalogue = _catalogue()
    legacy_plugins = diagnostics._legacy_file_plugins(
        {"checkmk-config-files": ["test/test.conf", "no/such/file.mk"]},
        catalogue=catalogue,
    )
    assert [p.name for p in legacy_plugins] == ["config_files"]

    dump, logger = _make_dump(tmp_path, list(legacy_plugins))

    assert "etc/check_mk/test/test.conf" in _tar_names(dump)
    assert "No such files: no/such/file.mk" in logger.content()


def test_legacy_cee_file_options_absent_on_community() -> None:
    """Without the CEE plugins the core/licensing options are silently unavailable"""
    catalogue = _catalogue()
    legacy_plugins = diagnostics._legacy_file_plugins(
        {
            "checkmk-core-files": ["core/history"],
            "checkmk-licensing-files": ["licensing/history.json"],
        },
        catalogue=catalogue,
    )
    assert not legacy_plugins
