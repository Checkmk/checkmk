# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import signal
import subprocess
import sys
import time
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from typing import Protocol

import pytest
from bazel_devserver.__main__ import main
from bazel_devserver.dev_server import DevServer
from bazel_devserver.errors import DevServerError

_TARGET = "//packages/app:dev"

_FAKE_BAZEL = """\
import os
import pathlib
import sys
import time

fake = pathlib.Path(os.environ["FAKE_DIR"])
with (fake / "bazel.log").open("a") as log:
    log.write(" ".join(sys.argv[1:]) + "\\n")
command = next(arg for arg in sys.argv[1:] if not arg.startswith("-"))
if command == "query":
    print("packages/app")
elif command == "run":
    [script] = [arg.split("=", 1)[1] for arg in sys.argv if arg.startswith("--script_path=")]
    launcher = pathlib.Path(script)
    launcher.write_text(f'#!/bin/sh\\nexec "{sys.executable}" "{fake / "dev_server.py"}" "$@"\\n')
    launcher.chmod(0o755)
    sys.exit(int(os.environ.get("FAKE_RUN", "0")))
elif os.environ.get("FAKE_BUILD") == "hang":
    (fake / "build.pid").write_text(str(os.getpid()))
    time.sleep(60)
else:
    sys.exit(int(os.environ.get("FAKE_BUILD", "0")))
"""

_FAKE_DEV_SERVER = """\
import os
import pathlib
import shutil
import signal
import sys

sandbox = pathlib.Path(sys.argv[1])
fake = pathlib.Path(os.environ["FAKE_DIR"])


def remove_sandbox(signum, frame):
    with (fake / "interrupted").open("a") as interrupted:
        interrupted.write(f"{os.getpid()}\\n")
    shutil.rmtree(sandbox)
    sys.exit(0)


signal.signal(
    signal.SIGINT, signal.SIG_IGN if os.environ.get("FAKE_SIGINT") == "ignore" else remove_sandbox
)
(fake / "dev_server.pid").write_text(str(os.getpid()))
if "FAKE_EXIT" in os.environ:
    sys.exit(int(os.environ["FAKE_EXIT"]))
sandbox.mkdir()
with (fake / "stdin").open("a") as stdin:
    for line in sys.stdin:
        stdin.write(line)
        stdin.flush()
while True:
    signal.pause()
"""


def _wait_for(condition: Callable[[], bool], timeout: float = 10.0) -> bool:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.05)
    return True


def _read_once_written(path: Path) -> str:
    _wait_for(lambda: path.is_file() and bool(path.read_text()))
    return path.read_text() if path.is_file() else ""


@pytest.fixture(name="fake")
def fixture_fake(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A fake bazel on PATH, whose launchers run a fake dev server.

    The dev server writes its PID to ``fake/dev_server.pid``, creates the
    sandbox given as its argument, and copies its stdin to ``fake/stdin``.
    On SIGINT, it adds its PID to ``fake/interrupted`` and removes the sandbox.
    """
    fake = tmp_path / "fake"
    (fake / "bin").mkdir(parents=True)
    (fake / "bazel.py").write_text(_FAKE_BAZEL)
    (fake / "dev_server.py").write_text(_FAKE_DEV_SERVER)
    bazel = fake / "bin" / "bazel"
    bazel.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{fake / "bazel.py"}" "$@"\n')
    bazel.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bazel.parent}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("FAKE_DIR", str(fake))
    (tmp_path / "packages" / "app").mkdir(parents=True)
    return fake


class _CreateDevServer(Protocol):
    def __call__(
        self, *args: str, startup_options: Sequence[str] = (), build_options: Sequence[str] = ()
    ) -> DevServer: ...


@pytest.fixture(name="dev_servers")
def fixture_dev_servers(fake: Path) -> Iterator[_CreateDevServer]:
    """Creates dev servers of the fake target with the given arguments; stops them all."""
    repo_root = fake.parent
    created: list[DevServer] = []

    def create(
        *args: str, startup_options: Sequence[str] = (), build_options: Sequence[str] = ()
    ) -> DevServer:
        created.append(
            DevServer(
                repo_root,
                _TARGET,
                args,
                startup_options=startup_options,
                build_options=build_options,
            )
        )
        return created[-1]

    yield create
    for dev_server in created:
        dev_server.stop()


@pytest.fixture(name="sandbox")
def fixture_sandbox(tmp_path: Path) -> Path:
    return tmp_path / "sandbox"


@pytest.fixture(name="dev_server")
def fixture_dev_server(dev_servers: _CreateDevServer, sandbox: Path) -> DevServer:
    return dev_servers(str(sandbox))


@pytest.mark.parametrize(
    ("build_exit_code", "line"),
    [
        pytest.param("0", "IBAZEL_BUILD_COMPLETED SUCCESS\n", id="success"),
        pytest.param("1", "IBAZEL_BUILD_COMPLETED FAILURE\n", id="failure"),
    ],
)
def test_rebuild_after_change_is_announced_to_dev_server(
    tmp_path: Path,
    fake: Path,
    monkeypatch: pytest.MonkeyPatch,
    dev_server: DevServer,
    build_exit_code: str,
    line: str,
) -> None:
    monkeypatch.setenv("FAKE_BUILD", build_exit_code)
    dev_server.start()

    (tmp_path / "packages" / "app" / "app.ts").write_text("export const app = 1\n")

    assert _read_once_written(fake / "stdin") == line


def test_stop_ends_running_build(
    tmp_path: Path, fake: Path, monkeypatch: pytest.MonkeyPatch, dev_server: DevServer
) -> None:
    monkeypatch.setenv("FAKE_BUILD", "hang")
    dev_server.start()
    (tmp_path / "packages" / "app" / "app.ts").write_text("export const app = 1\n")
    build = Path("/proc") / _read_once_written(fake / "build.pid")

    dev_server.stop()

    assert not build.exists()


def test_start_fails_when_the_dev_server_does_not_build(
    monkeypatch: pytest.MonkeyPatch, dev_server: DevServer
) -> None:
    monkeypatch.setenv("FAKE_RUN", "1")

    with pytest.raises(DevServerError, match=f"Building {_TARGET} failed"):
        dev_server.start()


def test_startup_options_precede_every_bazel_command(
    fake: Path, dev_servers: _CreateDevServer, sandbox: Path
) -> None:
    dev_server = dev_servers(str(sandbox), startup_options=["--output_base=/ob"])

    dev_server.start()

    commands = (fake / "bazel.log").read_text().splitlines()
    assert [command.split()[0] for command in commands] == ["--output_base=/ob"] * 2


def test_build_options_follow_run_but_not_query(
    fake: Path, dev_servers: _CreateDevServer, sandbox: Path
) -> None:
    dev_server = dev_servers(str(sandbox), build_options=["--symlink_prefix=/"])

    dev_server.start()

    assert [command.split()[:2] for command in (fake / "bazel.log").read_text().splitlines()] == [
        ["query", "kind('source"],
        ["run", "--symlink_prefix=/"],
    ]


def test_wait_returns_exit_code_of_dev_server(
    monkeypatch: pytest.MonkeyPatch, dev_server: DevServer
) -> None:
    monkeypatch.setenv("FAKE_EXIT", "3")
    dev_server.start()

    assert dev_server.wait() == 3


def test_stop_lets_dev_server_remove_its_sandbox(dev_server: DevServer, sandbox: Path) -> None:
    dev_server.start()
    assert _wait_for(sandbox.exists)

    dev_server.stop()

    assert not sandbox.exists()


def test_stop_kills_dev_server_that_ignores_sigint(
    fake: Path, monkeypatch: pytest.MonkeyPatch, dev_server: DevServer, sandbox: Path
) -> None:
    monkeypatch.setenv("FAKE_SIGINT", "ignore")
    dev_server.start()
    assert _wait_for(sandbox.exists)
    process = Path("/proc") / _read_once_written(fake / "dev_server.pid")

    dev_server.stop()

    assert not process.exists()


def test_start_interrupts_dev_server_left_behind_by_crashed_run(
    tmp_path: Path, fake: Path, dev_servers: _CreateDevServer, sandbox: Path
) -> None:
    with subprocess.Popen(
        [sys.executable, "-m", "bazel_devserver", _TARGET, "--", str(sandbox)],
        env={**os.environ, "BUILD_WORKSPACE_DIRECTORY": str(tmp_path)},
    ) as crashed:
        assert _wait_for(sandbox.exists)
        orphan = (fake / "dev_server.pid").read_text()
        crashed.kill()

    dev_servers(str(sandbox)).start()

    assert _read_once_written(fake / "interrupted").split() == [orphan]


def test_start_fails_while_another_run_serves_same_arguments(
    dev_servers: _CreateDevServer, sandbox: Path
) -> None:
    dev_servers(str(sandbox)).start()
    assert _wait_for(sandbox.exists)

    with pytest.raises(DevServerError, match="already runs"):
        dev_servers(str(sandbox)).start()


def test_start_leaves_dev_server_for_other_arguments_running(
    tmp_path: Path, dev_servers: _CreateDevServer, sandbox: Path
) -> None:
    dev_servers(str(sandbox)).start()
    assert _wait_for(sandbox.exists)
    other = tmp_path / "other"

    dev_servers(str(other)).start()

    assert _wait_for(other.exists)
    assert sandbox.exists()


def test_stop_leaves_dev_server_for_other_arguments_running(
    tmp_path: Path, dev_servers: _CreateDevServer, sandbox: Path
) -> None:
    other = tmp_path / "other"
    dev_servers(str(other)).start()
    dev_server = dev_servers(str(sandbox))
    dev_server.start()
    assert _wait_for(other.exists)

    dev_server.stop()

    assert other.exists()


@pytest.mark.parametrize(
    "launch",
    [
        pytest.param([], id="sigint handled"),
        pytest.param(
            ["sh", "-c", 'trap "" INT; exec "$@"', "sh"],
            id="sigint ignored, as for background jobs of a shell",
        ),
    ],
)
@pytest.mark.usefixtures("fake")
def test_ctrl_c_lets_dev_server_remove_its_sandbox(
    tmp_path: Path, sandbox: Path, launch: list[str]
) -> None:
    with subprocess.Popen(
        [*launch, sys.executable, "-m", "bazel_devserver", _TARGET, "--", str(sandbox)],
        env={**os.environ, "BUILD_WORKSPACE_DIRECTORY": str(tmp_path)},
    ) as cli:
        assert _wait_for(sandbox.exists)

        cli.send_signal(signal.SIGINT)
        cli.wait(timeout=10)

    assert not sandbox.exists()


def test_relative_label_is_rejected() -> None:
    with pytest.raises(SystemExit):
        main([":dev"])
