#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Unit tests for :mod:`tests.testlib.pytest_helpers.flake_reporter`.

Tests drive the plugin via its public hooks and assert on the written
``flakes.json`` file — the only observable output.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from tests.testlib.pytest_helpers import flake_reporter
from tests.testlib.pytest_helpers.flake_reporter import (
    FlakeReport,
    FlakeReporter,
)

_NODEID = "tests/system/foo/test_bar.py::TestSuite::test_flaky"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _report(nodeid: str, when: str, outcome: str, longrepr: str = "") -> pytest.TestReport:
    r = MagicMock(spec=pytest.TestReport)
    r.nodeid = nodeid
    r.when = when
    r.outcome = outcome
    r.longrepr = longrepr if longrepr else None
    return r


def _make_session(options: dict[str, str | None]) -> MagicMock:
    """Return a mock pytest.Session whose config resolves getoption from *options*."""
    config = MagicMock(spec=pytest.Config)
    config.getoption.side_effect = lambda opt, default=None: options.get(opt, default)
    session = MagicMock(spec=pytest.Session)
    session.config = config
    return session


def _finish(reporter: FlakeReporter, output_dir: Path) -> None:
    """Run sessionfinish, directing output to *output_dir* via --flake-report."""
    reporter.pytest_sessionfinish(
        session=_make_session({"--flake-report": str(output_dir)}),
    )


def _read_report(output_dir: Path) -> FlakeReport:
    return FlakeReport.model_validate(json.loads((output_dir / "flakes.json").read_text()))


def _pass_all_phases(reporter: FlakeReporter, nodeid: str) -> None:
    for when in ("setup", "call", "teardown"):
        reporter.pytest_runtest_logreport(_report(nodeid, when, "passed"))


def _configure(reruns: int) -> pytest.PytestPluginManager:
    """Run the plugin's pytest_configure for a session with --reruns=*reruns*."""
    config = MagicMock(spec=pytest.Config)
    config.getoption.side_effect = lambda opt, default=None: (
        reruns if opt == "--reruns" else default
    )
    config.pluginmanager = pluginmanager = pytest.PytestPluginManager()
    flake_reporter.pytest_configure(config)
    return pluginmanager


def _registered_reporters(pluginmanager: pytest.PytestPluginManager) -> list[FlakeReporter]:
    return [p for p in pluginmanager.get_plugins() if isinstance(p, FlakeReporter)]


def _make_reporter() -> FlakeReporter:
    """Return the FlakeReporter registered for a session with --reruns=2."""
    (reporter,) = _registered_reporters(_configure(reruns=2))
    return reporter


def _simulate_rerun(
    reporter: FlakeReporter, nodeid: str, failing_phase: str, longrepr: str = ""
) -> None:
    """Feed reports for one failed attempt of *nodeid*.

    Mirrors pytest-rerunfailures: phases before the failing one pass normally;
    the failing phase is reported as "rerun" and no further phase of that
    attempt is reported.
    """
    phases = ["setup", "call", "teardown"]
    for phase in phases[: phases.index(failing_phase)]:
        reporter.pytest_runtest_logreport(_report(nodeid, phase, "passed"))
    reporter.pytest_runtest_logreport(_report(nodeid, failing_phase, "rerun", longrepr))


# ---------------------------------------------------------------------------
# Flake detection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("failing_phase", ["setup", "call", "teardown"])
def test_test_that_fails_then_passes_is_a_flake(tmp_path: Path, failing_phase: str) -> None:
    """A test that fails on any phase and then passes cleanly is a flake."""
    reporter = _make_reporter()
    _simulate_rerun(reporter, _NODEID, failing_phase)
    _pass_all_phases(reporter, _NODEID)
    _finish(reporter, tmp_path)

    assert len(_read_report(tmp_path).flakes) == 1


def test_consistently_failing_test_is_not_a_flake(tmp_path: Path) -> None:
    """A test that never passes is not a flake."""
    reporter = _make_reporter()
    _simulate_rerun(reporter, _NODEID, "call")
    reporter.pytest_runtest_logreport(_report(_NODEID, "setup", "passed"))
    reporter.pytest_runtest_logreport(_report(_NODEID, "call", "failed"))
    reporter.pytest_runtest_logreport(_report(_NODEID, "teardown", "passed"))
    _finish(reporter, tmp_path)

    assert _read_report(tmp_path).flakes == []


def test_partial_retry_is_not_a_flake(tmp_path: Path) -> None:
    """A test is only confirmed as a flake once all three phases of a retry pass."""
    reporter = _make_reporter()
    _simulate_rerun(reporter, _NODEID, "call")
    reporter.pytest_runtest_logreport(_report(_NODEID, "setup", "passed"))
    reporter.pytest_runtest_logreport(_report(_NODEID, "call", "passed"))
    # teardown has not fired yet
    _finish(reporter, tmp_path)

    assert _read_report(tmp_path).flakes == []


def test_multiple_reruns_before_passing_is_still_a_flake(tmp_path: Path) -> None:
    """A test that fails several times before passing is still a flake."""
    reporter = _make_reporter()
    _simulate_rerun(reporter, _NODEID, "call")
    _simulate_rerun(reporter, _NODEID, "call")
    _simulate_rerun(reporter, _NODEID, "call")
    _pass_all_phases(reporter, _NODEID)
    _finish(reporter, tmp_path)

    assert len(_read_report(tmp_path).flakes) == 1


def test_all_flaky_tests_in_a_session_are_reported(tmp_path: Path) -> None:
    """Every test that fails and then passes appears in the report."""
    nodeid_a = "tests/system/foo/test_a.py::test_one"
    nodeid_b = "tests/system/foo/test_b.py::test_two"

    reporter = _make_reporter()
    _simulate_rerun(reporter, nodeid_a, "call")
    _simulate_rerun(reporter, nodeid_b, "call")
    _pass_all_phases(reporter, nodeid_a)
    _pass_all_phases(reporter, nodeid_b)
    _finish(reporter, tmp_path)

    assert {f.test_name for f in _read_report(tmp_path).flakes} == {"test_one", "test_two"}


def test_empty_flakes_list_when_no_flakes_detected(tmp_path: Path) -> None:
    """The report is written with an empty flakes list when no flakes were observed."""
    _finish(_make_reporter(), tmp_path)

    assert _read_report(tmp_path).flakes == []


def test_no_report_written_when_no_output_dir_configured(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """No flakes.json is written when none of --flake-report, --junitxml, --html is set."""
    monkeypatch.chdir(tmp_path)
    _make_reporter().pytest_sessionfinish(session=_make_session({}))

    assert not any(tmp_path.iterdir())


def test_flakes_not_tracked_when_reruns_not_active() -> None:
    """Without --reruns, no reporter is registered, so no flakes.json is written."""
    assert _registered_reporters(_configure(reruns=0)) == []


# ---------------------------------------------------------------------------
# Flake record content
# ---------------------------------------------------------------------------


def test_flake_record_preserves_first_failure_trace(tmp_path: Path) -> None:
    """The stack trace comes from the first failing run, not later reruns."""
    reporter = _make_reporter()
    _simulate_rerun(reporter, _NODEID, "call", longrepr="AssertionError on attempt 1")
    _simulate_rerun(reporter, _NODEID, "call", longrepr="AssertionError on attempt 2")
    _pass_all_phases(reporter, _NODEID)
    _finish(reporter, tmp_path)

    flake = _read_report(tmp_path).flakes[0]
    assert "attempt 1" in flake.stack_trace
    assert "attempt 2" not in flake.stack_trace


def test_flake_record_splits_nodeid_into_path_and_name(tmp_path: Path) -> None:
    """test_path and test_name reflect the parts before and after '::' in the nodeid."""
    reporter = _make_reporter()
    _simulate_rerun(reporter, _NODEID, "call")
    _pass_all_phases(reporter, _NODEID)
    _finish(reporter, tmp_path)

    flake = _read_report(tmp_path).flakes[0]
    assert flake.test_path == "tests/system/foo/test_bar.py"
    assert flake.test_name == "TestSuite::test_flaky"


def test_testsuite_extracted_for_paths_under_tests(tmp_path: Path) -> None:
    """testsuite is tests/<type>/<name>; deeper nesting is excluded."""
    nodeid = "tests/system/singlesite/nonfree/ultimate/test_foo.py::test_bar"
    reporter = _make_reporter()
    _simulate_rerun(reporter, nodeid, "call")
    _pass_all_phases(reporter, nodeid)
    _finish(reporter, tmp_path)

    assert _read_report(tmp_path).flakes[0].testsuite == "tests/system/singlesite"


def test_testsuite_is_null_for_paths_not_rooted_at_tests(tmp_path: Path) -> None:
    """testsuite is null when the test path does not start at the tests/ directory."""
    nodeid = "packages/foo/test_bar.py::test_baz"
    reporter = _make_reporter()
    _simulate_rerun(reporter, nodeid, "call")
    _pass_all_phases(reporter, nodeid)
    _finish(reporter, tmp_path)

    assert _read_report(tmp_path).flakes[0].testsuite is None


def test_testsuite_is_null_for_shallow_paths_under_tests(tmp_path: Path) -> None:
    """testsuite is null when the path has fewer than two directory components under tests/."""
    nodeid = "tests/unit/test_foo.py::test_bar"
    reporter = _make_reporter()
    _simulate_rerun(reporter, nodeid, "call")
    _pass_all_phases(reporter, nodeid)
    _finish(reporter, tmp_path)

    assert _read_report(tmp_path).flakes[0].testsuite is None


def test_parametrized_test_name_is_preserved(tmp_path: Path) -> None:
    """Parametrized test IDs including brackets are kept intact in test_name."""
    nodeid = "tests/system/foo/test_bar.py::test_something[param1-param2]"
    reporter = _make_reporter()
    _simulate_rerun(reporter, nodeid, "call")
    _pass_all_phases(reporter, nodeid)
    _finish(reporter, tmp_path)

    assert _read_report(tmp_path).flakes[0].test_name == "test_something[param1-param2]"


# ---------------------------------------------------------------------------
# Output directory resolution
# ---------------------------------------------------------------------------


def test_report_written_next_to_junitxml(tmp_path: Path) -> None:
    """flakes.json is written to the same directory as --junitxml."""
    junit_dir = tmp_path / "results"
    junit_dir.mkdir()
    session = _make_session({"--junitxml": str(junit_dir / "junit.xml")})
    _make_reporter().pytest_sessionfinish(session=session)

    assert (junit_dir / "flakes.json").exists()


def test_report_written_next_to_html(tmp_path: Path) -> None:
    """flakes.json is written to the same directory as --html."""
    html_dir = tmp_path / "results"
    html_dir.mkdir()
    session = _make_session({"--html": str(html_dir / "report.html")})
    _make_reporter().pytest_sessionfinish(session=session)

    assert (html_dir / "flakes.json").exists()


def test_flake_report_option_takes_priority_over_junitxml(tmp_path: Path) -> None:
    """--flake-report overrides --junitxml when both are set."""
    flake_dir = tmp_path / "flake-out"
    flake_dir.mkdir()
    junit_dir = tmp_path / "junit-out"
    junit_dir.mkdir()
    session = _make_session(
        {
            "--flake-report": str(flake_dir),
            "--junitxml": str(junit_dir / "junit.xml"),
        }
    )
    _make_reporter().pytest_sessionfinish(session=session)

    assert (flake_dir / "flakes.json").exists()
    assert not (junit_dir / "flakes.json").exists()


def test_junitxml_takes_priority_over_html(tmp_path: Path) -> None:
    """--junitxml is preferred over --html when both are set."""
    junit_dir = tmp_path / "junit-out"
    junit_dir.mkdir()
    html_dir = tmp_path / "html-out"
    html_dir.mkdir()
    session = _make_session(
        {
            "--junitxml": str(junit_dir / "junit.xml"),
            "--html": str(html_dir / "report.html"),
        }
    )
    _make_reporter().pytest_sessionfinish(session=session)

    assert (junit_dir / "flakes.json").exists()
    assert not (html_dir / "flakes.json").exists()


def test_flake_report_option_takes_priority_over_html(tmp_path: Path) -> None:
    """--flake-report overrides --html when both are set."""
    flake_dir = tmp_path / "flake-out"
    flake_dir.mkdir()
    html_dir = tmp_path / "html-out"
    html_dir.mkdir()
    session = _make_session(
        {
            "--flake-report": str(flake_dir),
            "--html": str(html_dir / "report.html"),
        }
    )
    _make_reporter().pytest_sessionfinish(session=session)

    assert (flake_dir / "flakes.json").exists()
    assert not (html_dir / "flakes.json").exists()


# ---------------------------------------------------------------------------
# Report metadata
# ---------------------------------------------------------------------------


def test_report_captures_run_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The report records the distro, edition, and version from environment variables."""
    monkeypatch.setenv("DISTRO", "ubuntu-24.04")
    monkeypatch.setenv("EDITION", "pro")
    monkeypatch.setenv("VERSION", "2.5.0p8")

    _finish(_make_reporter(), tmp_path)

    report = _read_report(tmp_path)
    assert report.distro == "ubuntu-24.04"
    assert report.edition == "pro"
    assert report.version == "2.5.0p8"
