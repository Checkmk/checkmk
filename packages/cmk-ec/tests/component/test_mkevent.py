#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Runs mkevent, with a FIFO standing in for the event pipe of the Event Console"""

import fcntl
import io
import os
import re
import resource
import socket
import subprocess
import time
from collections.abc import Iterator, Mapping
from contextlib import chdir, contextmanager, suppress
from pathlib import Path
from typing import Literal

import pytest

# Instead of mkevent's default of 5 seconds, for slow machines and for giving up quickly
_GENEROUS_DELIVERY_TIMEOUT_MS = 60_000
_SHORT_DELIVERY_TIMEOUT_MS = 100


def _run_mkevent(
    *args: str,
    argv0: str | None = None,
    env: Mapping[str, str] | None = None,
    delivery_timeout_ms: int | None = None,
) -> subprocess.CompletedProcess[str]:
    mkevent = os.environ["MKEVENT"]
    return subprocess.run(
        [argv0 or mkevent, *args],
        executable=mkevent,
        capture_output=True,
        encoding="utf-8",
        env=_with_delivery_timeout(env, delivery_timeout_ms),
        timeout=30,
        check=False,
    )


def _with_delivery_timeout(
    env: Mapping[str, str] | None, delivery_timeout_ms: int | None
) -> Mapping[str, str] | None:
    if delivery_timeout_ms is None:
        return env
    return {
        **(os.environ if env is None else env),
        "MKEVENT_DELIVERY_TIMEOUT_MS": str(delivery_timeout_ms),
    }


def _send_event(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess[str], bytes]:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    # With a reader, mkevent doesn't wait, and reading hits EOF once mkevent is gone.
    reader = os.open(pipe, os.O_RDONLY | os.O_NONBLOCK)
    try:
        result = _run_mkevent("-P", str(pipe), *args)
        received = b""
        while chunk := os.read(reader, 65536):
            received += chunk
        return result, received
    finally:
        os.close(reader)


def _open_fifo(path: Path, mode: Literal["r", "w"]) -> io.FileIO:
    # Without waiting for the other end. Unlike a file descriptor, it can be closed twice.
    flags = os.O_RDONLY if mode == "r" else os.O_WRONLY
    return io.FileIO(os.open(path, flags | os.O_NONBLOCK), mode)


@contextmanager
def _started_mkevent(
    *args: str, delivery_timeout_ms: int = _GENEROUS_DELIVERY_TIMEOUT_MS
) -> Iterator[subprocess.Popen[str]]:
    with subprocess.Popen(
        [os.environ["MKEVENT"], *args],
        stderr=subprocess.PIPE,
        encoding="utf-8",
        env=_with_delivery_timeout(None, delivery_timeout_ms),
    ) as process:
        try:
            yield process
        finally:
            process.kill()  # Leaving the with statement waits for it.


def _fill(fd: int) -> None:
    os.set_blocking(fd, False)
    with suppress(BlockingIOError):
        while True:
            os.write(fd, b"x" * 65536)


def _wait_until_opened(pid: int, path: Path) -> None:
    deadline = time.monotonic() + 30
    while not _has_opened(pid, path):
        assert _process_state(pid) != "Z", f"process {pid} exited"
        assert time.monotonic() < deadline, f"process {pid} didn't open {path}"
        time.sleep(0.01)


def _has_opened(pid: int, path: Path) -> bool:
    try:
        fds = list(Path(f"/proc/{pid}/fd").iterdir())
    except PermissionError:  # Once the process has exited, nobody may look.
        return False
    for fd in fds:
        # The dynamic loader's file descriptors can be gone before we look.
        with suppress(FileNotFoundError):
            if fd.readlink() == path.resolve():
                return True
    return False


def _wait_until_sleeping(pid: int) -> None:
    deadline = time.monotonic() + 30
    while (state := _process_state(pid)) != "S":
        assert state != "Z", f"process {pid} exited"
        assert time.monotonic() < deadline, f"process {pid} didn't sleep"
        time.sleep(0.01)


def _process_state(pid: int) -> str:
    # The state follows the command name in parentheses, see proc_pid_stat(5).
    return Path(f"/proc/{pid}/stat").read_text().rpartition(")")[2].split()[0]


def test_message_is_written_as_one_line(tmp_path: Path) -> None:
    result, received = _send_event(tmp_path, "something happened")

    assert (result.returncode, received) == (0, b"something happened\n")


def test_notification_is_written_as_syslog_message(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", "2", "myhost", "myservice", "it broke", "10", "admin"
    )

    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;10;admin; myhost myservice: it broke\n", received)


def test_host_notification_is_written_as_syslog_message(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", "1", "myhost", "", "it's down", "10", "admin"
    )

    # Host state DOWN (1) is mapped like service state CRIT (2): priority crit (2).
    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;10;admin; myhost HOST: it's down\n", received)


@pytest.mark.parametrize(
    "state, service, header",
    [
        pytest.param("0", "myservice", b"<13>@", id="service OK is notice"),
        pytest.param("1", "myservice", b"<12>@", id="service WARN is warning"),
        pytest.param("2", "myservice", b"<10>@", id="service CRIT is crit"),
        pytest.param("3", "myservice", b"<11>@", id="service UNKNOWN is err"),
        pytest.param("0", "", b"<13>@", id="host UP is notice"),
        pytest.param("1", "", b"<10>@", id="host DOWN is crit"),
        pytest.param("2", "", b"<11>@", id="host UNREACHABLE is err"),
    ],
)
def test_notification_state_is_mapped_to_syslog_priority(
    tmp_path: Path, state: str, service: str, header: bytes
) -> None:
    result, received = _send_event(
        tmp_path, "-n", "1", "", state, "myhost", service, "it changed", "10", "admin"
    )

    # With facility user (1), the priority is 8 plus the severity.
    assert result.returncode == 0
    assert received.startswith(header)


def test_unset_service_sl_and_contact_fall_back_to_host_ones(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path,
        "-n",
        "1",
        "",
        "2",
        "myhost",
        "myservice",
        "it broke",
        "$_SERVICEEC_SL$",
        "$_SERVICEEC_CONTACT$",
        "20",
        "hostadmin",
    )

    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;20;hostadmin; myhost myservice: it broke\n", received)


def test_unset_sl_and_contact_become_0_and_empty(tmp_path: Path) -> None:
    result, received = _send_event(
        tmp_path,
        "-n",
        "1",
        "",
        "2",
        "myhost",
        "myservice",
        "it broke",
        "$_SERVICEEC_SL$",
        "$_SERVICEEC_CONTACT$",
        "$_HOSTEC_SL$",
        "$_HOSTEC_CONTACT$",
    )

    assert result.returncode == 0
    assert re.fullmatch(rb"<10>@\d+;0;; myhost myservice: it broke\n", received)


def test_vanished_reader_is_an_error(tmp_path: Path) -> None:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    with _open_fifo(pipe, "r") as reader, _open_fifo(pipe, "w") as writer:
        _fill(writer.fileno())
        with _started_mkevent("-P", str(pipe), "something happened") as process:
            # mkevent opens the FIFO and then waits for room in the full pipe.
            _wait_until_opened(process.pid, pipe)

            reader.close()
            _, stderr = process.communicate(timeout=30)

    assert (process.returncode, stderr) == (
        1,
        f"Cannot write to event pipe '{pipe}': Broken pipe\n",
    )


def test_reader_never_sees_a_partial_line(tmp_path: Path) -> None:
    message = "something happened"
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    with _open_fifo(pipe, "r") as reader, _open_fifo(pipe, "w") as writer:
        # A pipe of a single page with room for the message, but not its newline.
        page_size = resource.getpagesize()
        fcntl.fcntl(writer, fcntl.F_SETPIPE_SZ, page_size)
        filler = b"x" * (page_size - len(message))
        writer.write(filler)
        with _started_mkevent("-P", str(pipe), message) as process:
            _wait_until_opened(process.pid, pipe)
            _wait_until_sleeping(process.pid)  # i.e. waiting for room in the full pipe
            received_while_blocked = reader.read(65536)
            process.wait(timeout=30)
            received_afterwards = reader.read(65536)

    assert (received_while_blocked, process.returncode, received_afterwards) == (
        filler,
        0,
        b"something happened\n",
    )


def test_message_waits_for_late_reader(tmp_path: Path) -> None:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    with _started_mkevent("-P", str(pipe), "something happened") as process:
        # Like a starting Event Console, once mkevent found nobody reading, i.e. sleeps
        _wait_until_sleeping(process.pid)
        with _open_fifo(pipe, "r") as reader:
            _, stderr = process.communicate(timeout=30)
            received = reader.readall()

    assert (process.returncode, stderr, received) == (0, "", b"something happened\n")


def test_pipe_nobody_reads_is_an_error(tmp_path: Path) -> None:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)

    result = _run_mkevent(
        "-P", str(pipe), "something happened", delivery_timeout_ms=_SHORT_DELIVERY_TIMEOUT_MS
    )

    assert (result.returncode, result.stderr) == (
        1,
        (
            f"Cannot open event pipe '{pipe}': Nobody read it within 0.1 seconds. "
            "Is the Event Console running?\n"
        ),
    )


def test_pipe_removed_once_nobody_read_it_is_a_temporary_error(tmp_path: Path) -> None:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    # Removes the pipe once mkevent found nobody reading it
    fake_vanishing_fifo = str(Path(os.environ["FAKE_VANISHING_FIFO"]).absolute())

    result = _run_mkevent(
        "-P",
        str(pipe),
        "something happened",
        env={**os.environ, "LD_PRELOAD": fake_vanishing_fifo},
    )

    assert (result.returncode, result.stderr) == (
        1,
        f"Cannot open event pipe '{pipe}': No such file or directory\n",
    )


def test_notification_for_full_pipe_nobody_reads_is_an_error(tmp_path: Path) -> None:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    with _open_fifo(pipe, "r"), _open_fifo(pipe, "w") as writer:
        _fill(writer.fileno())

        result = _run_mkevent(
            "-P",
            str(pipe),
            *("-n", "1", "", "2", "myhost", "myservice", "it broke", "10", "admin"),
            delivery_timeout_ms=_SHORT_DELIVERY_TIMEOUT_MS,
        )

    assert (result.returncode, result.stderr) == (
        1,
        (
            f"Cannot write to event pipe '{pipe}': Still full after 0.1 seconds. "
            "Is the Event Console overloaded?\n"
        ),
    )


def test_notification_waits_for_room_in_full_pipe_until_the_deadline(tmp_path: Path) -> None:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    with _open_fifo(pipe, "r") as reader, _open_fifo(pipe, "w") as writer:
        # A pipe of a single page, full
        page_size = resource.getpagesize()
        fcntl.fcntl(writer, fcntl.F_SETPIPE_SZ, page_size)
        filler = b"x" * page_size
        writer.write(filler)
        with _started_mkevent(
            "-P", str(pipe), *("-n", "1", "", "2", "myhost", "myservice", "it broke", "10", "admin")
        ) as process:
            _wait_until_opened(process.pid, pipe)
            _wait_until_sleeping(process.pid)  # i.e. waiting for room in the full pipe
            received = reader.read(65536)
            process.wait(timeout=30)
            received += reader.read(65536)

    assert process.returncode == 0
    assert re.fullmatch(
        rb"<10>@\d+;10;admin; myhost myservice: it broke\n", received.removeprefix(filler)
    )


def test_plain_message_waits_for_room_in_full_pipe_after_the_deadline(tmp_path: Path) -> None:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    with _open_fifo(pipe, "r") as reader, _open_fifo(pipe, "w") as writer:
        # A pipe of a single page, full
        page_size = resource.getpagesize()
        fcntl.fcntl(writer, fcntl.F_SETPIPE_SZ, page_size)
        filler = b"x" * page_size
        writer.write(filler)
        # Already past its deadline once it has opened the FIFO
        with _started_mkevent("-P", str(pipe), "something happened", delivery_timeout_ms=0) as (
            process
        ):
            _wait_until_opened(process.pid, pipe)
            _wait_until_sleeping(process.pid)  # i.e. waiting for room in the full pipe
            received = reader.read(65536)
            process.wait(timeout=30)
            received += reader.read(65536)

    assert (process.returncode, received) == (0, filler + b"something happened\n")


def test_long_notification_once_begun_is_finished_after_the_deadline(tmp_path: Path) -> None:
    pipe = tmp_path / "events"
    os.mkfifo(pipe)
    with _open_fifo(pipe, "r") as reader, _open_fifo(pipe, "w") as writer:
        # A pipe of two pages, one of them full, so the line can take the other one only.
        page_size = resource.getpagesize()
        fcntl.fcntl(writer, fcntl.F_SETPIPE_SZ, 2 * page_size)
        filler = b"x" * page_size
        writer.write(filler)
        # Longer than PIPE_BUF, so that a part can go in, and past its deadline once opened
        with _started_mkevent(
            "-P",
            str(pipe),
            *("-n", "1", "", "2", "myhost", "myservice", "y" * 6000, "10", "admin"),
            delivery_timeout_ms=0,
        ) as process:
            _wait_until_opened(process.pid, pipe)
            _wait_until_sleeping(process.pid)  # i.e. waiting for room for the rest of the line
            received = reader.read(65536)
            process.wait(timeout=30)
            received += reader.read(65536)

    assert process.returncode == 0
    assert re.fullmatch(
        rb"<10>@\d+;10;admin; myhost myservice: y{6000}\n", received.removeprefix(filler)
    )


def test_socket_instead_of_pipe_is_a_permanent_error_without_waiting(tmp_path: Path) -> None:
    # Opening a UNIX socket fails like opening a FIFO nobody reads, with ENXIO.
    path = tmp_path / "events"
    with socket.socket(socket.AF_UNIX) as sock:
        with chdir(tmp_path):  # The absolute path can be too long for a socket.
            sock.bind(path.name)

        # Waiting for a reader would take longer than running mkevent may.
        result = _run_mkevent(
            "-P", str(path), "something happened", delivery_timeout_ms=_GENEROUS_DELIVERY_TIMEOUT_MS
        )

    assert (result.returncode, result.stderr) == (
        2,
        f"Cannot open event pipe '{path}': No such device or address\n",
    )


def test_regular_file_instead_of_pipe_is_a_permanent_error(tmp_path: Path) -> None:
    path = tmp_path / "events"
    path.write_bytes(b"something important\n")

    result = _run_mkevent("-P", str(path), "something happened")

    assert (result.returncode, result.stderr, path.read_bytes()) == (
        2,
        f"Cannot open event pipe '{path}': Not a FIFO\n",
        b"something important\n",
    )


@pytest.mark.parametrize(
    "relative_path, error",
    [
        pytest.param(".", "Is a directory", id="directory"),
        pytest.param("file/events", "Not a directory", id="below a file"),
    ],
)
def test_path_no_pipe_can_be_at_is_a_permanent_error(
    tmp_path: Path, relative_path: str, error: str
) -> None:
    (tmp_path / "file").touch()
    path = tmp_path / relative_path

    result = _run_mkevent("-P", str(path), "something happened")

    assert (result.returncode, result.stderr) == (
        2,
        f"Cannot open event pipe '{path}': {error}\n",
    )


def test_pipe_is_looked_up_below_omd_root(tmp_path: Path) -> None:
    result = _run_mkevent("something happened", env={"OMD_ROOT": str(tmp_path)})

    assert (result.returncode, result.stderr) == (
        1,
        f"Cannot open event pipe '{tmp_path}/tmp/run/mkeventd/events': No such file or directory\n",
    )


def test_pipe_is_looked_up_in_site_of_mkevent() -> None:
    result = _run_mkevent("something happened", argv0="/omd/sites/no-such-site/bin/mkevent", env={})

    assert (result.returncode, result.stderr) == (
        1,
        (
            "Cannot open event pipe '/omd/sites/no-such-site/tmp/run/mkeventd/events': "
            "No such file or directory\n"
        ),
    )


def test_empty_pipe_falls_back_to_site_of_mkevent() -> None:
    result = _run_mkevent(
        "-P", "", "something happened", argv0="/omd/sites/no-such-site/bin/mkevent", env={}
    )

    assert (result.returncode, result.stderr) == (
        1,
        (
            "Cannot open event pipe '/omd/sites/no-such-site/tmp/run/mkeventd/events': "
            "No such file or directory\n"
        ),
    )


def test_pipe_is_not_derived_from_other_paths_below_omd_sites() -> None:
    # mkevent once cut the length of "/bin/mkevent" off any such path, aborting for this one.
    result = _run_mkevent("something happened", argv0="/omd/sites/", env={})

    assert (result.returncode, result.stderr) == (
        2,
        "Cannot find event pipe: Use -P PIPE outside of a site\n",
    )


def test_pipe_outside_of_site_is_a_permanent_error() -> None:
    result = _run_mkevent("something happened", env={})

    assert (result.returncode, result.stderr) == (
        2,
        "Cannot find event pipe: Use -P PIPE outside of a site\n",
    )


@pytest.mark.parametrize(
    "args",
    [
        pytest.param([], id="no arguments"),
        pytest.param(["-P"], id="pipe option alone"),
        pytest.param(["-P", "events"], id="pipe without message"),
        pytest.param(
            ["-n", "1", "", "2", "myhost", "myservice", "it broke", "10"],
            id="notification without contact",
        ),
    ],
)
def test_too_few_arguments_are_a_permanent_usage_error(args: list[str]) -> None:
    result = _run_mkevent(*args)

    assert (result.returncode, result.stderr) == (
        2,
        (
            "Usage: mkevent [-P PIPE] 'Text of the message'\n"
            "       mkevent [-P PIPE] -n FACILITY REMOTE STATE HOST SERVICE MESSAGE SL CONTACT"
            " [HOST_SL HOST_CONTACT]\n"
        ),
    )


@pytest.mark.parametrize(
    "remote",
    [
        # inet_aton failed for the following, so mkevent took them for 255.255.255.255.
        pytest.param("1.2.3.999", id="octet out of range"),
        pytest.param("2001:db8::1", id="IPv6 address"),
        # inet_aton took the following for 127.0.0.1.
        pytest.param("0177.0.0.1", id="octal octet"),
        pytest.param("127.1", id="shorthand"),
        pytest.param("127.0.0.1 junk", id="trailing text"),
    ],
)
def test_invalid_remote_host_is_a_permanent_error(remote: str) -> None:
    result = _run_mkevent("-n", "1", remote, "2", "myhost", "myservice", "it broke", "10", "admin")

    assert (result.returncode, result.stderr) == (
        2,
        f"Cannot send to remote host '{remote}': Not an IPv4 address\n",
    )


def test_sending_to_broadcast_address_is_a_permanent_error() -> None:
    # Sending fails with EACCES without SO_BROADCAST. Unlike 255.255.255.255, this one needs no
    # default route.
    result = _run_mkevent(
        "-n", "1", "127.255.255.255", "2", "myhost", "myservice", "it broke", "10", "admin"
    )

    assert (result.returncode, result.stderr) == (
        2,
        "Cannot send to remote host '127.255.255.255': Permission denied\n",
    )
