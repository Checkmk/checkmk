#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import contextlib
import errno
import logging
import os
import socket
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable, Iterator, Sequence
from pathlib import Path
from typing import NamedTuple, NoReturn

import pytest

import cmk.ec.export as ec
from cmk.ccc.site import SiteId
from cmk.ec.config import Config
from cmk.ec.helpers import ECLock
from cmk.ec.history import History
from cmk.ec.main import (
    create_history,
    create_history_raw,
    default_slave_status_master,
    EventServer,
    EventStatus,
    make_config,
    MAX_SPOOL_FILE_SIZE,
    MAX_TRIES_LACKING_MEMORY,
    read_spool_file,
    StatusTableEvents,
    StatusTableHistory,
)
from cmk.ec.perfcounters import Perfcounters
from cmk.ec.query import Columns
from cmk.ec.settings import create_settings

_RECEIVE_TIMEOUT = 10  # seconds
_TERMINATE_TIMEOUT = 10  # seconds
# How long to wait for events beyond the expected ones, so a test sees surplus events, too
_SURPLUS_EVENTS_TIMEOUT = 0.1  # seconds
# Instead of a second, so tests don't wait that long for spool files to be seen or for restarts
_EVENT_SERVER_DELAY = 0.01  # seconds

_MATCHING_ALL = ec.Rule(
    id="all",
    actions=[],
    actions_in_downtime=True,
    autodelete=False,
    cancel_action_phases="always",
    cancel_actions=[],
    comment="",
    description="",
    disabled=False,
    docu_url="",
    invert_matching=False,
    sl=ec.ServiceLevel(precedence="message", value=0),
    state=0,
)


class _CoreWithoutHosts:
    """Answers the host lookups of the Event Console like a monitoring core without any hosts"""

    def __init__(self) -> None:
        self.unexpected_queries: list[str] = []

    def query(self, query: str) -> Sequence[Sequence[object]]:
        match query.splitlines():
            case ["GET status", "Columns: program_start"]:
                return [[0]]
            case ["GET hosts", *_]:
                return []
            case _:
                self.unexpected_queries.append(query)
                raise ValueError(f"unexpected Livestatus query {query!r}")


class _EventConsole(NamedTuple):
    settings: ec.Settings
    event_status: EventStatus


type _HistoryFactory = Callable[[ec.Settings, Config, logging.Logger, Columns, Columns], History]
type _SpoolFileReader = Callable[[Path], Iterable[bytes] | None]


@pytest.fixture(name="event_console")
def fixture_event_console() -> Iterator[_EventConsole]:
    with _running_event_console(create_history) as event_console:
        yield event_console


@contextlib.contextmanager
def _running_event_console(
    make_history: _HistoryFactory,
    *,
    idle_timeout: float = _EVENT_SERVER_DELAY,
    read_spool_file: _SpoolFileReader = read_spool_file,
) -> Iterator[_EventConsole]:
    """A running event server, wired up like by main(), opening an event for each message"""
    # Unix socket paths are limited to ~108 bytes, which pytest's tmp_path may exceed.
    with tempfile.TemporaryDirectory(dir="/tmp") as omd_root:
        settings = create_settings("1.2.3i45", Path(omd_root), ["mkeventd"])
        settings.paths.event_pipe.value.parent.mkdir(parents=True)
        logger = logging.getLogger("cmk.mkeventd")
        # Unlike SQLite, recording the history in files leaves nothing open after the test.
        config = make_config(ec.default_config()) | {"archive_mode": "file"}
        history = make_history(
            settings, config, logger, StatusTableEvents.columns, StatusTableHistory.columns
        )
        perfcounters = Perfcounters(logger.getChild("lock.perfcounters"))
        core = _CoreWithoutHosts()
        event_status = EventStatus(
            settings, config, perfcounters, history, logger.getChild("EventStatus"), core
        )
        event_server = EventServer(
            logger.getChild("EventServer"),
            settings,
            config,
            default_slave_status_master(),
            perfcounters,
            ECLock(logger.getChild("lock.configuration")),
            history,
            event_status,
            StatusTableEvents.columns,
            core,
            SiteId("hurz"),
            idle_timeout=idle_timeout,
            read_spool_file=read_spool_file,
            restart_delay=_EVENT_SERVER_DELAY,
        )
        event_server.compile_rules([ec.default_rule_pack([_MATCHING_ALL])])
        # So that an event server which doesn't terminate fails the test instead of hanging it
        event_server.daemon = True
        event_server.start()
        try:
            yield _EventConsole(settings, event_status)
        finally:
            event_server.terminate()
            # Wake the server up, so it doesn't wait for its select() timeout before terminating.
            # Just connecting does that: Sending anything, even no data, would fail with EPIPE if
            # the server accepted the connection and closed it on terminating in the meantime.
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as event_socket:
                event_socket.connect(str(settings.paths.event_socket.value))
            event_server.join(_TERMINATE_TIMEOUT)
        if event_server.is_alive():
            pytest.fail(f"the event server doesn't terminate within {_TERMINATE_TIMEOUT} s")
        # The event server closes the event pipe when it terminates, so it doesn't leak.
        if fds := _fds_open_on(settings.paths.event_pipe.value):
            pytest.fail(f"the event pipe is still open {fds} times after terminating")
        # The Event Console copes with failing queries itself, so don't let a test rely on that.
        if core.unexpected_queries:
            pytest.fail(f"unexpected Livestatus queries: {core.unexpected_queries!r}")


def _write_to_event_pipe(settings: ec.Settings, data: bytes) -> None:
    with settings.paths.event_pipe.value.open("wb") as pipe:
        pipe.write(data)


def _send_to_event_socket(settings: ec.Settings, data: bytes) -> None:
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as event_socket:
        event_socket.connect(str(settings.paths.event_socket.value))
        event_socket.sendall(data)


def _event_texts(event_status: EventStatus) -> list[str]:
    with event_status.lock:
        return [event["text"] for event in event_status.events()]


def _texts_of_events(event_status: EventStatus, count: int) -> list[str]:
    """
    Returns the texts of the events once there are as many as given, or after a timeout, including
    surplus events coming right after them
    """
    deadline = time.monotonic() + _RECEIVE_TIMEOUT
    while len(_event_texts(event_status)) < count and time.monotonic() < deadline:
        time.sleep(0.01)
    time.sleep(_SURPLUS_EVENTS_TIMEOUT)
    return _event_texts(event_status)


def test_octet_counted_syslog_message_from_the_event_socket_is_not_split_at_its_newlines(
    event_console: _EventConsole,
) -> None:
    # Like the syslog exporter of the OpenTelemetry collector sends a multi-line log message
    message = b"<14>1 2026-11-02T16:00:00Z myservice myapp - - - disk \nfull\n"

    _send_to_event_socket(event_console.settings, b"%d %s" % (len(message), message))

    # The Event Console removes the newlines from the text, see scrub_string().
    assert _texts_of_events(event_console.event_status, 1) == ["disk full"]


def test_wrong_octet_count_on_the_event_pipe_holds_back_no_message_of_another_program(
    event_console: _EventConsole,
) -> None:
    settings, event_status = event_console
    # Like an octet-counted syslog message, but shorter than announced
    _write_to_event_pipe(settings, b"999 <14>not as long as announced\n")

    _write_to_event_pipe(settings, b"from another program\n")

    assert _texts_of_events(event_status, 2) == [
        "999 <14>not as long as announced",
        "from another program",
    ]


def _fds_open_on(path: Path) -> int:
    """Counts the file descriptors of this process which are open on the given file"""
    targets = []
    for fd in Path("/proc/self/fd").iterdir():
        with contextlib.suppress(FileNotFoundError):  # closed in the meantime
            targets.append(os.readlink(fd))
    return targets.count(str(path.resolve()))


def _make_adding_history_entries_fail(settings: ec.Settings) -> None:
    history_dir = settings.paths.history_dir.value
    # A file instead of the history directory makes adding entries fail, even for root.
    history_dir.parent.mkdir(parents=True, exist_ok=True)
    history_dir.touch()


def _restart_event_server_by_an_error(settings: ec.Settings, event_status: EventStatus) -> None:
    """
    Makes adding history entries fail, which restarts the event server with a raw history, and
    waits until the restarted event server has read a message from the event pipe
    """
    _make_adding_history_entries_fail(settings)
    _write_to_event_pipe(settings, b"before the restart\n")
    _texts_of_events(event_status, 1)  # The event is there before adding its entry fails.
    _write_to_event_pipe(settings, b"after the restart\n")
    if (texts := _texts_of_events(event_status, 2)) != ["before the restart", "after the restart"]:
        pytest.fail(f"no event from the event pipe after the restart: {texts!r}")


def test_event_server_restarted_after_an_error_has_the_event_pipe_open_only_once(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The raw history raises its errors, which restarts the event server.
    with _running_event_console(create_history_raw) as (settings, event_status):
        _restart_event_server_by_an_error(settings, event_status)
        fds = _fds_open_on(settings.paths.event_pipe.value)

    assert "Exception in EventServer server" in caplog.text
    assert fds == 1


def test_event_server_restarted_after_an_error_keeps_the_start_of_a_message_from_the_event_pipe(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The raw history raises its errors, which restarts the event server.
    with _running_event_console(create_history_raw) as (settings, event_status):
        _make_adding_history_entries_fail(settings)
        _write_to_event_pipe(settings, b"before the restart\nthe start of a message")
        _texts_of_events(event_status, 1)  # The event is there before adding its entry fails.

        _write_to_event_pipe(settings, b" and its rest\n")
        texts = _texts_of_events(event_status, 2)

    assert "Exception in EventServer server" in caplog.text
    assert texts == ["before the restart", "the start of a message and its rest"]


def test_event_server_restarted_after_an_error_keeps_a_client_with_the_start_of_its_message(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # The raw history raises its errors, which restarts the event server.
    with (
        _running_event_console(create_history_raw) as (settings, event_status),
        socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client,
    ):
        client.connect(str(settings.paths.event_socket.value))
        _make_adding_history_entries_fail(settings)
        client.sendall(b"before the restart\nthe start of a message")
        _texts_of_events(event_status, 1)  # The event is there before adding its entry fails.

        client.sendall(b" and its rest\n")
        texts = _texts_of_events(event_status, 2)

    assert "Exception in EventServer server" in caplog.text
    assert texts == ["before the restart", "the start of a message and its rest"]


def test_event_server_processes_messages_although_writing_the_history_fails(
    event_console: _EventConsole,
) -> None:
    settings, event_status = event_console
    _make_adding_history_entries_fail(settings)

    _write_to_event_pipe(settings, b"first\nsecond\n")

    assert _texts_of_events(event_status, 2) == ["first", "second"]


def _add_spool_file(
    spool_dir: Path, data: bytes, *, name: str = "file", mtime: float | None = None
) -> None:
    """Adds a spool file like its writers do, making it visible only once it is complete"""
    incomplete = spool_dir / f".{name}"
    incomplete.write_bytes(data)
    if mtime is not None:
        os.utime(incomplete, (mtime, mtime))
    incomplete.rename(spool_dir / name)


_ENTRIES_OTHER_THAN_REGULAR_FILES = (
    pytest.param(Path.mkdir, id="directory"),
    pytest.param(os.mkfifo, id="FIFO"),
    pytest.param(lambda path: path.symlink_to("nowhere"), id="broken symbolic link"),
)


@pytest.mark.parametrize("make_entry", _ENTRIES_OTHER_THAN_REGULAR_FILES)
def test_entry_other_than_a_regular_file_in_the_spool_directory_holds_back_no_spool_file(
    event_console: _EventConsole, make_entry: Callable[[Path], object]
) -> None:
    settings, event_status = event_console
    spool_dir = settings.paths.spool_dir.value
    spool_dir.mkdir(parents=True)
    make_entry(spool_dir / "entry")
    # Older than the spool file, so it comes first
    os.utime(spool_dir / "entry", (0, 0), follow_symlinks=False)

    _add_spool_file(spool_dir, b"from the spool file\n")

    assert _texts_of_events(event_status, 1) == ["from the spool file"]


def _logged_warnings(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.levelno == logging.WARNING]


@pytest.mark.parametrize("make_entry", _ENTRIES_OTHER_THAN_REGULAR_FILES)
def test_entry_other_than_a_regular_file_in_the_spool_directory_is_warned_about_once(
    event_console: _EventConsole,
    caplog: pytest.LogCaptureFixture,
    make_entry: Callable[[Path], object],
) -> None:
    settings, event_status = event_console
    spool_dir = settings.paths.spool_dir.value
    spool_dir.mkdir(parents=True)
    make_entry(spool_dir / "entry")

    _add_spool_file(spool_dir, b"from the spool file\n")
    # Meanwhile, the event server lists the spool directory again and again.
    _texts_of_events(event_status, 1)

    assert _logged_warnings(caplog) == [
        f"Skipping {spool_dir / 'entry'} in the spool directory while it leads to no regular file"
    ]


def _eventually(condition: Callable[[], bool]) -> bool:
    """Waits until the condition holds, or until a timeout, and returns whether it holds"""
    deadline = time.monotonic() + _RECEIVE_TIMEOUT
    while not condition():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.01)
    return True


def test_unreadable_spool_file_holds_back_no_spool_file(
    event_console: _EventConsole,
) -> None:
    settings, event_status = event_console
    spool_dir = settings.paths.spool_dir.value
    spool_dir.mkdir(parents=True)
    # Reading it fails even for root, as nothing is mapped at the start of the address space.
    (spool_dir / "unreadable").symlink_to("/proc/self/mem")

    # The modification time of /proc/self/mem is about now, so make the readable file newer.
    _add_spool_file(spool_dir, b"from the spool file\n", mtime=time.time() + 3600)

    assert _texts_of_events(event_status, 1) == ["from the spool file"]


def test_unreadable_spool_file_is_hidden(event_console: _EventConsole) -> None:
    spool_dir = event_console.settings.paths.spool_dir.value
    spool_dir.mkdir(parents=True)

    # Reading it fails even for root, as nothing is mapped at the start of the address space.
    (spool_dir / "unreadable").symlink_to("/proc/self/mem")

    assert _eventually((spool_dir / ".unreadable.unreadable").is_symlink)


def test_spool_file_too_big_to_read_at_once_is_hidden(event_console: _EventConsole) -> None:
    spool_dir = event_console.settings.paths.spool_dir.value
    spool_dir.mkdir(parents=True)
    incomplete = spool_dir / ".too_big"
    # Sparse, so it takes neither time nor disk space
    with incomplete.open("wb") as too_big:
        too_big.truncate(MAX_SPOOL_FILE_SIZE + 1)

    incomplete.rename(spool_dir / "too_big")

    assert _eventually((spool_dir / ".too_big.unreadable").exists)


def _reading_spool_files_after(*actions: Callable[[Path], object]) -> _SpoolFileReader:
    """
    Reads spool files like the event server, but does an action right before reading each of the
    first ones: Something happening right between listing the spool directory and reading a file
    from it can't be timed.
    """
    remaining = list(actions)

    def read(path: Path) -> Iterable[bytes] | None:
        if remaining:
            remaining.pop(0)(path)
        return read_spool_file(path)

    return read


def _lack_file_descriptors(_path: Path) -> NoReturn:
    raise OSError(errno.EMFILE, os.strerror(errno.EMFILE))


def _lack_memory(_path: Path) -> NoReturn:
    raise MemoryError


def _lack_kernel_memory(_path: Path) -> NoReturn:
    raise OSError(errno.ENOMEM, os.strerror(errno.ENOMEM))


_LACKS_OF_MEMORY = (
    pytest.param(_lack_memory, id="memory"),
    pytest.param(_lack_kernel_memory, id="kernel memory"),
)

_LACKS_OF_RESOURCES = (
    pytest.param(_lack_file_descriptors, id="file descriptors"),
    *_LACKS_OF_MEMORY,
)


@pytest.mark.parametrize("lack_resources", _LACKS_OF_RESOURCES)
def test_spool_file_which_cannot_be_read_for_lack_of_resources_is_processed_later(
    lack_resources: Callable[[Path], object],
) -> None:
    # Up to the last try before a lack of memory makes the event server give up on it
    tries = [lack_resources] * (MAX_TRIES_LACKING_MEMORY - 1)
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(*tries)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        _add_spool_file(spool_dir, b"from the spool file\n")
        texts = _texts_of_events(event_status, 1)

    assert texts == ["from the spool file"]


@pytest.mark.parametrize("lack_resources", _LACKS_OF_RESOURCES)
def test_spool_file_which_cannot_be_read_for_lack_of_resources_is_warned_about_once(
    lack_resources: Callable[[Path], object], caplog: pytest.LogCaptureFixture
) -> None:
    # Like above, but the event server tries again before the resources are free again.
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(lack_resources, lack_resources)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        _add_spool_file(spool_dir, b"from the spool file\n")
        _texts_of_events(event_status, 1)

    assert sum("trying again later" in record.getMessage() for record in caplog.records) == 1


@pytest.mark.parametrize("lack_memory", _LACKS_OF_MEMORY)
def test_spool_file_which_never_fits_into_memory_is_hidden(
    lack_memory: Callable[[Path], object],
) -> None:
    # Memory may never suffice for a big file, e.g. under a limit of the address space.
    tries = [lack_memory] * MAX_TRIES_LACKING_MEMORY
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(*tries)
    ) as (settings, _event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        _add_spool_file(spool_dir, b"from the spool file\n")
        hidden = _eventually((spool_dir / ".file.unreadable").exists)

    assert hidden


@pytest.mark.parametrize("lack_memory", _LACKS_OF_MEMORY)
def test_spool_file_which_never_fits_into_memory_holds_back_no_spool_file(
    lack_memory: Callable[[Path], object],
) -> None:
    tries = [lack_memory] * MAX_TRIES_LACKING_MEMORY
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(*tries)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        # The second one comes after the first one, by its modification time or else by its name.
        _add_spool_file(spool_dir, b"never fits into memory\n", name="first")
        _add_spool_file(spool_dir, b"from the next spool file\n", name="second")
        texts = _texts_of_events(event_status, 1)

    assert texts == ["from the next spool file"]


def test_spool_file_which_cannot_be_read_for_lack_of_file_descriptors_is_never_given_up() -> None:
    # Unlike memory, file descriptors lack for any file alike, so giving up on one helps no other.
    tries = [_lack_file_descriptors] * MAX_TRIES_LACKING_MEMORY
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(*tries)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        _add_spool_file(spool_dir, b"from the spool file\n")
        texts = _texts_of_events(event_status, 1)

    assert texts == ["from the spool file"]


def test_spool_file_lacking_memory_is_not_given_up_while_messages_keep_arriving(
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Each message wakes the event server up, but it tries the spool file again only after its idle
    # timeout, here longer than the test takes.
    tries = [_lack_memory] * MAX_TRIES_LACKING_MEMORY
    with _running_event_console(
        create_history,
        idle_timeout=_RECEIVE_TIMEOUT,
        read_spool_file=_reading_spool_files_after(*tries),
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)
        _add_spool_file(spool_dir, b"from the spool file\n")

        # More messages than tries before giving up on it, each one read on its own
        for number in range(MAX_TRIES_LACKING_MEMORY + 1):
            _write_to_event_pipe(settings, b"message %d\n" % number)
            _texts_of_events(event_status, number + 1)
        if not _logged(caplog, "trying again later"):
            pytest.fail("the event server doesn't try to read the spool file")
        given_up = (spool_dir / ".file.unreadable").exists()

    assert not given_up


def test_lack_of_resources_for_a_spool_file_after_giving_up_on_another_one_is_warned_about(
    caplog: pytest.LogCaptureFixture,
) -> None:
    tries = [*[_lack_memory] * MAX_TRIES_LACKING_MEMORY, _lack_file_descriptors]
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(*tries)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        # The second one comes after the first one, by its modification time or else by its name.
        _add_spool_file(spool_dir, b"never fits into memory\n", name="first")
        _add_spool_file(spool_dir, b"from the next spool file\n", name="second")
        _texts_of_events(event_status, 1)

    assert sum("trying again later" in record.getMessage() for record in caplog.records) == 2


def _logged_errors(caplog: pytest.LogCaptureFixture) -> list[str]:
    return [record.getMessage() for record in caplog.records if record.levelno >= logging.ERROR]


def test_spool_file_removed_while_being_read_is_no_error(caplog: pytest.LogCaptureFixture) -> None:
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(Path.unlink)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        # The second one comes after the first one, by its modification time or else by its name.
        _add_spool_file(spool_dir, b"removed while being read\n", name="first")
        _add_spool_file(spool_dir, b"from the next spool file\n", name="second")
        texts = _texts_of_events(event_status, 1)

    assert texts == ["from the next spool file"]
    assert _logged_errors(caplog) == []


def _replace_by_fifo(path: Path) -> None:
    path.unlink()
    os.mkfifo(path)


def test_spool_file_replaced_by_a_fifo_before_being_read_holds_back_no_spool_file() -> None:
    # Reading a FIFO would wait for a writer.
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(_replace_by_fifo)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        # The second one comes after the first one, by its modification time or else by its name.
        _add_spool_file(spool_dir, b"replaced by a FIFO\n", name="first")
        _add_spool_file(spool_dir, b"from the next spool file\n", name="second")
        texts = _texts_of_events(event_status, 1)

    assert texts == ["from the next spool file"]


def _replace_by_directory(path: Path) -> None:
    path.unlink()
    path.mkdir()


def test_spool_file_replaced_by_a_directory_before_being_read_is_skipped() -> None:
    # Unlike for a FIFO, Python's open() refuses a directory itself.
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(_replace_by_directory)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)

        # The second one comes after the first one, by its modification time or else by its name.
        _add_spool_file(spool_dir, b"replaced by a directory\n", name="first")
        _add_spool_file(spool_dir, b"from the next spool file\n", name="second")
        _texts_of_events(event_status, 1)
        # Not put aside like an unreadable file
        skipped = (spool_dir / "first").is_dir()

    assert skipped


@pytest.mark.parametrize(
    "make_vanish",
    (
        pytest.param(Path.unlink, id="removed"),
        pytest.param(_replace_by_fifo, id="replaced by a FIFO"),
    ),
)
def test_new_spool_file_with_the_name_of_one_which_lacked_memory_is_not_given_up_early(
    make_vanish: Callable[[Path], object],
) -> None:
    # Up to the last try before giving up on it, then it's no regular file anymore when tried again.
    tries = [*[_lack_memory] * (MAX_TRIES_LACKING_MEMORY - 1), make_vanish, _lack_memory]
    with _running_event_console(
        create_history, read_spool_file=_reading_spool_files_after(*tries)
    ) as (settings, event_status):
        spool_dir = settings.paths.spool_dir.value
        spool_dir.mkdir(parents=True)
        _add_spool_file(spool_dir, b"vanishes\n")
        if not _eventually(lambda: not (spool_dir / "file").is_file()):
            pytest.fail("the spool file lacking memory is not tried again")
        # Processed only after the try which finds the spool file vanished, so that try can't find
        # the new one instead
        _write_to_event_pipe(settings, b"after it vanished\n")
        _texts_of_events(event_status, 1)
        (spool_dir / "file").unlink(missing_ok=True)

        _add_spool_file(spool_dir, b"from the new spool file\n")
        texts = _texts_of_events(event_status, 2)

    assert texts == ["after it vanished", "from the new spool file"]


def test_spool_file_which_can_be_neither_read_nor_renamed_holds_back_no_spool_file(
    event_console: _EventConsole,
) -> None:
    settings, event_status = event_console
    spool_dir = settings.paths.spool_dir.value
    # A directory with its hidden name keeps it from being put aside, even for root.
    (spool_dir / ".unreadable.unreadable").mkdir(parents=True)
    (spool_dir / "unreadable").symlink_to("/proc/self/mem")

    _add_spool_file(spool_dir, b"from the spool file\n", mtime=time.time() + 3600)

    assert _texts_of_events(event_status, 1) == ["from the spool file"]


def _logged(caplog: pytest.LogCaptureFixture, text: str) -> bool:
    """Waits until a log message contains the given text, or until a timeout"""
    return _eventually(lambda: any(text in record.getMessage() for record in caplog.records))


def test_new_spool_file_with_the_name_of_an_ignored_one_which_is_gone_is_processed(
    event_console: _EventConsole, caplog: pytest.LogCaptureFixture
) -> None:
    settings, event_status = event_console
    spool_dir = settings.paths.spool_dir.value
    # A directory with its hidden name keeps it from being put aside, even for root.
    (spool_dir / ".unreadable.unreadable").mkdir(parents=True)
    (spool_dir / "unreadable").symlink_to("/proc/self/mem")
    if not _logged(caplog, f"Cannot process spool file {spool_dir / 'unreadable'}, ignoring it"):
        pytest.fail("the unreadable spool file is not ignored")
    (spool_dir / "unreadable").unlink()
    # Taking another spool file, the event server sees that the ignored one is gone.
    _add_spool_file(spool_dir, b"first\n")
    _texts_of_events(event_status, 1)

    _add_spool_file(spool_dir, b"second\n", name="unreadable")

    assert _texts_of_events(event_status, 2) == ["first", "second"]


def test_putting_aside_a_spool_file_keeps_one_put_aside_earlier_under_the_same_name(
    event_console: _EventConsole, caplog: pytest.LogCaptureFixture
) -> None:
    spool_dir = event_console.settings.paths.spool_dir.value
    spool_dir.mkdir(parents=True)
    put_aside_earlier = spool_dir / ".unreadable.unreadable"
    put_aside_earlier.write_bytes(b"put aside earlier\n")

    # Reading it fails even for root, as nothing is mapped at the start of the address space.
    (spool_dir / "unreadable").symlink_to("/proc/self/mem")

    if not _logged(caplog, f"Cannot process spool file {spool_dir / 'unreadable'}"):
        pytest.fail("the unreadable spool file is not put aside")
    assert put_aside_earlier.read_bytes() == b"put aside earlier\n"


def test_spool_file_which_cannot_be_removed_is_not_processed(
    event_console: _EventConsole, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    settings, event_status = event_console
    spool_dir = settings.paths.spool_dir.value
    spool_dir.parent.mkdir(parents=True, exist_ok=True)
    spool_file = tmp_path / "spool_file"
    spool_file.write_bytes(b"from the spool file\n")

    # Nobody can remove or rename the entries for the file descriptors of a process, not even root,
    # so make them the spool directory, with the spool file as the standard input of the process.
    with (
        spool_file.open("rb") as stdin,
        subprocess.Popen(
            ["sleep", "60"], stdin=stdin, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        ) as process,
    ):
        try:
            spool_dir.symlink_to(f"/proc/{process.pid}/fd")
            ignored = _logged(caplog, f"Cannot process spool file {spool_dir / '0'}, ignoring it")
        finally:
            process.kill()

    assert ignored
    assert _event_texts(event_status) == []
