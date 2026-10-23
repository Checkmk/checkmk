#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for the artifact collection in :meth:`tests.testlib.system.site.Site.save_results`.

The layout this produces is what CI publishes, and it is only ever exercised on a live
site - so the emitted commands are pinned here instead.
"""

import subprocess
from pathlib import Path

import pytest

from tests.testlib.common import utils2 as utils2_module
from tests.testlib.system import site as site_module
from tests.testlib.system.site import CMKCoreType, Site

SITE_ID = "unit_test_site"


@pytest.fixture(name="recorded_commands")
def _recorded_commands(monkeypatch: pytest.MonkeyPatch) -> list[list[str]]:
    commands: list[list[str]] = []

    def fake_run(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        commands.append(args)
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    def fake_check_output(cmd: list[str], **_kwargs: object) -> str:
        commands.append(cmd)
        return ""

    monkeypatch.setattr(site_module, "check_output", fake_check_output)
    monkeypatch.setattr(site_module, "run", fake_run)
    # `makedirs` reaches for its own module's `run`, so both have to be recorded.
    monkeypatch.setattr(utils2_module, "run", fake_run)
    return commands


@pytest.fixture(name="site")
def _site(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Site:
    monkeypatch.setenv("RESULT_PATH", str(tmp_path / "results"))

    site = Site.__new__(Site)  # a real site cannot be built without an installed Checkmk
    site.id = SITE_ID
    site.root = tmp_path / "omd" / "sites" / SITE_ID
    site.root.mkdir(parents=True)
    site.result_dir.mkdir(parents=True)

    monkeypatch.setattr(Site, "core_name", lambda _self: CMKCoreType.CMC)
    monkeypatch.setattr(Site, "file_exists", lambda _self, _path, _strict=False: True)
    return site


def _copies_into(commands: list[list[str]], target: Path) -> list[list[str]]:
    return [command for command in commands if command[0] == "cp" and command[-1] == str(target)]


def test_copies_the_site_logs_into_the_log_result_directory(
    site: Site, recorded_commands: list[list[str]]
) -> None:
    site.save_results()

    log_dir = site.result_dir / "log"
    assert ["mkdir", "-p", str(log_dir)] in recorded_commands
    assert _copies_into(recorded_commands, log_dir) == [
        ["cp", "-rL", f"{site.root / 'var' / 'log'}/.", str(log_dir)]
    ]


def test_copies_the_crash_reports_into_the_crash_archive(
    site: Site, recorded_commands: list[list[str]]
) -> None:
    site.save_results()

    assert ["mkdir", "-p", str(site.crash_archive_dir)] in recorded_commands
    assert _copies_into(recorded_commands, site.crash_archive_dir) == [
        ["cp", "-r", f"{site.crash_report_dir}/.", str(site.crash_archive_dir)]
    ]


def test_copies_the_background_jobs_into_their_own_result_directory(
    site: Site, recorded_commands: list[list[str]]
) -> None:
    site.save_results()

    background_jobs_dir = site.result_dir / "background_jobs"
    assert ["mkdir", "-p", str(background_jobs_dir)] in recorded_commands
    assert _copies_into(recorded_commands, background_jobs_dir) == [
        [
            "cp",
            "-r",
            f"{site.root / 'var' / 'check_mk' / 'background_jobs'}/.",
            str(background_jobs_dir),
        ]
    ]


def test_copying_the_same_site_twice_does_not_nest_the_artifacts(
    site: Site, recorded_commands: list[list[str]]
) -> None:
    """A second save_results() must overwrite the artifacts, not copy them inside themselves."""
    site.save_results()
    first_run = list(recorded_commands)
    recorded_commands.clear()

    site.save_results()

    assert recorded_commands == first_run


@pytest.mark.usefixtures("recorded_commands")
def test_a_failing_copy_does_not_fail_the_test(site: Site, monkeypatch: pytest.MonkeyPatch) -> None:
    """Artifact collection runs in teardown and must never fail a test which passed."""

    def failing_copy(cmd: list[str], **_kwargs: object) -> str:
        raise subprocess.CalledProcessError(1, cmd, stderr="vanished mid-copy")

    monkeypatch.setattr(site_module, "check_output", failing_copy)

    site.save_results()


@pytest.mark.usefixtures("recorded_commands")
def test_a_rename_inside_the_results_fails_the_test(
    site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing races with a rename of a file we copied ourselves."""

    def failing_mv(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[0] == "mv":
            raise subprocess.CalledProcessError(1, args, stderr="no such file or directory")
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(site_module, "run", failing_mv)

    with pytest.raises(subprocess.CalledProcessError):
        site.save_results()


@pytest.mark.usefixtures("recorded_commands")
def test_results_the_test_user_cannot_be_given_fail_the_test(
    site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Results nobody can read afterwards are as useless as no results."""

    def failing_chown(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if args[0] == "chown":
            raise subprocess.CalledProcessError(1, args, stderr="operation not permitted")
        return subprocess.CompletedProcess(args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(site_module, "run", failing_chown)

    with pytest.raises(subprocess.CalledProcessError):
        site.save_results()


@pytest.mark.usefixtures("recorded_commands")
def test_a_result_directory_that_cannot_be_created_fails_the_test(
    site: Site, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The result directories are the exception: not getting one is honest trouble."""

    def failing_makedirs(args: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise subprocess.CalledProcessError(1, args, stderr="read-only file system")

    monkeypatch.setattr(utils2_module, "run", failing_makedirs)

    with pytest.raises(subprocess.CalledProcessError):
        site.save_results()


def test_the_core_history_log_is_skipped_when_the_core_never_wrote_it(
    site: Site, recorded_commands: list[list[str]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A site that never fully started has no history file, so there is nothing to copy."""
    history_log = site.core_history_log()
    monkeypatch.setattr(
        Site, "file_exists", lambda _self, path, _strict=False: Path(path) != history_log
    )

    site.save_results()

    assert not any(str(history_log) in command for command in recorded_commands)


@pytest.mark.usefixtures("recorded_commands")
def test_a_crash_report_is_renamed_for_the_browser(site: Site) -> None:
    crash_dir = site.crash_archive_dir / "gui" / "0123"
    crash_dir.mkdir(parents=True)
    (crash_dir / "crash.info").touch()

    site.save_results()

    assert (crash_dir / "crash.json").exists()


@pytest.mark.usefixtures("recorded_commands")
def test_a_failing_crash_report_rename_does_not_fail_the_test(site: Site) -> None:
    """The renaming runs in teardown and must never fail a test which passed."""
    crash_dir = site.crash_archive_dir / "gui" / "0123"
    crash_dir.mkdir(parents=True)
    (crash_dir / "crash.info").touch()
    (crash_dir / "crash.json").mkdir()  # renaming onto a directory raises OSError

    site.save_results()

    assert (crash_dir / "crash.info").exists()
