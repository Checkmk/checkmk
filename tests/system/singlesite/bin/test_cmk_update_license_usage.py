#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import json
import logging
from datetime import datetime, timedelta

from cmk.utils.licensing.export import RawLicenseUsageReport
from cmk.utils.licensing.helper import rot47
from tests.testlib.site import Site

LOGGER = logging.getLogger(__name__)


def _get_max_sample_time(history_json: RawLicenseUsageReport) -> datetime | None:
    return max(
        datetime.fromtimestamp(entry["sample_time"]) for entry in history_json.get("history", [])
    )


def test_cmk_update_license_usage(site: Site) -> None:
    # Clear the sample file and next_run to force license usage sample generation.
    site.delete_file(site.licensing_dir / "history.json")
    site.delete_file(site.licensing_dir / "next_run")

    # Run cmk-update-license-usage for the first time, ensure it succeeds.
    p = site.run(["cmk-update-license-usage"])
    LOGGER.info("STDOUT: %s", p.stdout)
    LOGGER.info("STDERR: %s", p.stderr)
    p.check_returncode()

    # Check that the sample timestamp is plausible.
    history_json = json.loads(rot47(site.read_file(site.licensing_dir / "history.json")))
    latest_sample_first_run = _get_max_sample_time(history_json)
    assert latest_sample_first_run is not None
    assert datetime.now() - latest_sample_first_run < timedelta(days=2)

    # Run cmk-update-license-usage for the second time, ensure it succeeds.
    p = site.run(["cmk-update-license-usage", "--force"])
    LOGGER.info("STDOUT: %s", p.stdout)
    LOGGER.info("STDERR: %s", p.stderr)
    p.check_returncode()

    # Check that no error messages were written in the licensing log.
    error_logs = site.read_file(site.logs_dir / "licensing.log")
    assert not error_logs, f"Unexpected error messages in licensing.log:\n{error_logs}"
