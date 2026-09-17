#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Iterator

import pytest

from tests.system.gui.settings.settings_files import (
    GUI_SETTINGS_REL_PATH,
    OMD_SETTINGS_REL_PATH,
    SITE_SPECIFIC_SETTINGS_REL_PATH,
)
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.site import Site, SiteFactory

logger = logging.getLogger(__name__)


@pytest.fixture(name="remote_site_wato_disabled", scope="package")
def fixture_remote_site_wato_disabled(test_site: Site, site_factory: SiteFactory) -> Iterator[Site]:
    """Return one connected remote site with WATO disabled for this package's suites.

    It overrides the function-scoped fixture of the same name from the GUI conftest, which
    builds one site per test case.
    """
    with site_factory.connected_remote_site(
        "remote", test_site, "GUI settings suites"
    ) as remote_site:
        yield remote_site


@pytest.fixture(name="backed_up_settings")
def fixture_backed_up_settings(test_site: Site) -> Iterator[None]:
    setting_files = [
        GUI_SETTINGS_REL_PATH,
        OMD_SETTINGS_REL_PATH,
        SITE_SPECIFIC_SETTINGS_REL_PATH,
    ]
    list_of_files = ", ".join(map(str, setting_files))
    logger.info("Backup settings within: '%s'", list_of_files)
    backed_settings = {
        setting_file: test_site.read_file(setting_file)
        for setting_file in setting_files
        if test_site.file_exists(setting_file)
    }
    try:
        yield
    finally:
        if is_cleanup_enabled():
            logger.info("Restore settings within: '%s'", list_of_files)
            for setting_file in setting_files:
                if setting_file in backed_settings:
                    test_site.write_file(setting_file, backed_settings[setting_file])
                elif test_site.file_exists(setting_file):
                    test_site.delete_file(setting_file)
            logger.info("Activate the restored settings so no pending change is left behind")
            test_site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
