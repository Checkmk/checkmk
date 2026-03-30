# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""iBazel frontend supervisor subprocess lifecycle management."""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import threading
import time
from collections import deque
from pathlib import Path
from typing import TYPE_CHECKING

from cmk.dev_deploy.core import output
from cmk.dev_deploy.errors import FrontendError
from cmk.dev_deploy.frontend.ibazel_manager import ensure_ibazel

if TYPE_CHECKING:
    from typing import IO

    from cmk.dev_deploy.types import FrontendConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

IBAZEL_TARGET = "//packages/cmk-frontend-vue:vite"
"""The Bazel target for the frontend supervisor (runs Vite via iBazel)."""

_INOTIFY_SYSCTL_PATH = Path("/proc/sys/fs/inotify/max_user_watches")
"""Sysctl path for inotify watch limit on Linux."""

_INOTIFY_MIN_WATCHES = 524288
"""Minimum recommended inotify watches for large repos like Checkmk."""


def _pid_file() -> Path:
    """PID file for orphaned iBazel process detection."""
    return Path.home() / ".cache" / "cmk-dev-deploy" / "ibazel-frontend.pid"


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _check_port(host: str, port: int, timeout: float = 1.0) -> bool:
    """Return True if a TCP connection to *host:port* succeeds."""
    try:
        conn = socket.create_connection((host, port), timeout=timeout)
        conn.close()
        return True
    except (ConnectionRefusedError, OSError, TimeoutError):
        return False


def _kill_process_group(pid: int) -> None:
    """Send SIGKILL to the process group immediately (no grace period)."""
    try:
        pgid = os.getpgid(pid)
    except (ProcessLookupError, PermissionError):
        return

    try:
        os.killpg(pgid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass


def _find_bazel_children(pid: int) -> list[int]:
    """Find child processes of *pid* that are Bazel or Java workers."""
    children: set[int] = set()

    # Strategy 1: Walk /proc/{pid}/task/{tid}/children
    task_dir = Path(f"/proc/{pid}/task")
    try:
        for tid_entry in task_dir.iterdir():
            try:
                children_text = (tid_entry / "children").read_text().strip()
                if children_text:
                    for child_str in children_text.split():
                        try:
                            children.add(int(child_str))
                        except ValueError:
                            pass
            except (OSError, FileNotFoundError, ValueError, PermissionError):
                continue
    except (OSError, FileNotFoundError, PermissionError):
        # Strategy 2: Fallback -- scan /proc/ for processes with matching PPID
        try:
            for entry in Path("/proc").iterdir():
                if not entry.name.isdigit():
                    continue
                try:
                    stat_text = (entry / "stat").read_text()
                    # /proc/{pid}/stat: "pid (comm) state ppid ..."
                    # PPID is the 4th field; comm can contain spaces/parens
                    # so find the last ')' and parse from there
                    close_paren = stat_text.rfind(")")
                    if close_paren == -1:
                        continue
                    fields = stat_text[close_paren + 2 :].split()
                    # fields[0] = state, fields[1] = ppid
                    if len(fields) >= 2 and int(fields[1]) == pid:
                        children.add(int(entry.name))
                except (OSError, FileNotFoundError, ValueError, PermissionError):
                    continue
        except (OSError, FileNotFoundError, PermissionError):
            pass

    # Filter to Bazel/Java processes only
    bazel_children: list[int] = []
    for child_pid in children:
        try:
            cmdline = Path(f"/proc/{child_pid}/cmdline").read_text().lower()
            if "bazel" in cmdline or "java" in cmdline:
                bazel_children.append(child_pid)
        except (OSError, FileNotFoundError, ValueError, PermissionError):
            continue

    return bazel_children


def _collect_descendant_pids(root_pid: int) -> list[int]:
    """Recursively collect all Bazel/Java descendant PIDs, deepest first."""
    result: list[int] = []

    def _recurse(pid: int) -> None:
        try:
            children = _find_bazel_children(pid)
        except OSError:
            return
        for child in children:
            _recurse(child)  # Depth-first: children of child added before child
            if child not in result:
                result.append(child)

    _recurse(root_pid)
    return result


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
    except (OSError, FileNotFoundError, PermissionError):
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
                except (OSError, FileNotFoundError, ValueError, PermissionError):
                    continue
        except (OSError, FileNotFoundError, PermissionError):
            continue


def _check_inotify_watches() -> None:
    """Warn if inotify max_user_watches is below the recommended threshold."""
    try:
        current = int(_INOTIFY_SYSCTL_PATH.read_text().strip())
    except (OSError, ValueError):
        return  # Non-Linux or read error -- skip silently

    if current < _INOTIFY_MIN_WATCHES:
        output.warn(
            f"inotify watches too low: {current} (need {_INOTIFY_MIN_WATCHES})\n"
            "  iBazel may fail to watch all files in large repos.\n"
            "\n"
            "  Immediate fix:\n"
            f"    sudo sysctl fs.inotify.max_user_watches={_INOTIFY_MIN_WATCHES}\n"
            "\n"
            "  Permanent fix (persists across reboots):\n"
            f"    echo 'fs.inotify.max_user_watches={_INOTIFY_MIN_WATCHES}' | "
            "sudo tee -a /etc/sysctl.conf && sudo sysctl -p"
        )


# ---------------------------------------------------------------------------
# Stderr ring buffer
# ---------------------------------------------------------------------------


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
        from cmk.dev_deploy.core.output import _print_locked, GREEN, RESET

        prefix = f"{GREEN}[frontend]{RESET} "
        for line in pipe:
            stripped = line.rstrip("\n")
            self._buffer.append(stripped)
            if stripped:  # Skip empty lines from iBazel
                _print_locked(f"{prefix}{stripped}")

    def get_lines(self) -> list[str]:
        """Return the current contents of the ring buffer as a list."""
        return list(self._buffer)


# ---------------------------------------------------------------------------
# Stdout line prefixer
# ---------------------------------------------------------------------------


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
        from cmk.dev_deploy.core.output import _print_locked, GREEN, RESET

        prefix = f"{GREEN}[frontend]{RESET} "
        for line in pipe:
            stripped = line.rstrip("\n")
            if stripped:  # Skip empty lines from iBazel
                _print_locked(f"{prefix}{stripped}")


# ---------------------------------------------------------------------------
# FrontendSupervisor
# ---------------------------------------------------------------------------


class FrontendSupervisor:
    """Manages the iBazel frontend supervisor lifecycle as a subprocess."""

    def __init__(self, config: FrontendConfig, repo_root: Path) -> None:
        self._config = config
        self._repo_root = repo_root
        self._proc: subprocess.Popen[str] | None = None
        self._stdout_prefixer: _StdoutPrefixer | None = None
        self._stderr_capture: _StderrCapture | None = None

    # -- Orphan detection ----------------------------------------------------

    def _cleanup_orphaned_ibazel(self) -> None:
        """Kill orphaned iBazel processes from previous crashes."""
        if not _pid_file().exists():
            _cleanup_orphaned_port(self._config.port)
            return

        try:
            old_pid = int(_pid_file().read_text().strip())

            # Check if process is still alive
            try:
                os.kill(old_pid, 0)
            except (ProcessLookupError, PermissionError):
                # Process gone -- use port cleanup fallback
                _cleanup_orphaned_port(self._config.port)
                return

            # Verify it's actually iBazel by reading /proc/{pid}/cmdline
            try:
                cmdline = Path(f"/proc/{old_pid}/cmdline").read_text()
                if "ibazel" not in cmdline:
                    return  # Not iBazel -- leave it alone
            except OSError:
                return  # Cannot verify -- leave it alone

            # Find Bazel children BEFORE killing iBazel
            bazel_children = _find_bazel_children(old_pid)

            output.warn(f"Killing orphaned iBazel process (PID {old_pid})")
            _kill_process_group(old_pid)

            # Kill each Bazel child process group
            for child_pid in bazel_children:
                output.warn(f"Killing orphaned Bazel child process (PID {child_pid})")
                _kill_process_group(child_pid)

        except (ProcessLookupError, PermissionError, ValueError, OSError):
            pass  # Any error: just clean up PID file
        finally:
            try:
                _pid_file().unlink(missing_ok=True)
            except OSError:
                pass

        # Verify port is free after cleanup
        if _check_port("127.0.0.1", self._config.port):
            output.warn(
                f"Port {self._config.port} still in use after orphan cleanup -- "
                "pre-flight check will verify availability"
            )

    # -- PID file management -------------------------------------------------

    def _write_pid_file(self, pid: int) -> None:
        """Write the iBazel process PID to the PID file."""
        try:
            _pid_file().parent.mkdir(parents=True, exist_ok=True)
            _pid_file().write_text(str(pid))
        except OSError:
            pass

    def _remove_pid_file(self) -> None:
        """Remove the PID file if it exists.  Non-critical."""
        try:
            _pid_file().unlink(missing_ok=True)
        except OSError:
            pass

    # -- Pre-flight checks ---------------------------------------------------

    def _check_port_available(self) -> None:
        """Raise :class:`FrontendError` if port is already in use."""
        if _check_port("127.0.0.1", self._config.port):
            raise FrontendError(
                f"Port {self._config.port} is already in use",
                recovery=(
                    "This may be a stale cmk-dev-deploy iBazel instance.\n"
                    f"Try: kill $(lsof -t -i :{self._config.port})"
                ),
            )

    # -- Subprocess management -----------------------------------------------

    def _spawn_ibazel(self) -> None:
        """Spawn iBazel via ``ibazel run`` in a new process group."""
        ibazel_bin = ensure_ibazel()
        cmd = [str(ibazel_bin), "run", IBAZEL_TARGET]
        self._proc = subprocess.Popen(
            cmd,
            cwd=str(self._repo_root),
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
        """Poll port until iBazel/Vite is reachable or timeout expires."""
        output.info("Initial Bazel build started -- build output will appear below")
        deadline = time.monotonic() + self._config.startup_timeout
        while time.monotonic() < deadline:
            if _check_port("127.0.0.1", self._config.port):
                # Defense: verify process is still alive
                if self._proc is not None and self._proc.poll() is None:
                    return True
                return False
            time.sleep(self._config.health_check_interval)
        return False

    # -- Public API ----------------------------------------------------------

    def start(self) -> None:
        """Start iBazel and block until the port becomes reachable."""
        self._cleanup_orphaned_ibazel()
        _check_inotify_watches()
        self._check_port_available()
        self._spawn_ibazel()
        if not self._wait_until_ready():
            crash_lines = self.get_crash_report()
            self.stop()
            msg = (
                f"iBazel frontend supervisor failed to start within {self._config.startup_timeout}s"
            )
            if crash_lines:
                stderr_tail = "\n".join(crash_lines[-10:])
                msg += f"\n\nLast stderr output:\n{stderr_tail}"
            raise FrontendError(
                msg,
                recovery="Run cmk-dev-deploy --frontend again",
            )

    def stop(self) -> None:
        """SIGKILL the full process tree and verify port is freed. No-op if not started."""
        if self._proc is None:
            self._remove_pid_file()
            return

        # Even if proc has exited, we still need to clean up descendants
        if self._proc.poll() is not None:
            # Process dead but children may survive
            descendants = _collect_descendant_pids(self._proc.pid)
            for child_pid in descendants:
                _kill_process_group(child_pid)
            # Port cleanup fallback
            time.sleep(0.2)
            if _check_port("127.0.0.1", self._config.port):
                _cleanup_orphaned_port(self._config.port)
            self._proc = None
            self._remove_pid_file()
            return

        # 1. Collect all descendant PIDs before killing (they may disappear during kill)
        descendants = _collect_descendant_pids(self._proc.pid)

        # 2. Kill the iBazel process group (existing behavior)
        _kill_process_group(self._proc.pid)

        # 3. Kill each descendant's process group (bottom-up order)
        for child_pid in descendants:
            _kill_process_group(child_pid)

        # 4. Wait for iBazel to actually exit
        try:
            self._proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            pass

        # 5. Verify port is free; nuclear fallback if not
        time.sleep(0.2)  # Brief pause for OS to release port
        if _check_port("127.0.0.1", self._config.port):
            output.warn(f"Port {self._config.port} still in use after stop -- attempting cleanup")
            _cleanup_orphaned_port(self._config.port)

        self._proc = None
        self._remove_pid_file()

    def is_running(self) -> bool:
        """Return True if the iBazel process is still alive."""
        return self._proc is not None and self._proc.poll() is None

    def get_crash_report(self) -> list[str]:
        """Return the last N lines of stderr for crash diagnostics."""
        if self._stderr_capture is not None:
            self._stderr_capture._thread.join(timeout=1.0)  # noqa: SLF001
            return self._stderr_capture.get_lines()
        return []
