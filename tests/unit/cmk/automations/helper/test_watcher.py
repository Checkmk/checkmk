#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import ctypes
import dataclasses
import errno
import logging
import os
import re
import resource
import threading
import time
from collections.abc import Container, Iterator
from pathlib import Path
from typing import Final, override
from unittest.mock import Mock

import pytest
from fakeredis import FakeRedis, FakeServer
from redis.exceptions import TimeoutError as RedisTimeoutError
from watchdog.events import (
    DirCreatedEvent,
    DirDeletedEvent,
    DirModifiedEvent,
    DirMovedEvent,
    FileCreatedEvent,
    FileDeletedEvent,
    FileModifiedEvent,
    FileMovedEvent,
    FileSystemEvent,
)

from cmk.automations.helper import (
    Cache,
    config_from_disk_or_default_config,
    run_watcher,
    WatcherConfig,
)
from cmk.automations.helper._watcher import _AutomationWatcherHandler
from tests.testlib.common.utils import wait_until

# Like real events, the test events carry absolute paths, which the patterns match as a whole.
_WATCHED_MK_PATTERN: Final = "**/*.mk"
_WATCHED_TXT_FILE: Final = "/watched/foo.txt"
_WATCHED_DIRECTORY_PATTERN: Final = "**/some_dir*"
_WATCHED_DIRECTORY = "/watched/some_dir"
_MK_FILE: Final = "/watched/foo.mk"
_OTHER_MK_FILE: Final = "/watched/bar.mk"
_UNMATCHED_FILE: Final = "/watched/foo.bar"


@pytest.fixture(name="file_watcher_handler")
def get_file_watcher_handler(cache: Cache) -> _AutomationWatcherHandler:
    return _AutomationWatcherHandler(
        cache=cache, patterns=[_WATCHED_MK_PATTERN, "**/*.txt"], ignore_directories=True
    )


@pytest.fixture(name="directory_watcher_handler")
def get_directory_watcher_handler(cache: Cache) -> _AutomationWatcherHandler:
    return _AutomationWatcherHandler(
        cache=cache, patterns=[_WATCHED_DIRECTORY_PATTERN], ignore_directories=False
    )


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(
            FileMovedEvent(src_path="", dest_path=_MK_FILE),
            f"Source: n/a, destination: {_MK_FILE}, type: moved",
            id="file moved umwatched to watched directory",
        ),
        pytest.param(
            FileMovedEvent(src_path=_MK_FILE, dest_path=""),
            f"Source: {_MK_FILE}, destination: n/a, type: moved",
            id="file moved from watched to unwatched directory",
        ),
        pytest.param(
            FileMovedEvent(src_path=_MK_FILE, dest_path=_OTHER_MK_FILE),
            f"Source: {_MK_FILE}, destination: {_OTHER_MK_FILE}, type: moved",
            id="file moved within watched directory",
        ),
        pytest.param(
            FileCreatedEvent(src_path=_MK_FILE),
            f"Source: {_MK_FILE}, destination: n/a, type: created",
            id="mk-file created",
        ),
        pytest.param(
            FileCreatedEvent(src_path=_WATCHED_TXT_FILE),
            f"Source: {_WATCHED_TXT_FILE}, destination: n/a, type: created",
            id="txt-file created",
        ),
        pytest.param(
            FileModifiedEvent(src_path=_MK_FILE),
            f"Source: {_MK_FILE}, destination: n/a, type: modified",
            id="file modified",
        ),
        pytest.param(
            FileDeletedEvent(src_path=_MK_FILE),
            f"Source: {_MK_FILE}, destination: n/a, type: deleted",
            id="file deleted",
        ),
    ],
)
def test_automation_watcher_logging_pattern_match(
    caplog: pytest.LogCaptureFixture,
    file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
    output: str,
) -> None:
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)

    assert output in caplog.text


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(
            FileMovedEvent(src_path="", dest_path=_UNMATCHED_FILE), id="no match overwritten"
        ),
        pytest.param(FileCreatedEvent(src_path=_UNMATCHED_FILE), id="no match created"),
        pytest.param(FileModifiedEvent(src_path=_UNMATCHED_FILE), id="no match modified"),
        pytest.param(FileDeletedEvent(src_path=_UNMATCHED_FILE), id="no match deleted"),
    ],
)
def test_automation_watcher_logging_no_match(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)
    assert cache.get_last_detected_change() == last_change_reference
    assert not caplog.text


@pytest.mark.parametrize(
    "event, output",
    [
        pytest.param(
            DirMovedEvent(src_path="", dest_path=_WATCHED_DIRECTORY),
            f"Source: n/a, destination: {_WATCHED_DIRECTORY}, type: moved",
            id="dir moved from unwatched to watched directory",
        ),
        pytest.param(
            DirMovedEvent(src_path=_WATCHED_DIRECTORY, dest_path=""),
            f"Source: {_WATCHED_DIRECTORY}, destination: n/a, type: moved",
            id="dir moved from watched to unwatched directory",
        ),
        pytest.param(
            DirMovedEvent(src_path=_WATCHED_DIRECTORY, dest_path=f"{_WATCHED_DIRECTORY}2"),
            f"Source: {_WATCHED_DIRECTORY}, destination: {_WATCHED_DIRECTORY}2, type: moved",
            id="watched dir moved to watched dir",
        ),
        pytest.param(
            DirCreatedEvent(src_path=_WATCHED_DIRECTORY),
            f"Source: {_WATCHED_DIRECTORY}, destination: n/a, type: created",
            id="dir created",
        ),
        pytest.param(
            DirModifiedEvent(src_path=_WATCHED_DIRECTORY),
            f"Source: {_WATCHED_DIRECTORY}, destination: n/a, type: modified",
            id="dir modified",
        ),
        pytest.param(
            DirDeletedEvent(src_path=_WATCHED_DIRECTORY),
            f"Source: {_WATCHED_DIRECTORY}, destination: n/a, type: deleted",
            id="dir deleted",
        ),
    ],
)
def test_automation_watcher_logging_directory_match(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    directory_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
    output: str,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO):
        directory_watcher_handler.dispatch(event)
    assert cache.get_last_detected_change() > last_change_reference
    assert output in caplog.text


@pytest.mark.parametrize(
    "event",
    [
        pytest.param(
            DirMovedEvent(src_path="", dest_path=_WATCHED_DIRECTORY),
            id="no match dir overwritten",
        ),
        pytest.param(DirCreatedEvent(src_path=_WATCHED_DIRECTORY), id="no match dir created"),
        pytest.param(DirModifiedEvent(src_path=_WATCHED_DIRECTORY), id="no match dir modified"),
        pytest.param(DirDeletedEvent(src_path=_WATCHED_DIRECTORY), id="no match dir deleted"),
    ],
)
def test_automation_watcher_logging_directories_ignored(
    caplog: pytest.LogCaptureFixture,
    cache: Cache,
    file_watcher_handler: _AutomationWatcherHandler,
    event: FileSystemEvent,
) -> None:
    last_change_reference = cache.get_last_detected_change()
    with caplog.at_level(logging.INFO):
        file_watcher_handler.dispatch(event)
    assert cache.get_last_detected_change() == last_change_reference
    assert not caplog.text


def test_error_while_watching_reaches_the_caller(tmp_path: Path, cache: Cache) -> None:
    watcher_config = _site_watcher_config(tmp_path)

    with pytest.raises(RuntimeError, match="server failed"), run_watcher(watcher_config, cache):
        raise RuntimeError("server failed")


@pytest.mark.parametrize(
    "changed_file",
    [
        pytest.param("etc/check_mk/main.mk", id="main.mk"),
        pytest.param("etc/check_mk/local.mk", id="local.mk"),
        pytest.param("etc/check_mk/final.mk", id="final.mk"),
        pytest.param("etc/check_mk/experimental.mk", id="experimental.mk"),
        pytest.param("etc/check_mk/conf.d/wato/rules.mk", id="rules"),
        pytest.param("etc/check_mk/conf.d/wato/hosts.pkl", id="pickled hosts"),
        pytest.param("var/check_mk/autochecks/heute.mk", id="autochecks"),
        pytest.param("var/check_mk/discovered_host_labels/heute.mk", id="host labels"),
        pytest.param("var/check_mk/stored_passwords", id="stored passwords"),
    ],
)
def test_change_to_site_configuration_is_detected(
    tmp_path: Path, cache: Cache, changed_file: str
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    (tmp_path / changed_file).parent.mkdir(parents=True, exist_ok=True)

    with run_watcher(watcher_config, cache):
        (tmp_path / changed_file).touch()
        _wait_for_detected_change(cache)

    assert cache.get_last_detected_change() > 0


def test_permission_change_to_site_configuration_is_detected(tmp_path: Path, cache: Cache) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    rules = tmp_path / "etc" / "check_mk" / "conf.d" / "wato" / "rules.mk"
    rules.parent.mkdir(parents=True, exist_ok=True)
    rules.touch()

    with run_watcher(watcher_config, cache):
        rules.chmod(0o600)
        _wait_for_detected_change(cache)

    assert cache.get_last_detected_change() > 0


# watchdog follows the renamed folder only if its reader thread handles IN_MOVED_TO within the 50 ms
# it holds IN_MOVED_FROM back. The test pauses the thread for 10 ms in between, so on a heavily
# loaded machine, e.g. in CI, the thread may need longer, and the test fails although nothing is
# wrong. To run it, e.g. after changing the delay, remove the skip temporarily.
@pytest.mark.skip(
    reason="CMK-41782: timing-dependent, fails spuriously on a heavily loaded machine"
)
def test_hosts_of_a_new_folder_in_a_renamed_folder_are_detected(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    cache: Cache,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    (wato / "folder").mkdir(parents=True)
    hosts = wato / "renamed" / "new" / "hosts.mk"
    _delay_watchdog_after_moves_from(monkeypatch)

    with (
        caplog.at_level(logging.INFO, logger="cmk.automations.helper._watcher"),
        run_watcher(watcher_config, cache),
    ):
        (wato / "folder").rename(wato / "renamed")
        _wait_for_earlier_changes(caplog, wato / "renamed.mk")
        hosts.parent.mkdir()
        _wait_for_earlier_changes(caplog, wato / "created.mk")
        hosts.touch()
        _wait_for_log(caplog, f"Source: {hosts},")

    assert f"Source: {hosts}," in caplog.text


@pytest.mark.parametrize(
    "unrelated_file, relevant_file",
    [
        pytest.param(
            "etc/check_mk/multisite.mk", "etc/check_mk/main.mk", id="other configuration file"
        ),
        pytest.param(
            "etc/check_mk/conf.d/wato/.rules.mk.newab12cd",
            "etc/check_mk/conf.d/wato/rules.mk",
            id="temporary file of a save",
        ),
    ],
)
def test_change_to_unrelated_file_is_ignored(
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
    cache: Cache,
    unrelated_file: str,
    relevant_file: str,
) -> None:
    """The watcher handles the changes in order, so detecting *relevant_file* means it has seen
    *unrelated_file*, too."""
    watcher_config = _site_watcher_config(tmp_path)
    (tmp_path / relevant_file).parent.mkdir(parents=True, exist_ok=True)

    with (
        caplog.at_level(logging.INFO, logger="cmk.automations.helper._watcher"),
        run_watcher(watcher_config, cache),
    ):
        (tmp_path / unrelated_file).touch()
        (tmp_path / relevant_file).touch()
        _wait_for_detected_change(cache)

    assert f"Source: {tmp_path / relevant_file}," in caplog.text
    assert str(tmp_path / unrelated_file) not in caplog.text


def test_used_up_inotify_watches_keep_the_watcher_from_starting(
    tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    (tmp_path / "etc" / "check_mk" / "conf.d" / "wato").mkdir()
    # only the scheduled directories get a watch, conf.d/wato/ gets none
    watched = {os.fsencode(schedule.path) for schedule in watcher_config.schedules}
    _use_up_inotify_watches(monkeypatch, except_for=watched)

    with (
        pytest.raises(OSError) as raised,
        run_watcher(watcher_config, cache),
    ):
        pass

    assert raised.value.errno == errno.ENOSPC


def test_folder_that_cannot_be_watched_keeps_the_watcher_from_starting(
    tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _fail_to_watch(monkeypatch, wato)

    with (
        pytest.raises(OSError) as raised,
        run_watcher(watcher_config, cache),
    ):
        pass

    assert raised.value.errno == errno.ENOSPC


def test_used_up_inotify_watches_are_logged_with_twice_the_current_limit(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    current_limit = int(Path("/proc/sys/fs/inotify/max_user_watches").read_text())
    watcher_config = _site_watcher_config(tmp_path)
    (tmp_path / "etc" / "check_mk" / "conf.d" / "wato").mkdir()
    watched = {os.fsencode(schedule.path) for schedule in watcher_config.schedules}
    _use_up_inotify_watches(monkeypatch, except_for=watched)

    with contextlib.suppress(OSError), run_watcher(watcher_config, cache):
        pass

    assert _suggested_limit(caplog.text, "max_user_watches") == 2 * current_limit


def test_used_up_file_descriptors_are_logged_with_a_hint(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)

    with (
        contextlib.suppress(OSError),
        _used_up_file_descriptors(monkeypatch),
        run_watcher(watcher_config, cache),
    ):
        pass

    assert "raise the limit of open files, e.g. with: ulimit -n " in caplog.text


def test_used_up_file_descriptors_at_the_hard_limit_are_logged_with_a_hint(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)

    with (
        contextlib.suppress(OSError),
        _used_up_file_descriptors(monkeypatch, up_to_the_hard_limit=True),
        run_watcher(watcher_config, cache),
    ):
        pass

    assert "raise the hard limit of open files of the site user as root" in caplog.text


def test_used_up_inotify_instances_are_logged_with_a_hint(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    _use_up_inotify_instances(monkeypatch)

    with contextlib.suppress(OSError), run_watcher(watcher_config, cache):
        pass

    assert "sysctl fs.inotify.max_user_instances=" in caplog.text


def test_hosts_of_a_new_folder_that_cannot_be_watched_are_detected(
    tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _fail_to_watch_once_filled(monkeypatch, wato / "folder", "hosts.mk")

    with run_watcher(watcher_config, cache):
        (wato / "folder").mkdir()
        _wait_for_detected_change(cache)

    assert cache.get_last_detected_change() > 0


def test_change_is_detected_after_a_new_folder_cannot_be_watched(
    tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _fail_to_watch_once_filled(monkeypatch, wato / "folder", ".wato")  # matches no pattern

    with run_watcher(watcher_config, cache):
        (wato / "folder").mkdir()
        (wato / "rules.mk").touch()
        _wait_for_detected_change(cache)

    assert cache.get_last_detected_change() > 0


def test_new_folder_that_cannot_be_watched_is_logged_with_a_hint(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _fail_to_watch_once_filled(monkeypatch, wato / "folder", ".wato")

    with run_watcher(watcher_config, cache):
        (wato / "folder").mkdir()
        _wait_for_log(caplog, "Cannot watch")

    assert any(
        f"Cannot watch {wato / 'folder'}:" in message and "sysctl fs.inotify." in message
        for message in caplog.messages
    )


def test_new_folder_tree_that_cannot_be_watched_is_logged_once(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _fail_to_watch_once_nested(monkeypatch, wato / "folder", "sub/subsub")

    with (
        caplog.at_level(logging.INFO, logger="cmk.automations.helper._watcher"),
        run_watcher(watcher_config, cache),
    ):
        (wato / "folder").mkdir()
        _wait_for_earlier_changes(caplog, wato / "rules.mk")

    assert sum("Cannot watch" in message for message in caplog.messages) == 1


def test_change_is_detected_after_watchdog_fails_to_handle_an_event(
    tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _make_watchdog_fail(monkeypatch, wato / "folder")

    with run_watcher(watcher_config, cache):
        (wato / "folder").mkdir()
        (wato / "rules.mk").touch()
        _wait_for_detected_change(cache)

    assert cache.get_last_detected_change() > 0


def test_failure_of_watchdog_to_handle_an_event_is_logged(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    conf_d = tmp_path / "etc" / "check_mk" / "conf.d"
    _make_watchdog_fail(monkeypatch, conf_d / "folder")

    with run_watcher(watcher_config, cache):
        (conf_d / "folder").mkdir()
        _wait_for_log(caplog, "Error while handling")

    assert f"Error while handling a change below {conf_d}," in caplog.text


def test_every_automation_requires_a_reload_after_a_new_folder_cannot_be_watched(
    tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _fail_to_watch_once_filled(monkeypatch, wato / "folder", ".wato")  # matches no pattern

    with run_watcher(watcher_config, cache):
        (wato / "folder").mkdir()
        _wait_for_reload_required(cache)

    assert cache.reload_required(last_reload=time.time())


def test_every_automation_requires_a_reload_after_watchdog_fails_to_handle_an_event(
    tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _make_watchdog_fail(monkeypatch, wato / "folder")

    with run_watcher(watcher_config, cache):
        (wato / "folder").mkdir()
        _wait_for_reload_required(cache)

    assert cache.reload_required(last_reload=time.time())


def test_change_is_detected_while_redis_hangs_on_marking_changes_unwatched(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _fail_to_watch_once_filled(monkeypatch, wato / "folder", ".wato")  # matches no pattern
    cache = _CacheHangingOnMarks.setup(client=FakeRedis())

    with run_watcher(watcher_config, cache):
        try:
            (wato / "folder").mkdir()  # makes the watcher mark that changes may go unnoticed
            (wato / "rules.mk").touch()
            _wait_for_detected_change(cache)

            assert cache.get_last_detected_change() > 0
        finally:
            cache.released.set()


def test_failure_to_mark_changes_unwatched_is_logged(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    wato = tmp_path / "etc" / "check_mk" / "conf.d" / "wato"
    wato.mkdir()
    _fail_to_watch_once_filled(monkeypatch, wato / "folder", ".wato")  # matches no pattern
    cache = _CacheTimingOutOnMarks.setup(client=FakeRedis())

    with run_watcher(watcher_config, cache):
        (wato / "folder").mkdir()  # makes the watcher mark that changes may go unnoticed
        _wait_for_log(caplog, "Error while storing")

    assert "[watcher] Error while storing whether changes may go unnoticed" in caplog.text


def test_watcher_start_forgets_unwatched_changes_of_an_earlier_run(
    tmp_path: Path, cache: Cache
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    cache.store_changes_unwatched(unwatched=True)  # e.g. before the automation helper restarted

    with run_watcher(watcher_config, cache):
        pass

    assert not cache.reload_required(last_reload=time.time())


def test_watcher_starts_while_redis_is_unavailable(tmp_path: Path) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    server = FakeServer()
    server.connected = False
    cache = Cache.setup(client=FakeRedis(server=server))

    with run_watcher(watcher_config, cache):
        pass


def test_watcher_stops_after_the_place_of_a_moved_out_folder_was_reused(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache
) -> None:
    watcher_config = _site_watcher_config(tmp_path)
    folder = tmp_path / "etc" / "check_mk" / "conf.d" / "wato" / "folder"
    folder.mkdir(parents=True)

    with (
        caplog.at_level(logging.INFO, logger="cmk.automations.helper._watcher"),
        run_watcher(watcher_config, cache),
    ):
        _reuse_the_place_of_a_moved_out_folder(caplog, folder, tmp_path / "outside")

    assert "[watcher] Shutdown complete" in caplog.text


def test_error_while_shutting_down_is_logged(
    caplog: pytest.LogCaptureFixture, tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    watcher_config = _site_watcher_config(tmp_path)

    with contextlib.suppress(OSError), run_watcher(watcher_config, cache):
        _fail_to_stop_watching(monkeypatch)

    assert "[watcher] Error while shutting down" in caplog.text


def test_watcher_does_not_start_without_a_running_watchdog_reader(
    tmp_path: Path, cache: Cache, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Like after a fork, e.g. in daemonize(), when watchdog.observers was imported before."""
    from watchdog.observers.inotify_c import InotifyFD

    watcher_config = _site_watcher_config(tmp_path)
    reader = Mock(spec=InotifyFD)
    reader.is_alive.return_value = False
    # watchdog's process-wide reader is a boundary we cannot inject.
    monkeypatch.setattr(InotifyFD, "_instance", reader)

    with (
        pytest.raises(RuntimeError, match="reader thread is not running"),
        run_watcher(watcher_config, cache),
    ):
        pass


class _CacheTimingOutOnMarks(Cache):
    """A cache that times out when the watcher marks that changes may go unnoticed, as Redis may."""

    @override
    def store_changes_unwatched(self, *, unwatched: bool) -> None:
        if unwatched:
            raise RedisTimeoutError("Timeout reading from socket")
        super().store_changes_unwatched(unwatched=unwatched)


@dataclasses.dataclass(frozen=True)
class _CacheHangingOnMarks(Cache):
    """A cache that hangs when the watcher marks that changes may go unnoticed, until released, as
    if Redis hung."""

    released: threading.Event = dataclasses.field(default_factory=threading.Event)

    @override
    def store_changes_unwatched(self, *, unwatched: bool) -> None:
        if unwatched:
            self.released.wait()
        super().store_changes_unwatched(unwatched=unwatched)


def _site_watcher_config(omd_root: Path) -> WatcherConfig:
    """The default watcher configuration of a site in *omd_root*, with the watched directories."""
    config = config_from_disk_or_default_config(
        omd_root=omd_root,
        run_directory=omd_root / "tmp" / "run",
        log_directory=omd_root / "var" / "log",
    ).watcher_config
    for schedule in config.schedules:
        schedule.path.mkdir(parents=True, exist_ok=True)
    return config


def _use_up_inotify_watches(
    monkeypatch: pytest.MonkeyPatch, *, except_for: Container[bytes]
) -> None:
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def limited_add_watch(fd: int, path: bytes, mask: int) -> int:
        if path in except_for:
            return add_watch(fd, path, mask)
        ctypes.set_errno(errno.ENOSPC)
        return -1

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", limited_add_watch)


def _use_up_inotify_instances(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make creating watchdog's inotify instance fail as if the user's instances were used up."""
    from watchdog.observers import inotify_c

    def failing_inotify_init() -> int:
        ctypes.set_errno(errno.EMFILE)
        return -1

    # watchdog's process-wide instance and the system call are boundaries we cannot inject.
    # Without the instance, watchdog creates it anew.
    monkeypatch.setattr(inotify_c.InotifyFD, "_instance", None)
    monkeypatch.setattr(inotify_c, "inotify_init", failing_inotify_init)


@contextlib.contextmanager
def _used_up_file_descriptors(
    monkeypatch: pytest.MonkeyPatch, *, up_to_the_hard_limit: bool = False
) -> Iterator[None]:
    """Lower this process's limit of open files to the files it has open, so that creating
    watchdog's inotify instance fails; *up_to_the_hard_limit* reports that limit as the hard one,
    too."""
    from watchdog.observers import inotify_c

    # watchdog's process-wide instance is a boundary we cannot inject. Without it, watchdog
    # creates it anew.
    monkeypatch.setattr(inotify_c.InotifyFD, "_instance", None)
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    lowest_free = os.open(os.devnull, os.O_RDONLY)
    os.close(lowest_free)
    resource.setrlimit(resource.RLIMIT_NOFILE, (lowest_free, hard))
    if up_to_the_hard_limit:
        getrlimit = resource.getrlimit

        def getrlimit_at_hard_limit(which: int) -> tuple[int, int]:
            if which == resource.RLIMIT_NOFILE:
                return lowest_free, lowest_free
            return getrlimit(which)

        # The system call is a boundary we cannot inject, and lowering the hard limit for real
        # could not be undone.
        monkeypatch.setattr(resource, "getrlimit", getrlimit_at_hard_limit)
    try:
        yield
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))


def _fail_to_watch(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    """Make watching *directory* fail as if the watches were used up, but not watching others, as
    when the watches are used up just then and free again right after."""
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def failing_add_watch(fd: int, path: bytes, mask: int) -> int:
        if path != os.fsencode(directory):
            return add_watch(fd, path, mask)
        ctypes.set_errno(errno.ENOSPC)
        return -1

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", failing_add_watch)


def _fail_to_watch_once_filled(
    monkeypatch: pytest.MonkeyPatch, directory: Path, file_name: str
) -> None:
    """Make watching *directory* fail as if the watches were used up, once the file *file_name*
    has appeared in it, as when the file is written right after creating the directory."""
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def failing_add_watch(fd: int, path: bytes, mask: int) -> int:
        if path != os.fsencode(directory):
            return add_watch(fd, path, mask)
        (directory / file_name).touch()
        ctypes.set_errno(errno.ENOSPC)
        return -1

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", failing_add_watch)


def _fail_to_watch_once_nested(
    monkeypatch: pytest.MonkeyPatch, directory: Path, nested: str
) -> None:
    """Make watching *directory* and the directories below it fail as if the watches were used up,
    once the directories *nested* have appeared in it, as when a tree is copied in."""
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def failing_add_watch(fd: int, path: bytes, mask: int) -> int:
        if not Path(os.fsdecode(path)).is_relative_to(directory):
            return add_watch(fd, path, mask)
        (directory / nested).mkdir(parents=True, exist_ok=True)
        ctypes.set_errno(errno.ENOSPC)
        return -1

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", failing_add_watch)


def _delay_watchdog_after_moves_from(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make watchdog's reader thread pause after each IN_MOVED_FROM, as a busy automation helper
    might between the two events of a rename."""
    from watchdog.observers.inotify_c import InotifyEvent, InotifyFD

    handle_event = InotifyFD.handle_event

    def delayed_handle_event(self: InotifyFD, event: InotifyEvent) -> None:
        handle_event(self, event)
        if event.is_moved_from:
            time.sleep(0.01)

    # watchdog's process-wide reader is a boundary we cannot inject.
    monkeypatch.setattr(InotifyFD, "handle_event", delayed_handle_event)


def _wait_for_earlier_changes(caplog: pytest.LogCaptureFixture, marker: Path) -> None:
    """Wait until the watcher has handled the changes so far below the watched directory of the
    new file *marker*: it handles them in order, so it has once it has handled *marker*."""
    marker.touch()
    _wait_for_log(caplog, f"Source: {marker},")


def _make_watchdog_fail(monkeypatch: pytest.MonkeyPatch, directory: Path) -> None:
    """Make watchdog fail unexpectedly to handle the creation of *directory*, as a bug in it would."""
    from watchdog.observers import inotify_c

    add_watch = inotify_c.inotify_add_watch

    def failing_add_watch(fd: int, path: bytes, mask: int) -> int:
        if path == os.fsencode(directory):
            raise RuntimeError("bug in watchdog")
        return add_watch(fd, path, mask)

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_add_watch", failing_add_watch)


def _fail_to_stop_watching(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make watchdog fail unexpectedly to remove its watches, after removing them.

    Like after a real failure, some of watchdog's threads stay blocked, but they are daemon
    threads."""
    from watchdog.observers import inotify_c

    rm_watch = inotify_c.inotify_rm_watch

    def failing_rm_watch(fd: int, wd: inotify_c.WatchDescriptor) -> int:
        rm_watch(fd, wd)
        ctypes.set_errno(errno.EIO)
        return -1

    # The system call is a boundary we cannot inject.
    monkeypatch.setattr(inotify_c, "inotify_rm_watch", failing_rm_watch)


def _reuse_the_place_of_a_moved_out_folder(
    caplog: pytest.LogCaptureFixture, folder: Path, outside: Path
) -> None:
    """Move the watched *folder* to *outside*, then create and delete a folder in its place.

    watchdog 7.0.0 keeps the path of a directory moved out of the watched directories. The new
    folder takes the path over and deleting it drops the path, so watchdog looks the path up in
    vain when it stops watching the moved folder."""
    outside.mkdir()
    folder.rename(outside / folder.name)
    folder.mkdir()
    (folder / "hosts.mk").touch()
    _wait_for_log(caplog, f"Source: {folder / 'hosts.mk'},")  # so the new folder has a watch
    (folder / "hosts.mk").unlink()
    folder.rmdir()
    (folder.parent / "rules.mk").touch()
    # watchdog handles the changes in order, so it has handled the deletion by now
    _wait_for_log(caplog, f"Source: {folder.parent / 'rules.mk'},")


def _suggested_limit(text: str, name: str) -> int:
    """The value *text* suggests for the inotify limit *name*, or 0 if it suggests none."""
    return int(match[1]) if (match := re.search(rf"sysctl fs\.inotify\.{name}=(\d+)", text)) else 0


def _wait_for_detected_change(cache: Cache) -> None:
    with contextlib.suppress(TimeoutError):  # the test's assertion reports it
        wait_until(lambda: cache.get_last_detected_change() > 0, timeout=5, interval=0.01)


def _wait_for_reload_required(cache: Cache) -> None:
    with contextlib.suppress(TimeoutError):  # the test's assertion reports it
        wait_until(lambda: cache.reload_required(last_reload=time.time()), timeout=5, interval=0.01)


def _wait_for_log(caplog: pytest.LogCaptureFixture, text: str) -> None:
    with contextlib.suppress(TimeoutError):  # the test's assertion reports it
        wait_until(lambda: text in caplog.text, timeout=5, interval=0.01)
