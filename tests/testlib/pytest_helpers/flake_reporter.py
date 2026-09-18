#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pytest plugin to detect and report flaky tests.

A flaky test is one that failed on a first attempt but passed after being
rerun by ``pytest-rerunfailures``.  When a session ends, the plugin writes
``flakes.json`` to a directory determined by the following priority order:

1. ``--flake-report <DIR>`` CLI arg — highest priority; if provided, always
   used, regardless of the options below.
2. Parent directory of ``--junitxml`` output.
3. Parent directory of ``--html`` (pytest-html) output.

If none of the above applies, or ``pytest-rerunfailures`` is not active,
no file is written.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

_FLAKES_FILENAME = "flakes.json"
_ALL_TEST_PHASES = {"setup", "call", "teardown"}
_TESTSUITE_DEPTH = 3  # tests/<testsuite-type>/<testsuite-name>


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class FlakeRecord(BaseModel):
    """Metadata for a single flaky test case."""

    test_path: str = Field(
        description="Path to the test module, relative to directory where pytest was run."
    )
    test_name: str = Field(description="Test-case name")
    testsuite: str | None = Field(
        description=("tests/<type>/<name> when test_path is rooted at 'tests/', otherwise null")
    )
    stack_trace: str = Field(description="Stack trace captured from the first failing run")


class FlakeReport(BaseModel):
    """Complete flake report: environment metadata plus per-test flake records."""

    # Environment details
    distro: str = Field(description="OS distribution (e.g. ubuntu-24.04)")
    edition: str = Field(description="Checkmk edition (e.g. pro, community, cloud)")
    version: str = Field(description="Checkmk version string (e.g. 2.5.0p8 or daily)")

    # Test details — empty list when no flakes were detected
    flakes: list[FlakeRecord] = Field(
        default_factory=list,
        description="Test cases that failed on first attempt but passed after rerun",
    )


# ---------------------------------------------------------------------------
# Plugin implementation
# ---------------------------------------------------------------------------


@dataclass
class _RerunState:
    """Tracks rerun state for a single test node across retry attempts."""

    stack_trace: str
    phases_passed: set[str] = field(default_factory=set)


class FlakeReporter:
    """Pytest plugin that tracks reruns and emits a JSON flake report."""

    def __init__(self) -> None:
        # nodeid → rerun state (first failure trace + phases passed in current attempt)
        self._rerun_state: dict[str, _RerunState] = {}
        self._flakes: list[FlakeRecord] = []
        self._rerun_active: bool = False

    def pytest_configure(self, config: pytest.Config) -> None:
        """Detect whether pytest-rerunfailures is under use.

        Currently, only in medium-chain runs.
        """
        self._rerun_active = (config.getoption("--reruns", default=0) or 0) > 0

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Detect tests that failed on one attempt but passed on a later one.

        Any failure in test phases of `setup`, `call`, or `teardown`
        records the test as a candidate flake. The test is confirmed as a flake
        only when all three test phases pass cleanly in a subsequent attempt.
        """
        if not self._rerun_active:
            return

        nodeid = report.nodeid
        test_phase = report.when
        # pytest-rerunfailures sets outcome of a phase to "rerun" at runtime;
        # vanilla pytest only declares `outcome` as Literal['passed', 'failed', 'skipped']
        outcome: str = report.outcome

        if outcome == "rerun":
            # Record the first failure only; subsequent failures are not overwritten.
            if nodeid not in self._rerun_state:
                self._rerun_state[nodeid] = _RerunState(_format_longrepr(report.longrepr))

        elif outcome == "passed" and nodeid in self._rerun_state:
            state = self._rerun_state[nodeid]
            if test_phase == "setup":
                # New rerun - track status of all test phases
                state.phases_passed = {"setup"}
            else:
                state.phases_passed.add(test_phase)
                if state.phases_passed == _ALL_TEST_PHASES:
                    self._flakes.append(_build_record(nodeid, state.stack_trace))
                    del self._rerun_state[nodeid]

    def pytest_addoption(self, parser: pytest.Parser) -> None:
        """Register the ``--flake-report`` CLI option."""
        parser.addoption(
            "--flake-report",
            default=None,
            metavar="DIR",
            help=(
                f"Directory where '{_FLAKES_FILENAME}' is written. "
                "When omitted, the output directory falls back to: "
                "the parent directory of --junitxml, then the parent directory of --html. "
                "If none of these apply, no flake report is written."
                "When provided, takes precedence over the directories inferred from "
                "--junitxml and --html."
            ),
        )

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        """Write ``flakes.json`` according to the output-directory priority rules."""
        output_dir = _resolve_output_dir(session.config)
        if output_dir is None or not self._rerun_active:
            return

        report = FlakeReport(
            distro=os.environ.get("DISTRO", ""),
            edition=os.environ.get("EDITION", ""),
            version=os.environ.get("VERSION", ""),
            flakes=self._flakes,
        )

        output_path = output_dir / _FLAKES_FILENAME
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report.model_dump_json(indent=2), encoding="utf-8")

        logger.info(
            "Flake report written to %s (%d flake(s) detected)",
            output_path,
            len(self._flakes),
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_output_dir(config: pytest.Config) -> Path | None:
    """Return the directory for ``flakes.json``, or ``None`` if disabled.

    Priority:
        1. ``--flake-report`` — always wins when explicitly provided.
        2. Parent directory of ``--junitxml``.
        3. Parent directory of ``--html`` (pytest-html).
        Otherwise, ``None`` — no report is written.
    """
    # highest priority: explicit --flake-report
    flake_report: str | None = config.getoption("--flake-report", default=None)
    if flake_report is not None:
        return Path(flake_report)

    # co-locate with JUnit XML
    xmlpath: str | None = config.getoption("--junitxml", default=None)
    if xmlpath:
        return Path(xmlpath).parent

    # co-locate with pytest-html report
    htmlpath: str | None = config.getoption("--html", default=None)
    if htmlpath:
        return Path(htmlpath).parent

    return None


def _format_longrepr(longrepr: object) -> str:
    """Convert a pytest ``longrepr`` to a plain string."""
    return str(longrepr) if longrepr is not None else ""


def _extract_testsuite(test_path: str) -> str | None:
    """Return ``tests/<type>/<name>``.

    Only if `test_path` is rooted at `tests`.
    Deeper nesting (e.g. ``nonfree/ultimate/``) is intentionally excluded.

    Examples,

        "tests/system/singlesite/nonfree/test_foo.py"  →  "tests/system/singlesite"
        "tests/system/multisite/test_baz.py"          →  "tests/system/multisite"
    """
    parts = Path(test_path).parts
    if not parts or parts[0] != "tests":
        return None
    # Exclude the filename, then cap at _TESTSUITE_DEPTH components
    directory_parts = parts[:-1]
    if len(directory_parts) < _TESTSUITE_DEPTH:
        return None
    return "/".join(directory_parts[:_TESTSUITE_DEPTH])


def _build_record(nodeid: str, stack_trace: str) -> FlakeRecord:
    """Build a FlakeRecord from a pytest node ID and stack trace."""
    test_path, *name_parts = nodeid.split("::")
    return FlakeRecord(
        test_path=test_path,
        test_name="::".join(name_parts) if name_parts else test_path,
        testsuite=_extract_testsuite(test_path),
        stack_trace=stack_trace,
    )
