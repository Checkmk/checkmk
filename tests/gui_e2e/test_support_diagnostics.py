#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Collect tests specific to page Setup > Support diagnostics"""

import logging
import re
from pathlib import Path

import pytest
from playwright.sync_api import expect

from tests.gui_e2e.testlib.playwright.pom.dashboard import Dashboard
from tests.gui_e2e.testlib.playwright.pom.setup.background_jobs import BackgroundJobDetails
from tests.gui_e2e.testlib.playwright.pom.setup.support_diagnostics import SupportDiagnostics

logger = logging.getLogger(__name__)


def test_download_diagnostics(dashboard_page: Dashboard, request: pytest.FixtureRequest) -> None:
    """Validate diagnostic dump can be downloaded from the UI.

    * Start a background job to generate diagnostic dump.
    * Check for errors within the background job logs.
    * Diagnostic dump can be downloaded.
    """
    file_prefix: str = request.node.name
    artifacts_dir = Path(request.config.getoption("--output"))

    diagnostics = SupportDiagnostics(dashboard_page.page)
    job_details: BackgroundJobDetails = diagnostics.job_details()

    # validate job finishes
    background_job_timeout = 300_000
    expect(
        job_details.job_state_locator,
        message=f"Expected background job to complete within {background_job_timeout // 1000} sec!",
    ).to_have_text("finished", timeout=background_job_timeout)

    error_pattern = re.compile(r"ERROR.*?[:\n]")
    ignore_errors = {
        # TODO: CMK-23084; update ignore list once ticket is resolved.
        "ERROR - No Checkmk server found",
        # TODO: CMK-20811; update ignore list once ticket is resolved.
        "ERROR - No information",
    }
    # find unique errors; strip to remove whitespaces, like '\n'.
    errors = {error.strip() for error in re.findall(error_pattern, job_details.job_log)}

    # remove ignored errors
    errors.difference_update(ignore_errors)

    if errors:
        download_log = artifacts_dir / f"{file_prefix}_diagnostic_dump.log"
        logger.info("Saving log as test-artifact as '%s'", download_log)
        download_log.write_text(job_details.job_log)
        raise AssertionError(
            f"Following errors encountered while generating diagnostic dumps:\n{errors}\n"
            f"The log with errors can be found as a test-artifact within '{artifacts_dir}'."
        )

    # validate downloading the dump
    with job_details.page.expect_download() as download_info:
        job_details.progress_info_retrieve_created_dump_icon.click()
    download = download_info.value

    # validate download size
    assert download.path().stat().st_size > 0, "Downloaded 'diagnostic dump' is empty!"
