#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from tests.testlib import repo_path
from tests.testlib.playwright.helpers import PPage
from tests.testlib.playwright.pom.werks import Werks

import cmk.utils.version as cmk_version
import cmk.utils.werks

logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="skipping temporarily; werks integration is broken")
def test_werks_available(logged_in_page: PPage) -> None:
    # get the expected editions for the werks
    # NOTE: We can not use cmk_version to detect the edition due to monkey-patching in the testlib!
    # since the tests are always running in a CEE environment, we do not consider other editions
    werk_editions = {
        cmk_version.Edition.CRE.short,
        cmk_version.Edition.CEE.short,
    }
    logger.info("Checking for editions: %s", ",".join(werk_editions))
    # get all werks (list is required to retain the order)
    internal_werks = cmk.utils.werks.load_raw_files(repo_path() / ".werks")
    # sort werks by date
    internal_werks = dict(sorted(internal_werks.items(), key=lambda item: item[1]["date"]))
    # filter werks by edition
    internal_werks = {
        werk_id: werk
        for werk_id, werk in internal_werks.items()
        if werk["edition"] in werk_editions
    }
    internal_werk_ids = list(internal_werks.keys())
    assert len(internal_werk_ids) > 0, "No werks found in the repo!"

    # get all werks on the werks page (list is required to retain the order)
    werks_page = Werks(logged_in_page)
    displayed_werks = werks_page.get_recent_werks()
    displayed_werk_ids = list(displayed_werks.keys())
    assert len(displayed_werk_ids) > 0, "Werk page does not return any werks!"

    # get the relevant slice of werks for comparison (displayed werks are sorted descending)
    oldest_displayed_werk_index = internal_werk_ids.index(displayed_werk_ids[-1])
    current_internal_werk_ids = internal_werk_ids[oldest_displayed_werk_index:]
    assert (
        len(current_internal_werk_ids) > 0
    ), "Could not detect current werks! Site not in sync with repo?"

    # detect any missing werks
    different_werks = set(current_internal_werk_ids).symmetric_difference(set(displayed_werk_ids))
    if different_werks:
        missing_werks = set(current_internal_werk_ids).difference(set(displayed_werk_ids))
        if missing_werks:
            logger.warning("Missing werks detected: %s", missing_werks)
        unexpected_werks = set(displayed_werk_ids).difference(set(internal_werk_ids))
        if unexpected_werks:
            logger.warning("Unexpected werks found: %s Site ahead of repo?", unexpected_werks)
        missing_werks_cnt = len(missing_werks)
        # check if the site is outdated (i.e. missing werks are identical to the latest werks)
        latest_werks = set(current_internal_werk_ids[-missing_werks_cnt:])
        if missing_werks == latest_werks:
            logger.warning("Latest werks missing! Site not in sync with repo?")
    assert len(different_werks) == 0, "Werks mismatch! Make sure site and repo are in sync!"

    # check that all werk links share the same url format
    for werk in displayed_werks:
        response = werks_page.go(displayed_werks[werk])
        assert response and response.ok, f"Could not navigate to werk {werk}!"
