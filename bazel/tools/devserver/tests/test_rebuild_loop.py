# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import threading
from collections.abc import Iterator
from pathlib import Path

import pytest
from bazel_devserver.rebuild_loop import RebuildLoop


class _DevServer:
    """Fake query, build and notify callables; builds can be held until released.

    The log records each query and each notified build result, in order.
    """

    def __init__(self, packages: list[str]) -> None:
        self.packages = packages
        self.query_errors: list[Exception] = []
        self.build_results: list[bool | Exception] = []
        self.build_started = threading.Event()
        self.build_may_finish = threading.Event()
        self.build_may_finish.set()
        self.log: list[str] = []
        self._logged = threading.Condition()

    def query(self) -> list[str]:
        self._append("query")
        if self.query_errors:
            raise self.query_errors.pop(0)
        return list(self.packages)

    def build(self) -> bool:
        self.build_started.set()
        self.build_may_finish.wait()
        result = self.build_results.pop(0) if self.build_results else True
        if isinstance(result, Exception):
            raise result
        return result

    def notify(self, succeeded: bool) -> None:
        self._append("success" if succeeded else "failure")

    @property
    def notifications(self) -> list[str]:
        return [entry for entry in self.log if entry != "query"]

    def wait_for_builds(self, count: int, timeout: float = 5.0) -> bool:
        with self._logged:
            return self._logged.wait_for(lambda: len(self.notifications) >= count, timeout)

    def wait_for_queries(self, count: int, timeout: float = 5.0) -> bool:
        with self._logged:
            return self._logged.wait_for(lambda: self.log.count("query") >= count, timeout)

    def _append(self, entry: str) -> None:
        with self._logged:
            self.log.append(entry)
            self._logged.notify_all()


@pytest.fixture(name="package")
def fixture_package(tmp_path: Path) -> Path:
    package = tmp_path / "packages" / "app"
    package.mkdir(parents=True)
    (package / "app.ts").write_text("export const app = 1\n")
    return package


@pytest.fixture(name="packages")
def fixture_packages(tmp_path: Path, package: Path) -> list[str]:
    return [package.relative_to(tmp_path).as_posix()]


@pytest.fixture(name="dev_server")
def fixture_dev_server(packages: list[str]) -> _DevServer:
    return _DevServer(packages)


@pytest.fixture(name="bazelignore")
def fixture_bazelignore() -> str | None:
    """The content of the repository's ``.bazelignore``; ``None`` for none."""
    return None


@pytest.fixture(name="loop")
def fixture_loop(
    tmp_path: Path, dev_server: _DevServer, bazelignore: str | None
) -> Iterator[RebuildLoop]:
    if bazelignore is not None:
        (tmp_path / ".bazelignore").write_text(bazelignore)
    loop = RebuildLoop(tmp_path, dev_server.query, dev_server.build, dev_server.notify)
    loop.start()
    yield loop
    loop.stop(interrupt=dev_server.build_may_finish.set)


pytestmark = pytest.mark.usefixtures("loop")


def test_modified_file_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(1)


def test_failed_build_is_reported_as_failure(package: Path, dev_server: _DevServer) -> None:
    dev_server.build_results.append(False)

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(1)
    assert dev_server.notifications == ["failure"]


def test_build_error_is_reported_as_failure(package: Path, dev_server: _DevServer) -> None:
    dev_server.build_results.append(RuntimeError("bazel vanished"))

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_builds(1)
    assert dev_server.notifications == ["failure"]


def test_change_after_build_error_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    dev_server.build_results.append(RuntimeError("bazel vanished"))
    (package / "app.ts").write_text("export const app = 2\n")
    dev_server.wait_for_builds(1)

    (package / "app.ts").write_text("export const app = 3\n")

    assert dev_server.wait_for_builds(2)


def test_file_saved_by_rename_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    saved = package.parent / "app.ts.tmp"
    saved.write_text("export const app = 2\n")

    saved.replace(package / "app.ts")

    assert dev_server.wait_for_builds(1)


def test_deleted_file_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    (package / "app.ts").unlink()

    assert dev_server.wait_for_builds(1)


def test_file_added_to_new_subdirectory_triggers_rebuild(
    package: Path, dev_server: _DevServer
) -> None:
    subdirectory = package / "components"
    subdirectory.mkdir()
    dev_server.wait_for_builds(1)

    (subdirectory / "new.ts").write_text("export const new = 1\n")

    assert dev_server.wait_for_builds(2)


def test_change_during_build_triggers_another_build(package: Path, dev_server: _DevServer) -> None:
    dev_server.build_may_finish.clear()
    (package / "app.ts").write_text("export const app = 2\n")
    assert dev_server.build_started.wait(5.0)

    (package / "app.ts").write_text("export const app = 3\n")
    dev_server.build_may_finish.set()

    assert dev_server.wait_for_builds(2)


def test_stop_waits_for_the_running_build(
    package: Path, dev_server: _DevServer, loop: RebuildLoop
) -> None:
    dev_server.build_may_finish.clear()
    (package / "app.ts").write_text("export const app = 2\n")
    assert dev_server.build_started.wait(5.0)

    stopping = threading.Thread(target=loop.stop, args=(lambda: None,))
    stopping.start()
    stopping.join(0.5)

    assert stopping.is_alive()


def test_interrupted_build_is_not_reported(
    package: Path, dev_server: _DevServer, loop: RebuildLoop
) -> None:
    dev_server.build_results.append(False)
    dev_server.build_may_finish.clear()
    (package / "BUILD").write_text("")
    assert dev_server.build_started.wait(5.0)

    loop.stop(interrupt=dev_server.build_may_finish.set)

    assert dev_server.log == ["query"]


def test_build_is_reported_before_the_packages_are_queried_again(
    package: Path, dev_server: _DevServer
) -> None:
    (package / "BUILD").write_text("")

    assert dev_server.wait_for_queries(2)
    assert dev_server.log[:3] == ["query", "success", "query"]


def test_package_added_by_build_file_change_is_built(
    tmp_path: Path, package: Path, packages: list[str], dev_server: _DevServer
) -> None:
    (tmp_path / "added").mkdir()
    packages.append("added")

    (package / "BUILD").write_text("")

    assert dev_server.wait_for_builds(2)


def test_package_added_by_build_file_change_is_watched(
    tmp_path: Path, package: Path, packages: list[str], dev_server: _DevServer
) -> None:
    (tmp_path / "added").mkdir()
    packages.append("added")
    (package / "BUILD").write_text("")
    dev_server.wait_for_builds(2)

    (tmp_path / "added" / "new.ts").write_text("export const new = 1\n")

    assert dev_server.wait_for_builds(3)


def test_failed_query_is_repeated_after_next_build(package: Path, dev_server: _DevServer) -> None:
    dev_server.query_errors.append(RuntimeError("no such package"))
    (package / "BUILD").write_text("")
    dev_server.wait_for_queries(2)

    (package / "app.ts").write_text("export const app = 2\n")

    assert dev_server.wait_for_queries(3)


def test_build_file_outside_the_packages_triggers_query(
    tmp_path: Path, dev_server: _DevServer
) -> None:
    added = tmp_path / "packages" / "added"
    added.mkdir()

    (added / "BUILD").write_text("")

    assert dev_server.wait_for_queries(2)


class TestRootPackage:
    @pytest.fixture(name="packages")
    def fixture_packages(self, tmp_path: Path, package: Path) -> list[str]:
        return ["", (package.parent / "other").relative_to(tmp_path).as_posix()]

    def test_top_level_file_triggers_rebuild(self, tmp_path: Path, dev_server: _DevServer) -> None:
        (tmp_path / "MODULE.bazel").write_text("")

        assert dev_server.wait_for_builds(1)

    def test_file_below_another_directory_triggers_no_rebuild(
        self, package: Path, dev_server: _DevServer
    ) -> None:
        (package / "app.ts").write_text("export const app = 2\n")

        assert not dev_server.wait_for_builds(1, timeout=0.5)


def test_change_outside_the_packages_triggers_no_rebuild(
    tmp_path: Path, dev_server: _DevServer
) -> None:
    other = tmp_path / "packages" / "other"
    other.mkdir()

    (other / "other.ts").write_text("export const other = 1\n")

    assert not dev_server.wait_for_builds(1, timeout=0.5)


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(".app.ts.swp", id="vim swap file"),
        pytest.param("4913", id="vim write probe"),
        pytest.param("app.ts~", id="backup"),
        pytest.param("#app.ts#", id="emacs autosave"),
        pytest.param("app.ts___jb_tmp___", id="JetBrains safe write"),
        pytest.param(".coverage", id="coverage data"),
    ],
)
def test_scratch_file_triggers_no_rebuild(package: Path, dev_server: _DevServer, name: str) -> None:
    (package / name).write_text("")

    assert not dev_server.wait_for_builds(1, timeout=0.5)


def test_dot_file_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    (package / ".eslintrc.json").write_text("{}\n")

    assert dev_server.wait_for_builds(1)


def test_change_in_pycache_triggers_no_rebuild(package: Path, dev_server: _DevServer) -> None:
    pycache = package / "__pycache__"
    pycache.mkdir()

    (pycache / "app.cpython-314.pyc").write_bytes(b"")

    assert not dev_server.wait_for_builds(1, timeout=0.5)


def test_change_in_dot_directory_triggers_rebuild(package: Path, dev_server: _DevServer) -> None:
    cargo = package / ".cargo"
    cargo.mkdir()
    dev_server.wait_for_builds(1)

    (cargo / "config.toml").write_text("")

    assert dev_server.wait_for_builds(2)


class TestBazelIgnore:
    @pytest.fixture(name="bazelignore")
    def fixture_bazelignore(self) -> str:
        return "# installed by pnpm\n\npackages/app/node_modules\n"

    @pytest.mark.parametrize("name", ["module.js", "BUILD"])
    def test_change_in_ignored_directory_triggers_no_rebuild(
        self, package: Path, dev_server: _DevServer, name: str
    ) -> None:
        ignored = package / "node_modules"
        ignored.mkdir()

        (ignored / name).write_text("")

        assert not dev_server.wait_for_builds(1, timeout=0.5)

    def test_change_next_to_ignored_directory_triggers_rebuild(
        self, package: Path, dev_server: _DevServer
    ) -> None:
        (package / "node_modules.ts").write_text("export const modules = 1\n")

        assert dev_server.wait_for_builds(1)
