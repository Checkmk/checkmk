#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


"""Collect the performance suites' results and upload them; perftest_upload.sh calls it.

Without arguments, it collects the Bazel-based suites, which `bazel test` ran beforehand, from
bazel-testlogs into a results folder per suite. With --site, it takes the site suite's results.
In CI, it uploads each suite and checks it against the weekly, monthly and yearly baselines.
"""

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterator, Mapping, Sequence
from datetime import date
from pathlib import Path

REPO_PATH = Path(__file__).resolve().parents[3]


def branch_version() -> str:
    defines = REPO_PATH / "defines.make"
    return subprocess.run(
        ["make", "--no-print-directory", f"--file={defines}", "print-BRANCH_VERSION"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def run_date(env: Mapping[str, str]) -> date:
    """The day a run belongs to: PERFTEST_DATE, which perftest.sh fixes when it starts, or today.

    So a site run that ends after midnight is uploaded and checked as the day it started.
    """
    return date.fromisoformat(env["PERFTEST_DATE"]) if env.get("PERFTEST_DATE") else date.today()


def version(given: str, branch: str, today: date) -> str:
    """The version under test; a daily build is named after its date."""
    return given if given and given != "daily" else f"{branch}-{today:%Y.%m.%d}"


def job_suffix(custom_git_ref: str) -> str:
    """Keep a run of a custom git ref (the Jenkins parameter CUSTOM_GIT_REF) apart.

    Its job gets the ref as suffix, e.g. "_a34da07c041c" for a commit or "_166605-8" for a
    Gerrit patch set. So it neither replaces nor joins the day's default job.
    """
    if not custom_git_ref:
        return ""
    if custom_git_ref.startswith("refs/changes/"):
        # refs/changes/<last two digits>/<change>/<patch set>
        ref = custom_git_ref.removeprefix("refs/changes/").partition("/")[2]
    else:
        ref = custom_git_ref.removeprefix("refs/heads/")
    ref = re.sub("[^A-Za-z0-9]", "-", ref)
    return f"_{ref[:12] if re.fullmatch('[0-9a-f]{13,40}', ref) else ref}"


def job_name(the_version: str, edition: str, env: Mapping[str, str]) -> str:
    """A run's job in the database, and its results folder.

    An underscore in it starts the suffix, so the release part gets none.
    """
    release = env.get("RELEASE") or f"{the_version}.{edition}"
    return release.replace("_", "-") + job_suffix(env.get("CUSTOM_GIT_REF", ""))


def result_root(env: Mapping[str, str]) -> Path:
    return Path(env.get("RESULT_PATH") or REPO_PATH / "results")


def database(suite: str) -> str:
    if suite == "data-backend":
        return "performance_data_backend"
    # The default. A suite that needs another database gets its own entry here.
    return "performance_component"


def _plot(args: Sequence[str]) -> int:
    module = "tests.performance.reporting.perftest_plot"
    command = [sys.executable, "-m", module, *args]
    return subprocess.run(command, check=False, cwd=REPO_PATH).returncode


def upload(args: Sequence[str], plot: Callable[[Sequence[str]], int] = _plot) -> bool:
    """Store a suite, check the weekly baseline, then the monthly and yearly ones.

    All three run even if one fails.
    """
    reads_only = ["--skip-filesystem-writes", "--skip-database-writes"]
    return_codes = [
        plot(args),
        plot([*args, *reads_only, "--baseline-offset=30"]),
        plot([*args, *reads_only, "--baseline-offset=365"]),
    ]
    return not any(return_codes)


def _collect_bazel_suites(results: Path, name: str) -> Iterator[tuple[Path, str]]:
    """Copy each suite's outputs from bazel-testlogs; yield its root dir and database."""

    def bazel(*args: str) -> str:
        return subprocess.run(
            ["bazel", *args], cwd=REPO_PATH, check=True, capture_output=True, text=True
        ).stdout

    testlogs = Path(bazel("info", "bazel-testlogs").strip())
    suites = "tests(//tests/performance:bazel_performance)"
    for label in bazel("query", "--output=label", suites).split():
        package, _, target = label.partition(":")
        suite = package.rsplit("/", 1)[-1].removeprefix("cmk-")
        testlog_dir = testlogs / package.removeprefix("//") / target
        if not (testlog_dir / "test.outputs").is_dir():
            print(f"No test outputs for {label} under {testlog_dir} - skipping")
            continue
        benchmark_dir = results / f"performance-{suite}" / name
        benchmark_dir.mkdir(parents=True, exist_ok=True)
        for output in (testlog_dir / "test.outputs").iterdir():
            if output.is_file():
                shutil.copy2(output, benchmark_dir)
        shutil.copy2(testlog_dir / "test.xml", benchmark_dir / "junit.xml")
        yield benchmark_dir.parent, database(suite)


def main(argv: Sequence[str]) -> int:
    if argv not in ([], ["--site"]):
        print("Usage: perftest_upload.sh [--site]", file=sys.stderr)
        return 2
    env = os.environ
    branch = branch_version()
    edition = env.get("EDITION") or "cee"
    the_version = version(env.get("VERSION", ""), branch, run_date(env))
    results = result_root(env)
    if argv:
        # The site suite's baseline checks only warn.
        suites = iter([(results / "performance", "performance")])
        extra_args = ["--warn-only"]
    else:
        suites = _collect_bazel_suites(results, job_name(the_version, edition, env))
        extra_args = []
    # A suite's failed upload or check fails the job, but only after every suite is uploaded.
    rc = 0
    for root_dir, db in suites:
        if env.get("CI") and not upload(
            [
                f"--branch-version={branch}",
                f"--product-release={the_version}",
                f"--edition={edition}",
                f"--root-dir={root_dir}",
                f"--dbname={db}",
                "--dbhost=qa.lan.checkmk.net",
                "--require-database",
                "--log-level=INFO",
                "--validate-baselines",
                "--append-db",
                f"--job-suffix={job_suffix(env.get('CUSTOM_GIT_REF', ''))}",
                *extra_args,
            ]
        ):
            rc = 200
        print(f"ROOT_DIR={root_dir}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
