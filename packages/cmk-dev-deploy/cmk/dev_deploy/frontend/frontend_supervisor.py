# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Vite dev server lifecycle: build, launch, readiness, and shutdown."""

import contextlib
import os
import signal
import socket
import subprocess
import threading
import time
from collections import deque
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

from bazel_devserver import process_tree

from cmk.dev_deploy.core import output
from cmk.dev_deploy.core.bazel import _cache_dir, bazel_command, command_options, startup_options
from cmk.dev_deploy.errors import FrontendError

if TYPE_CHECKING:
    from typing import IO

    from cmk.dev_deploy.types import Edition, FrontendConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VITE_TARGET = "//packages/cmk-frontend-vue:vite"
"""The js_run_devserver target that runs Vite."""

RUNNER_TARGET = "//bazel/tools/devserver"
"""The tool that runs the dev server and rebuilds it whenever its sources change."""

_INOTIFY_SYSCTL_PATH = Path("/proc/sys/fs/inotify/max_user_watches")
"""Sysctl path for inotify watch limit on Linux."""

_INOTIFY_MIN_WATCHES = 524288
"""Minimum recommended inotify watches for large repos like Checkmk."""

_SHUTDOWN_GRACE = 15.0
"""Seconds the runner gets to exit on SIGINT before its process group is killed.

Longer than the runner takes to stop the dev server: 5 s for it to exit on
SIGINT, and 3 s once it is killed.
"""


def _pid_file() -> Path:
    """PID file for orphaned runner detection."""
    return _cache_dir() / "frontend-dev-server.pid"


def _launcher() -> Path:
    """Launcher script that ``bazel run --script_path`` writes for the runner."""
    return _cache_dir() / "frontend-dev-server"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to *host:port* succeeds."""
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
        return True
    except ConnectionRefusedError, OSError, TimeoutError:
        return False


def _kill_process_group(pid: int) -> None:
    """Send SIGKILL to the process group of *pid*."""
    try:
        pgid = os.getpgid(pid)
    except ProcessLookupError, PermissionError:
        return

    process_tree.signal_group(pgid, signal.SIGKILL)


def _cleanup_orphaned_port(port: int) -> None:
    """Kill Bazel/Java processes holding *port* via /proc/net/tcp scan."""
    if not _check_port("127.0.0.1", port):
        return  # Port is free -- nothing to do

    # Convert port to hex for /proc/net/tcp matching
    hex_port = f"{port:04X}"

    # Scan /proc/net/tcp to find PID holding the port
    # Format: "  sl  local_address rem_address   st ..."
    # local_address is "hex_ip:hex_port"
    try:
        tcp_lines = Path("/proc/net/tcp").read_text().splitlines()
    except OSError, FileNotFoundError, PermissionError:
        return

    # Find inodes matching our port
    matching_inodes: set[str] = set()
    for line in tcp_lines[1:]:  # Skip header
        fields = line.split()
        if len(fields) < 10:
            continue
        local_addr = fields[1]
        if ":" not in local_addr:
            continue
        _, port_hex = local_addr.rsplit(":", 1)
        if port_hex.upper() == hex_port:
            matching_inodes.add(fields[9])  # inode field

    if not matching_inodes:
        return

    # Find PIDs owning these inodes by scanning /proc/{pid}/fd/
    for pid_entry in Path("/proc").iterdir():
        if not pid_entry.name.isdigit():
            continue
        pid_candidate = int(pid_entry.name)
        try:
            fd_dir = pid_entry / "fd"
            for fd_link in fd_dir.iterdir():
                try:
                    target = fd_link.resolve(strict=False)
                    target_str = str(target)
                    for inode in matching_inodes:
                        if f"socket:[{inode}]" in target_str:
                            # Found the PID -- verify it's Bazel/Java
                            try:
                                cmdline = Path(f"/proc/{pid_candidate}/cmdline").read_text().lower()
                                if "bazel" in cmdline or "java" in cmdline:
                                    output.warn(
                                        f"Killing orphaned Bazel process on port {port} "
                                        f"(PID {pid_candidate})"
                                    )
                                    _kill_process_group(pid_candidate)
                                    return
                            except (
                                OSError,
                                FileNotFoundError,
                                ValueError,
                                PermissionError,
                            ):
                                pass
                except OSError, FileNotFoundError, ValueError, PermissionError:
                    continue
        except OSError, FileNotFoundError, PermissionError:
            continue


def _wait_for_port_release(port: int, timeout: float = 3.0) -> bool:
    """Return True once nothing listens on *port*; killed processes release it only on exit."""
    deadline = time.monotonic() + timeout
    while _check_port("127.0.0.1", port):
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.1)
    return True


def _check_inotify_watches() -> None:
    """Warn if inotify max_user_watches is below the recommended threshold."""
    try:
        current = int(_INOTIFY_SYSCTL_PATH.read_text().strip())
    except OSError, ValueError:
        return  # Non-Linux or read error -- skip silently

    if current < _INOTIFY_MIN_WATCHES:
        output.warn(
            f"inotify watches too low: {current} (need {_INOTIFY_MIN_WATCHES})\n"
            "  The frontend dev server may miss changes in large repos.\n"
            "\n"
            "  Immediate fix:\n"
            f"    sudo sysctl fs.inotify.max_user_watches={_INOTIFY_MIN_WATCHES}\n"
            "\n"
            "  Permanent fix (persists across reboots):\n"
            f"    echo 'fs.inotify.max_user_watches={_INOTIFY_MIN_WATCHES}' | "
            "sudo tee -a /etc/sysctl.conf && sudo sysctl -p"
        )


# ---------------------------------------------------------------------------
# Output prefixing
# ---------------------------------------------------------------------------


def _print_frontend_line(line: str) -> None:
    from cmk.dev_deploy.core.output import _print_locked, GREEN, RESET

    if stripped := line.rstrip("\n"):
        _print_locked(f"{GREEN}[frontend]{RESET} {stripped}")


class _StderrCapture:
    """Daemon thread that streams stderr with [frontend] prefix and keeps a ring buffer."""

    def __init__(self, pipe: IO[str], maxlines: int = 50) -> None:
        self._buffer: deque[str] = deque(maxlen=maxlines)
        self._thread = threading.Thread(
            target=self._reader,
            args=(pipe,),
            daemon=True,
        )
        self._thread.start()

    def _reader(self, pipe: IO[str]) -> None:
        """Read lines from *pipe*, print with prefix, and store in ring buffer."""
        for line in pipe:
            self._buffer.append(line.rstrip("\n"))
            _print_frontend_line(line)

    def get_lines(self) -> list[str]:
        """Return the current contents of the ring buffer as a list."""
        return list(self._buffer)


class _StdoutPrefixer:
    """Daemon thread that re-emits stdout with [frontend] prefix."""

    def __init__(self, pipe: IO[str]) -> None:
        self._thread = threading.Thread(
            target=self._reader,
            args=(pipe,),
            daemon=True,
        )
        self._thread.start()

    def _reader(self, pipe: IO[str]) -> None:
        for line in pipe:
            _print_frontend_line(line)


# ---------------------------------------------------------------------------
# FrontendSupervisor
# ---------------------------------------------------------------------------


class FrontendSupervisor:
    """Runs the Vite dev server through the runner and waits until it serves.

    The runner, ``//bazel/tools/devserver``, rebuilds the dev server's
    target whenever its sources change, tells the dev server to sync, and
    stops the dev server on SIGINT.  It runs its Bazel commands on the
    deploy server, for the site's *edition* like the deploy builds, so that
    the server keeps its analysis cache between the two.
    """

    def __init__(self, config: FrontendConfig, repo_root: Path, *, edition: Edition) -> None:
        self._config = config
        self._repo_root = repo_root
        self._edition_option = f"--cmk_edition={edition}"
        self._proc: subprocess.Popen[str] | None = None
        self._stdout_prefixer: _StdoutPrefixer | None = None
        self._stderr_capture: _StderrCapture | None = None
        self._bazel_lock = threading.Lock()
        self._bazel: subprocess.Popen[str] | None = None
        self._stopping = False

    # -- Orphan detection ----------------------------------------------------

    def _cleanup_orphaned_server(self) -> None:
        """Stop an orphaned runner from a previous crash.

        It gets SIGINT first, which makes it stop the dev server.  Whatever is
        still alive after the grace period is killed.
        """
        if not _pid_file().exists():
            _cleanup_orphaned_port(self._config.port)
            return

        try:
            old_pid = int(_pid_file().read_text().strip())

            try:
                os.kill(old_pid, 0)
            except ProcessLookupError, PermissionError:
                _cleanup_orphaned_port(self._config.port)
                return

            try:
                cmdline = Path(f"/proc/{old_pid}/cmdline").read_text()
                if VITE_TARGET not in cmdline:
                    return  # PID reused by another process -- leave it alone
            except OSError:
                return  # Cannot verify -- leave it alone

            # Look the group up while the PID is known to be the runner's
            pgid = os.getpgid(old_pid)

            output.warn(f"Stopping orphaned frontend dev server (PID {old_pid})")
            process_tree.signal_group(pgid, signal.SIGINT)
            process_tree.wait_for_exit(old_pid, _SHUTDOWN_GRACE)
            process_tree.signal_group(pgid, signal.SIGKILL)

        except ProcessLookupError, PermissionError, ValueError, OSError:
            pass  # Any error: just clean up PID file
        finally:
            with contextlib.suppress(OSError):
                _pid_file().unlink(missing_ok=True)

        if not _wait_for_port_release(self._config.port):
            output.warn(
                f"Port {self._config.port} still in use after orphan cleanup -- "
                "pre-flight check will verify availability"
            )

    # -- PID file management -------------------------------------------------

    def _write_pid_file(self, pid: int) -> None:
        """Write the runner's PID to the PID file."""
        try:
            _pid_file().parent.mkdir(parents=True, exist_ok=True)
            _pid_file().write_text(str(pid))
        except OSError:
            pass

    def _remove_pid_file(self) -> None:
        """Remove the PID file if it exists.  Non-critical."""
        with contextlib.suppress(OSError):
            _pid_file().unlink(missing_ok=True)

    # -- Pre-flight checks ---------------------------------------------------

    def _check_port_available(self) -> None:
        """Raise :class:`FrontendError` if port is already in use."""
        if _check_port("127.0.0.1", self._config.port):
            raise FrontendError(
                f"Port {self._config.port} is already in use",
                recovery=(
                    "This may be a stale cmk-dev-deploy frontend dev server.\n"
                    f"Try: kill $(lsof -t -i :{self._config.port})"
                ),
            )

    # -- Bazel ---------------------------------------------------------------

    def _run_bazel(self, args: Sequence[str]) -> bool:
        """Run bazel on the deploy server, printing its output; True on success."""
        with self._bazel_lock:
            if self._stopping:
                return False
            proc = self._bazel = subprocess.Popen(
                bazel_command(args, self._repo_root),
                cwd=str(self._repo_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
            )
        for line in proc.stdout:  # type: ignore[union-attr]
            _print_frontend_line(line)
        return proc.wait() == 0

    def _end_bazel(self) -> None:
        with self._bazel_lock:
            self._stopping = True
            if self._bazel is not None:
                self._bazel.terminate()

    # -- Subprocess management -----------------------------------------------

    def _spawn_launcher(self) -> None:
        """Start the runner for the dev server in a new process group.

        The runner gets SIGINT once cdd is gone, however cdd ended, so it
        never outlives cdd with its rebuilds and dev server.
        """
        options = [
            *(f"--bazel_startup_option={option}" for option in startup_options(self._repo_root)),
            *(
                f"--bazel_build_option={option}"
                for option in [*command_options("build"), self._edition_option]
            ),
        ]
        self._proc = subprocess.Popen(
            ["setpriv", "--pdeathsig", "INT", str(_launcher()), *options, VITE_TARGET],
            cwd=str(self._repo_root),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            start_new_session=True,
            text=True,
        )
        self._write_pid_file(self._proc.pid)
        self._stdout_prefixer = _StdoutPrefixer(
            self._proc.stdout,  # type: ignore[arg-type]
        )
        self._stderr_capture = _StderrCapture(
            self._proc.stderr,  # type: ignore[arg-type]
            maxlines=self._config.stderr_buffer_lines,
        )

    def _wait_until_ready(self) -> bool:
        """Poll port until Vite is reachable, the runner exits, or the timeout expires."""
        deadline = time.monotonic() + self._config.startup_timeout
        while time.monotonic() < deadline:
            if not self.is_running():
                return False
            if _check_port("127.0.0.1", self._config.port):
                return True
            time.sleep(self._config.health_check_interval)
        return False

    def _launch(self) -> None:
        _launcher().parent.mkdir(parents=True, exist_ok=True)
        # Built here, so that the startup timeout does not include building the dev server
        if not self._run_bazel(["build", self._edition_option, VITE_TARGET, RUNNER_TARGET]):
            raise FrontendError(
                f"Building {VITE_TARGET} or {RUNNER_TARGET} failed",
                recovery="Fix the build errors above and run cmk-dev-deploy --frontend again",
            )
        if not self._run_bazel(
            ["run", self._edition_option, f"--script_path={_launcher()}", RUNNER_TARGET]
        ):
            raise FrontendError(
                f"Writing the launcher of {RUNNER_TARGET} failed",
                recovery="Run cmk-dev-deploy --frontend again",
            )
        self._spawn_launcher()
        if not self._wait_until_ready():
            msg = (
                f"Frontend dev server failed to start within {self._config.startup_timeout}s"
                if self.is_running()
                else "Frontend dev server exited during startup"
            )
            if crash_lines := self.get_crash_report():
                stderr_tail = "\n".join(crash_lines[-10:])
                msg += f"\n\nLast stderr output:\n{stderr_tail}"
            raise FrontendError(
                msg,
                recovery="Run cmk-dev-deploy --frontend again",
            )

    # -- Public API ----------------------------------------------------------

    def start(self) -> None:
        """Build and start the dev server, and block until the port becomes reachable."""
        self._cleanup_orphaned_server()
        _check_inotify_watches()
        self._check_port_available()
        output.info("Initial Bazel build started -- build output will appear below")
        try:
            self._launch()
        except BaseException:
            self.stop()
            raise

    def stop(self) -> None:
        """Stop the runner's process group and verify port is freed.

        The runner gets SIGINT first, which makes it stop the dev server.
        Whatever is still alive after the grace period is killed.

        A running bazel command is ended.  No-op if not started.
        """
        self._end_bazel()

        if self._proc is None:
            self._remove_pid_file()
            return

        # The runner leads its own session, so its PID is the group's ID,
        # which stays valid for the group's survivors once it is reaped.
        if self._proc.poll() is None:
            process_tree.signal_group(self._proc.pid, signal.SIGINT)
            with contextlib.suppress(subprocess.TimeoutExpired):
                self._proc.wait(timeout=_SHUTDOWN_GRACE)
        process_tree.signal_group(self._proc.pid, signal.SIGKILL)
        with contextlib.suppress(subprocess.TimeoutExpired):
            self._proc.wait(timeout=3)

        # Verify port is free; nuclear fallback if not
        time.sleep(0.2)  # Brief pause for OS to release port
        if _check_port("127.0.0.1", self._config.port):
            output.warn(f"Port {self._config.port} still in use after stop -- attempting cleanup")
            _cleanup_orphaned_port(self._config.port)

        self._proc = None
        self._remove_pid_file()

    def is_running(self) -> bool:
        """Return True if the dev server is still alive."""
        return self._proc is not None and self._proc.poll() is None

    def get_crash_report(self) -> list[str]:
        """Return the last N lines of stderr for crash diagnostics."""
        if self._stderr_capture is not None:
            self._stderr_capture._thread.join(timeout=1.0)  # noqa: SLF001
            return self._stderr_capture.get_lines()
        return []
