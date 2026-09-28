# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Run a dev server target, rebuild it whenever its sources change, and tell it so."""

import contextlib
import hashlib
import logging
import os
import signal
import subprocess
import threading
from collections.abc import Sequence
from pathlib import Path

from bazel_devserver import process_tree
from bazel_devserver.errors import DevServerError
from bazel_devserver.rebuild_loop import RebuildLoop

_logger = logging.getLogger(__name__)

_SHUTDOWN_GRACE = 5.0
"""Seconds the dev server gets to exit on SIGINT before its process tree is killed."""

_EXIT_TIMEOUT = 3.0
"""Seconds a killed dev server gets to exit."""

_BUILDING_COMMANDS = frozenset({"build", "run"})


def _state_dir() -> Path:
    cache = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
    return cache / "bazel-devserver"


class DevServer:
    """Runs *target* with *args*, rebuilds it on changes and reports each build on its stdin.

    The target speaks the iBazel protocol, like ``js_run_devserver``: it
    syncs its files whenever ``IBAZEL_BUILD_COMPLETED SUCCESS`` arrives on
    its stdin.  *startup_options* go before every bazel command,
    *build_options* after ``build`` and ``run``.

    The dev server runs in its own session, which gets SIGINT on stop:
    ``js_run_devserver`` deletes its sandbox under ``/tmp`` only on SIGINT or
    a regular exit.  Whatever is still alive after a grace period is killed.
    A dev server of the same checkout, target and arguments left behind by
    a crashed run is stopped the same way on start; while its run is alive,
    start fails.
    """

    def __init__(
        self,
        repo_root: Path,
        target: str,
        args: Sequence[str] = (),
        *,
        startup_options: Sequence[str] = (),
        build_options: Sequence[str] = (),
    ) -> None:
        self._repo_root = repo_root
        self._target = target
        self._args = tuple(args)
        self._startup_options = tuple(startup_options)
        self._build_options = tuple(build_options)
        key = "\0".join([str(repo_root.resolve()), target, *args])
        name = hashlib.sha256(key.encode()).hexdigest()[:16]
        self._pid_file = _state_dir() / f"{name}.pid"
        self._launcher = _state_dir() / f"{name}.launcher"
        self._rebuild_loop = RebuildLoop(repo_root, self._query_packages, self._build, self._notify)
        self._watching = False
        self._proc: subprocess.Popen[str] | None = None
        self._bazel_lock = threading.Lock()
        self._bazel: set[subprocess.Popen[str]] = set()
        self._stopping = False

    def start(self) -> None:
        """Build and start the dev server; returns once it runs, not once it serves."""
        self._stop_orphan()
        self._rebuild_loop.start()
        self._watching = True
        self._launcher.parent.mkdir(parents=True, exist_ok=True)
        if self._run_bazel(["run", f"--script_path={self._launcher}", self._target])[0] != 0:
            raise DevServerError(f"Building {self._target} failed")
        self._proc = subprocess.Popen(
            [str(self._launcher), *self._args],
            cwd=self._repo_root,
            stdin=subprocess.PIPE,
            start_new_session=True,
            text=True,
        )
        self._write_pid_file(self._proc.pid)

    def wait(self) -> int:
        """Block until the dev server exits by itself; returns its exit code."""
        if self._proc is None:
            raise RuntimeError("The dev server was not started")
        return self._proc.wait()

    def stop(self) -> None:
        """Stop rebuilding and stop the dev server's process tree; running bazel commands are ended."""
        if self._watching:
            self._rebuild_loop.stop(interrupt=self._end_bazel)
            self._watching = False
        else:
            self._end_bazel()
        if (proc := self._proc) is None:
            return
        remaining = process_tree.descendants(proc.pid)
        if proc.poll() is None:
            # The dev server leads its own session, so its PID stays the group's ID
            # for the group's survivors once it is reaped.
            process_tree.signal_group(proc.pid, signal.SIGINT)
            with contextlib.suppress(subprocess.TimeoutExpired):
                proc.wait(timeout=_SHUTDOWN_GRACE)
        process_tree.signal_group(proc.pid, signal.SIGKILL)
        for process in remaining:
            process_tree.kill_group_of(process)
        with contextlib.suppress(subprocess.TimeoutExpired):
            proc.wait(timeout=_EXIT_TIMEOUT)
        self._proc = None
        self._remove_pid_file(proc.pid)

    # -- Orphans ---------------------------------------------------------------

    def _stop_orphan(self) -> None:
        """Stop the dev server whose PID file a crashed run left behind."""
        try:
            pid, started, runner, runner_started = (
                int(field) for field in self._pid_file.read_text().split()
            )
        except OSError, ValueError:
            return
        if process_tree.start_time(pid) == started:
            if process_tree.start_time(runner) == runner_started:
                raise DevServerError(
                    f"{self._target} already runs with these arguments (PID {runner})",
                    recovery="Stop that run first",
                )
            _logger.warning(
                "Stopping the dev server left behind by an earlier run (PID %(pid)d)", {"pid": pid}
            )
            remaining = process_tree.descendants(pid)
            process_tree.signal_group(pid, signal.SIGINT)
            process_tree.wait_for_exit(pid, _SHUTDOWN_GRACE)
            process_tree.signal_group(pid, signal.SIGKILL)
            for process in remaining:
                process_tree.kill_group_of(process)
            process_tree.wait_for_exit(pid, _EXIT_TIMEOUT)
        self._remove_pid_file(pid)

    def _write_pid_file(self, pid: int) -> None:
        """Record the dev server and this run, each with its start time against PID reuse."""
        runner = os.getpid()
        with contextlib.suppress(OSError):
            self._pid_file.write_text(
                f"{pid} {process_tree.start_time(pid)} {runner} {process_tree.start_time(runner)}"
            )

    def _remove_pid_file(self, pid: int) -> None:
        """Remove the PID file, unless it names another run's dev server by now."""
        with contextlib.suppress(OSError, ValueError, IndexError):
            if int(self._pid_file.read_text().split()[0]) == pid:
                self._pid_file.unlink()

    # -- Bazel -----------------------------------------------------------------

    def _bazel_command(self, args: Sequence[str]) -> list[str]:
        command, *rest = args
        options = self._build_options if command in _BUILDING_COMMANDS else ()
        return ["bazel", *self._startup_options, command, *options, *rest]

    def _run_bazel(self, args: Sequence[str], *, capture: bool = False) -> tuple[int, str, str]:
        """Run bazel unless stopping, which counts as a failure; returns its exit code and output."""
        output = subprocess.PIPE if capture else None
        with self._bazel_lock:
            if self._stopping:
                return 1, "", ""
            proc = subprocess.Popen(
                self._bazel_command(args),
                cwd=self._repo_root,
                stdout=output,
                stderr=output,
                text=True,
            )
            self._bazel.add(proc)
        try:
            stdout, stderr = proc.communicate()
        finally:
            with self._bazel_lock:
                self._bazel.discard(proc)
        return proc.returncode, stdout or "", stderr or ""

    def _end_bazel(self) -> None:
        with self._bazel_lock:
            self._stopping = True
            for proc in self._bazel:
                proc.terminate()

    def _build(self) -> bool:
        return self._run_bazel(["build", self._target])[0] == 0

    def _query_packages(self) -> list[str]:
        """The main repository's packages with sources or BUILD/.bzl files of the target."""
        deps = f"deps({self._target})"
        returncode, stdout, stderr = self._run_bazel(
            ["query", f"kind('source file', {deps}) + buildfiles({deps})", "--output=package"],
            capture=True,
        )
        if returncode != 0:
            stderr_tail = "\n".join(stderr.splitlines()[-10:])
            raise DevServerError(f"Querying the sources of {self._target} failed:\n{stderr_tail}")
        return [package for package in stdout.splitlines() if not package.startswith("@")]

    def _notify(self, succeeded: bool) -> None:
        proc = self._proc
        if proc is None or proc.stdin is None:
            return
        status = "SUCCESS" if succeeded else "FAILURE"
        with contextlib.suppress(OSError, ValueError):
            proc.stdin.write(f"IBAZEL_BUILD_COMPLETED {status}\n")
            proc.stdin.flush()
