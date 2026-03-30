# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Unit tests for cmk.dev_deploy.cli (argument parsing)."""

from __future__ import annotations

import pytest

from cmk.dev_deploy.cli import parse_args

# ---------------------------------------------------------------------------
# Default values
# ---------------------------------------------------------------------------


class TestDefaults:
    """When no arguments are given, every flag should have its default."""

    def test_defaults(self) -> None:
        args = parse_args([])
        assert args.site is None
        assert args.info is False
        assert args.no_restart is False
        assert args.full is False
        assert args.verbose == 0
        assert args.dry_run is False
        assert args.watch is False
        assert args.jobs == 4
        assert args.rebuild_manifest is False
        assert args.frontend is False
        assert args.purge is False


# ---------------------------------------------------------------------------
# Individual flags
# ---------------------------------------------------------------------------


class TestIndividualFlags:
    """Each flag can be set independently."""

    def test_site_long(self) -> None:
        assert parse_args(["--site", "v260"]).site == "v260"

    def test_site_short(self) -> None:
        assert parse_args(["-s", "v260"]).site == "v260"

    def test_info(self) -> None:
        assert parse_args(["--info"]).info is True

    def test_no_restart(self) -> None:
        assert parse_args(["--no-restart"]).no_restart is True

    def test_full(self) -> None:
        assert parse_args(["--full"]).full is True

    def test_dry_run_long(self) -> None:
        assert parse_args(["--dry-run"]).dry_run is True

    def test_dry_run_short(self) -> None:
        assert parse_args(["-n"]).dry_run is True

    def test_watch_long(self) -> None:
        assert parse_args(["--watch"]).watch is True

    def test_watch_short(self) -> None:
        assert parse_args(["-w"]).watch is True

    def test_jobs_long(self) -> None:
        assert parse_args(["--jobs", "8"]).jobs == 8

    def test_jobs_short(self) -> None:
        assert parse_args(["-j", "8"]).jobs == 8

    def test_rebuild_manifest(self) -> None:
        assert parse_args(["--rebuild-manifest"]).rebuild_manifest is True

    def test_frontend(self) -> None:
        assert parse_args(["--frontend"]).frontend is True

    def test_purge(self) -> None:
        assert parse_args(["--purge"]).purge is True


# ---------------------------------------------------------------------------
# Verbose counting
# ---------------------------------------------------------------------------


class TestVerbose:
    """Verbose flag counts repetitions."""

    def test_single_v(self) -> None:
        assert parse_args(["-v"]).verbose == 1

    def test_double_v(self) -> None:
        assert parse_args(["-vv"]).verbose == 2

    def test_triple_v(self) -> None:
        assert parse_args(["-vvv"]).verbose == 3

    def test_long_verbose_once(self) -> None:
        assert parse_args(["--verbose"]).verbose == 1

    def test_long_verbose_twice(self) -> None:
        assert parse_args(["--verbose", "--verbose"]).verbose == 2


# ---------------------------------------------------------------------------
# Jobs validation
# ---------------------------------------------------------------------------


class TestJobsValidation:
    """Jobs < 1 are clamped to 1."""

    def test_zero_clamped_to_one(self) -> None:
        assert parse_args(["--jobs", "0"]).jobs == 1

    def test_negative_clamped_to_one(self) -> None:
        assert parse_args(["--jobs", "-1"]).jobs == 1

    def test_one_is_valid(self) -> None:
        assert parse_args(["--jobs", "1"]).jobs == 1

    def test_large_value(self) -> None:
        assert parse_args(["--jobs", "16"]).jobs == 16


# ---------------------------------------------------------------------------
# Mutual exclusivity -- watch conflicts
# ---------------------------------------------------------------------------


class TestWatchConflicts:
    """--watch conflicts with --dry-run, --info."""

    def test_watch_dry_run(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--watch", "--dry-run"])

    def test_watch_info(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--watch", "--info"])


# ---------------------------------------------------------------------------
# Mutual exclusivity -- full conflicts
# ---------------------------------------------------------------------------


class TestFullConflicts:
    """--full conflicts with --info."""

    def test_full_info(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--full", "--info"])


# ---------------------------------------------------------------------------
# Mutual exclusivity -- frontend conflicts
# ---------------------------------------------------------------------------


class TestFrontendConflicts:
    """--frontend conflicts with --dry-run, --info."""

    def test_frontend_dry_run(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--frontend", "--dry-run"])

    def test_frontend_info(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--frontend", "--info"])


# ---------------------------------------------------------------------------
# Mutual exclusivity -- purge conflicts
# ---------------------------------------------------------------------------


class TestPurgeConflicts:
    """--purge conflicts with --full, --dry-run, --watch, --info, --frontend, --since."""

    def test_purge_full(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--purge", "--full"])

    def test_purge_dry_run(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--purge", "--dry-run"])

    def test_purge_watch(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--purge", "--watch"])

    def test_purge_info(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--purge", "--info"])

    def test_purge_frontend(self) -> None:
        with pytest.raises(SystemExit):
            parse_args(["--purge", "--frontend"])


# ---------------------------------------------------------------------------
# Combined valid flags
# ---------------------------------------------------------------------------


class TestValidCombinations:
    """Flags that are allowed together should not raise."""

    def test_full_verbose_no_restart(self) -> None:
        args = parse_args(["--full", "-vv", "--no-restart"])
        assert args.full is True
        assert args.verbose == 2
        assert args.no_restart is True

    def test_site_with_dry_run(self) -> None:
        args = parse_args(["-s", "mysite", "--dry-run"])
        assert args.site == "mysite"
        assert args.dry_run is True

    def test_watch_with_verbose_and_jobs(self) -> None:
        args = parse_args(["--watch", "-vv", "-j", "2"])
        assert args.watch is True
        assert args.verbose == 2
        assert args.jobs == 2

    def test_purge_alone(self) -> None:
        args = parse_args(["--purge"])
        assert args.purge is True

    def test_purge_with_verbose_and_site(self) -> None:
        args = parse_args(["--purge", "-v", "-s", "mysite"])
        assert args.purge is True
        assert args.verbose == 1
        assert args.site == "mysite"
