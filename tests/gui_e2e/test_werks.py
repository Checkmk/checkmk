#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging

import pytest

from tests.testlib.playwright.pom.login import LoginPage
from tests.testlib.playwright.pom.werks import Werks
from tests.testlib.repo import repo_path

import cmk.utils.werks

from cmk.werks.models import Edition

logger = logging.getLogger(__name__)


@pytest.mark.skip(reason="skip until CMK-17126.")
def test_werks_available(logged_in_page: LoginPage) -> None:
    # get the expected editions for the werks
    # NOTE: We can not use cmk_version to detect the edition due to monkey-patching in the testlib!
    # since the tests are always running in a CEE environment, we do not consider other editions
    werk_editions = {
        Edition.CRE,
        Edition.CEE,
    }
    logger.info("Checking for editions: %s", ",".join(str(e.value) for e in werk_editions))
    # get all werks (list is required to retain the order)
    raw_werks = cmk.utils.werks.load_raw_files(repo_path() / ".werks")
    # sort werks by date and by edition
    werks_from_repo = {
        werk.id: werk
        for werk in sorted(raw_werks, key=lambda item: item.date)
        if werk.edition in werk_editions
    }
    werk_ids_from_repo = list(werks_from_repo.keys())
    assert len(werk_ids_from_repo) > 0, "No werks found in the repo!"

    # get all werks on the werks page (list is required to retain the order)
    werks_page = Werks(logged_in_page.page)
    displayed_werks = werks_page.get_recent_werks()
    displayed_werk_ids = list(displayed_werks.keys())
    assert len(displayed_werk_ids) > 0, "Checkmk site does not display any werks!"

    # get the relevant slice of werks for comparison (displayed werks are sorted descending)
    oldest_displayed_werk_id_index = werk_ids_from_repo.index(displayed_werk_ids[-1])
    current_werk_ids_from_repo = werk_ids_from_repo[oldest_displayed_werk_id_index:]
    assert (
        len(current_werk_ids_from_repo) > 0
    ), "Could not detect current werks! Site not in sync with repo?"

    # detect any missing werks
    different_werks = set(current_werk_ids_from_repo).symmetric_difference(set(displayed_werk_ids))
    assert_msg = []
    if different_werks:
        if missing_werks := set(current_werk_ids_from_repo) - set(displayed_werk_ids):
            assert_msg.append(f"Checkmk site does not list following werks: {missing_werks}")
            missing_werks_cnt = len(missing_werks)
            # check if the site is outdated (i.e. missing werks are identical to the latest werks)
            latest_werks = set(current_werk_ids_from_repo[-missing_werks_cnt:])
            if missing_werks == latest_werks:
                assert_msg.append("Latest werks missing! Site not in sync with repo?")
        if unexpected_werks := set(displayed_werk_ids) - set(werk_ids_from_repo):
            assert_msg.append(
                f"Checkmk site lists unexpected werks: {unexpected_werks}\n" "Site ahead of repo?"
            )

    assert len(different_werks) == 0, "\n".join(assert_msg)

    # check that all werk links share the same url format
    for werk in displayed_werks:
        response = werks_page.go(displayed_werks[werk])
        assert response and response.ok, f"Could not navigate to werk {werk}!"
