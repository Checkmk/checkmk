#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Tests for the mk_inotify agent plug-in.

Keep this module compatible with the oldest Python we support for agent
plug-ins: no f-strings, no variable annotations, no typing imports.
"""

import configparser
import os
import types
from pathlib import Path

import pytest

from agents.plugins import mk_inotify

_ = Path, pytest  # only used in type comments; make ruff happy

GLOBAL_SECTION = """
[global]
heartbeat_timeout=120
write_interval=10
max_messages_per_interval=100
stats_retention=120
"""

MASKS = {
    "access": 1,
    "open": 2,
    "create": 4,
    "delete": 8,
    "modify": 16,
    "movedto": 32,
    "movedfrom": 64,
    "moveself": 128,
}


def _parse(text):
    # type: (str) -> configparser.ConfigParser
    config = configparser.ConfigParser({})
    config.read_string(text)
    return config


def _write(path, content, age=None, now=1000.0):
    # type: (Path, str, float | None, float) -> None
    with open(str(path), "w") as opened:
        opened.write(content)
    if age is not None:
        os.utime(str(path), (now - age, now - age))


def test_plugin_is_importable():
    # type: () -> None
    """Guards against syntax and import-time side effects."""
    assert mk_inotify.__version__


def test_parse_arguments_defaults_to_background():
    # type: () -> None
    assert not mk_inotify.parse_arguments([]).foreground


def test_parse_arguments_g_selects_foreground():
    # type: () -> None
    assert mk_inotify.parse_arguments(["-g"]).foreground


def test_get_paths_uses_environment():
    # type: () -> None
    paths = mk_inotify.get_paths({"MK_CONFDIR": "/c", "MK_VARDIR": "/v"})

    assert paths == mk_inotify.Paths(
        config_file="/c/mk_inotify.cfg",
        configured_paths="/v/mk_inotify.configured",
        pid_file="/v/mk_inotify.pid",
        vardir="/v",
    )


def test_get_paths_falls_back_to_defaults():
    # type: () -> None
    paths = mk_inotify.get_paths({})

    assert paths == mk_inotify.Paths(
        config_file="/etc/check_mk/mk_inotify.cfg",
        configured_paths="/var/lib/check_mk_agent/mk_inotify.configured",
        pid_file="/var/lib/check_mk_agent/mk_inotify.pid",
        vardir="/var/lib/check_mk_agent",
    )


def test_read_global_settings_reads_the_bakery_keys():
    # type: () -> None
    settings = mk_inotify.read_global_settings(_parse(GLOBAL_SECTION))

    assert settings == mk_inotify.GlobalSettings(
        heartbeat_timeout=120,
        write_interval=10,
        max_messages_per_interval=100,
        stats_retention=120,
    )


def test_get_event_masks_resolves_names_on_the_module():
    # type: () -> None
    module = types.SimpleNamespace(
        IN_ACCESS=1,
        IN_OPEN=2,
        IN_CREATE=4,
        IN_DELETE=8,
        IN_MODIFY=16,
        IN_MOVED_TO=32,
        IN_MOVED_FROM=64,
        IN_MOVE_SELF=128,
    )

    assert mk_inotify.get_event_masks(module) == MASKS


def test_compute_folder_configs_file_section_monitors_listed_files():
    # type: () -> None
    config = _parse("[/some/path|file1|file2]\ncreate=1\nopen=1\n")

    folder_config = mk_inotify.compute_folder_configs(config, MASKS)["/some/path"]

    assert folder_config["monitor_files"] == {
        "create": {"file1", "file2"},
        "open": {"file1", "file2"},
    }
    assert folder_config["monitor_all"] == set()
    assert folder_config["mask"] == MASKS["create"] | MASKS["open"]


def test_compute_folder_configs_folder_section_monitors_whole_folder():
    # type: () -> None
    config = _parse("[/some/folder]\ncreate=1\ndelete=1\n")

    folder_config = mk_inotify.compute_folder_configs(config, MASKS)["/some/folder"]

    assert folder_config["monitor_files"] == {}
    assert folder_config["monitor_all"] == {"create", "delete"}
    assert folder_config["mask"] == MASKS["create"] | MASKS["delete"]


def test_compute_folder_configs_folder_wide_disable_removes_mode_from_files():
    # type: () -> None
    config = _parse("[/p|f]\ncreate=1\nopen=1\n[/p]\nopen=0\n")

    folder_config = mk_inotify.compute_folder_configs(config, MASKS)["/p"]

    assert folder_config["monitor_files"] == {"create": {"f"}}
    assert folder_config["mask"] == MASKS["create"]


def test_compute_folder_configs_ignores_global_section():
    # type: () -> None
    assert mk_inotify.compute_folder_configs(_parse(GLOBAL_SECTION), MASKS) == {}


def test_get_watched_files_lists_files_and_folders():
    # type: () -> None
    folder_configs = mk_inotify.compute_folder_configs(
        _parse("[/a|f1]\ncreate=1\n[/a|f1|f2]\nopen=1\n[/b]\ncreate=1\n"), MASKS
    )

    assert mk_inotify.get_watched_files(folder_configs) == {
        "configured\tfile\t/a/f1",
        "configured\tfile\t/a/f2",
        "configured\tfolder\t/b",
    }


def test_output_data_prints_header_and_configured_paths(tmp_path, capsys):
    # type: (Path, pytest.CaptureFixture[str]) -> None
    configured = tmp_path / "mk_inotify.configured"
    _write(configured, "configured\tfolder\t/b\n")

    mk_inotify.output_data(str(tmp_path), str(configured), 120, 1000.0)

    assert capsys.readouterr().out == "<<<inotify:sep(9)>>>\nconfigured\tfolder\t/b\n"


def test_output_data_prints_only_settled_stats_files(tmp_path, capsys):
    # type: (Path, pytest.CaptureFixture[str]) -> None
    _write(tmp_path / "mk_inotify.stats.990", "old\n", age=10)
    _write(tmp_path / "mk_inotify.stats.998", "fresh\n", age=2)

    mk_inotify.output_data(str(tmp_path), str(tmp_path / "missing"), 120, 1000.0)

    assert capsys.readouterr().out == "<<<inotify:sep(9)>>>\nold\n"


def test_output_data_removes_stats_files_older_than_retention(tmp_path):
    # type: (Path) -> None
    _write(tmp_path / "mk_inotify.stats.800", "expired\n", age=200)
    _write(tmp_path / "mk_inotify.stats.950", "kept\n", age=50)

    mk_inotify.output_data(str(tmp_path), str(tmp_path / "missing"), 100, 1000.0)

    assert sorted(os.listdir(str(tmp_path))) == ["mk_inotify.stats.950"]


def _pid_setup(tmp_path, cmdline):
    # type: (Path, str | None) -> tuple[str, str]
    pid_file = tmp_path / "mk_inotify.pid"
    _write(pid_file, "4242")
    proc_dir = tmp_path / "proc"
    if cmdline is not None:
        (proc_dir / "4242").mkdir(parents=True)
        _write(proc_dir / "4242" / "cmdline", cmdline)
    return str(pid_file), str(proc_dir)


def test_is_other_instance_running_without_pid_file(tmp_path):
    # type: (Path) -> None
    assert not mk_inotify.is_other_instance_running(str(tmp_path / "mk_inotify.pid"))


def test_is_other_instance_running_removes_pid_file_of_dead_process(tmp_path):
    # type: (Path) -> None
    pid_file, proc_dir = _pid_setup(tmp_path, cmdline=None)

    assert not mk_inotify.is_other_instance_running(pid_file, proc_dir)
    assert not os.path.exists(pid_file)


def test_is_other_instance_running_removes_pid_file_of_foreign_process(tmp_path):
    # type: (Path) -> None
    pid_file, proc_dir = _pid_setup(tmp_path, cmdline="bash\0")

    assert not mk_inotify.is_other_instance_running(pid_file, proc_dir)
    assert not os.path.exists(pid_file)


def test_is_other_instance_running_detects_live_mk_inotify(tmp_path):
    # type: (Path) -> None
    pid_file, proc_dir = _pid_setup(
        tmp_path, cmdline="python3\0/usr/lib/check_mk_agent/plugins/mk_inotify.py\0"
    )

    assert mk_inotify.is_other_instance_running(pid_file, proc_dir)
    assert os.path.exists(pid_file)


class _Event:
    def __init__(self, path, pathname, is_dir=False):
        # type: (str, str, bool) -> None
        self.path = path
        self.pathname = pathname
        self.dir = is_dir


def _monitor(vardir, foreground=False, max_messages=100):
    # type: (Path, bool, int) -> mk_inotify.Monitor
    folder_configs = mk_inotify.compute_folder_configs(
        _parse("[/w|f]\ncreate=1\n[/w]\nmodify=1\n"), MASKS
    )
    settings = mk_inotify.GlobalSettings(
        heartbeat_timeout=120,
        write_interval=10,
        max_messages_per_interval=max_messages,
        stats_retention=120,
    )
    paths = mk_inotify.get_paths({"MK_CONFDIR": str(vardir), "MK_VARDIR": str(vardir)})
    return mk_inotify.Monitor(folder_configs, settings, paths, foreground, None, 0.0)


def _recorded(monitor):
    # type: (mk_inotify.Monitor) -> list[list[str]]
    """The buffered lines without their timestamp column"""
    return [line.split("\t")[1:] for line in monitor.output]


def test_handle_event_records_configured_file_event(tmp_path):
    # type: (Path) -> None
    monitor = _monitor(tmp_path)

    monitor.handle_event("create", _Event("/w", "/w/f"))

    assert _recorded(monitor) == [["create", "/w/f"]]


def test_handle_event_records_folder_wide_mode_for_any_file(tmp_path):
    # type: (Path) -> None
    monitor = _monitor(tmp_path)

    monitor.handle_event("modify", _Event("/w", "/w/other"))

    assert _recorded(monitor) == [["modify", "/w/other"]]


def test_handle_event_ignores_unconfigured_mode(tmp_path):
    # type: (Path) -> None
    monitor = _monitor(tmp_path)

    monitor.handle_event("open", _Event("/w", "/w/f"))

    assert monitor.output == []


def test_handle_event_ignores_directory_events(tmp_path):
    # type: (Path) -> None
    monitor = _monitor(tmp_path)

    monitor.handle_event("create", _Event("/w", "/w/f", is_dir=True))

    assert monitor.output == []


def test_handle_event_ignores_unknown_folder(tmp_path):
    # type: (Path) -> None
    monitor = _monitor(tmp_path)

    monitor.handle_event("create", _Event("/other", "/other/f"))

    assert monitor.output == []


def test_handle_event_appends_limit_warning_once(tmp_path):
    # type: (Path) -> None
    monitor = _monitor(tmp_path, max_messages=1)

    for _ in range(4):
        monitor.handle_event("create", _Event("/w", "/w/f"))

    assert _recorded(monitor) == [
        ["create", "/w/f"],
        ["create", "/w/f"],
        ["Maximum messages reached: 1 per 10 seconds"],
    ]
    assert monitor.output[-1].startswith("warning\t")


def test_handle_event_in_foreground_prints_the_line(tmp_path, capsys):
    # type: (Path, pytest.CaptureFixture[str]) -> None
    monitor = _monitor(tmp_path, foreground=True)

    monitor.handle_event("create", _Event("/w", "/w/f"))

    assert capsys.readouterr().out == monitor.output[0] + "\n"


def test_flush_in_foreground_prints_lines_and_watched_files(tmp_path, capsys):
    # type: (Path, pytest.CaptureFixture[str]) -> None
    monitor = _monitor(tmp_path, foreground=True)
    monitor.handle_event("create", _Event("/w", "/w/f"))
    line = monitor.output[0]
    capsys.readouterr()

    monitor.flush(1234.0)

    assert set(capsys.readouterr().out.splitlines()) == {
        line,
        "configured\tfile\t/w/f",
        "configured\tfolder\t/w",
    }
    assert monitor.output == []


def test_flush_in_background_writes_stats_file(tmp_path):
    # type: (Path) -> None
    monitor = _monitor(tmp_path)
    monitor.handle_event("create", _Event("/w", "/w/f"))
    line = monitor.output[0]

    monitor.flush(1234.0)

    with open(str(tmp_path / "mk_inotify.stats.1234")) as stats_file:
        assert stats_file.read() == line + "\n"
    assert monitor.output == []


def test_flush_without_buffered_lines_writes_nothing(tmp_path, capsys):
    # type: (Path, pytest.CaptureFixture[str]) -> None
    monitor = _monitor(tmp_path)

    monitor.flush(1234.0)

    assert os.listdir(str(tmp_path)) == []
    assert capsys.readouterr().out == ""


class _ProcessEvent:
    """Mimics pyinotify.ProcessEvent's constructor contract"""

    def __init__(self, **kwargs):
        # type: (object) -> None
        self.my_init(**kwargs)

    def my_init(self, **kwargs):
        # type: (object) -> None
        raise NotImplementedError


def test_event_handler_dispatches_to_monitor(tmp_path):
    # type: (Path) -> None
    monitor = _monitor(tmp_path)
    handler_class = mk_inotify.make_event_handler_class(
        types.SimpleNamespace(ProcessEvent=_ProcessEvent)
    )

    handler_class(monitor=monitor).process_IN_CREATE(_Event("/w", "/w/f"))

    assert _recorded(monitor) == [["create", "/w/f"]]
