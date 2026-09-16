#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""End-to-end coverage of the settings pages, driven through 'Sounds in views'.

Covers the round trip of a global setting toggled on the overview and reset in its editor,
and the round trip of a site-specific override saved and removed on a site's settings page.
"""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import cast

import pytest

from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.setup.global_settings import (
    GlobalSettings,
    SiteSpecificSettings,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.common.utils2 import is_cleanup_enabled
from tests.testlib.site import Site, SiteFactory

logger = logging.getLogger(__name__)


GUI_SETTINGS_REL_PATH = Path("etc/check_mk/multisite.d/wato/global.mk")
SITE_SPECIFIC_SETTINGS_REL_PATH = Path("etc/check_mk/multisite.d/sites.mk")

SOUNDS_SETTING = "Sounds in views"
SOUNDS_VARNAME = "enable_sounds"

STORAGE_TIMEOUT = 10


@pytest.fixture(name="remote_site_wato_disabled", scope="module")
def fixture_remote_site_wato_disabled(test_site: Site, site_factory: SiteFactory) -> Iterator[Site]:
    """Return a second Checkmk site object for a distributed setup, shared across this module.

    WATO is disabled on the remote site (disable_remote_configuration=True).

    This overrides the function-scoped fixture of the same name from the top-level conftest.
    """
    with site_factory.connected_remote_site(
        "remote", test_site, "test_global_settings"
    ) as remote_site:
        yield remote_site


@pytest.fixture(name="backed_up_settings")
def fixture_backed_up_settings(test_site: Site) -> Iterator[None]:
    setting_files = [GUI_SETTINGS_REL_PATH, SITE_SPECIFIC_SETTINGS_REL_PATH]
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


def _global_settings(central_site: Site) -> dict[str, object]:
    if not central_site.file_exists(GUI_SETTINGS_REL_PATH):
        return {}
    return central_site.read_global_settings(GUI_SETTINGS_REL_PATH)


def _site_globals(central_site: Site, site_id: str) -> dict[str, object]:
    if not central_site.file_exists(SITE_SPECIFIC_SETTINGS_REL_PATH):
        return {}
    sites = central_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)["sites"]
    return cast(dict[str, object], sites.get(site_id, {}).get("globals", {}))


def test_setting_toggled_on_the_overview_is_stored_and_reset_in_the_editor(
    test_site: Site,
    dashboard_page: MainDashboard,
    backed_up_settings: None,  # noqa: ARG001
) -> None:
    initial_settings = _global_settings(test_site)
    settings = GlobalSettings(dashboard_page.page)

    settings.toggle(SOUNDS_SETTING)

    wait_until(
        lambda: _global_settings(test_site).get(SOUNDS_VARNAME) is True,
        timeout=STORAGE_TIMEOUT,
        condition_name=f"the toggled setting '{SOUNDS_SETTING}' is stored as enabled",
    )

    settings.open_editor(SOUNDS_SETTING).reset()

    wait_until(
        lambda: _global_settings(test_site) == initial_settings,
        timeout=STORAGE_TIMEOUT,
        condition_name=f"the setting '{SOUNDS_SETTING}' is stored at its factory state again",
    )


def test_site_override_comes_and_goes_alone(
    test_site: Site,
    remote_site_wato_disabled: Site,
    dashboard_page: MainDashboard,
    backed_up_settings: None,  # noqa: ARG001
) -> None:
    initial_settings = _global_settings(test_site)
    initial_site_globals = _site_globals(test_site, remote_site_wato_disabled.id)
    settings = SiteSpecificSettings(dashboard_page.page, remote_site_wato_disabled.id)

    editor = settings.open_editor(SOUNDS_SETTING)
    editor.container.get_by_role("checkbox", name="Sounds", exact=True).check()
    editor.save()

    wait_until(
        lambda: (
            _site_globals(test_site, remote_site_wato_disabled.id)
            == initial_site_globals | {SOUNDS_VARNAME: True}
        ),
        timeout=STORAGE_TIMEOUT,
        condition_name=(
            f"the setting '{SOUNDS_SETTING}' is stored as enabled "
            f"for site '{remote_site_wato_disabled.id}'"
        ),
    )
    assert _global_settings(test_site) == initial_settings, (
        f"Overriding the setting '{SOUNDS_SETTING}' for site "
        f"'{remote_site_wato_disabled.id}' changed the global settings"
    )

    settings.open_editor(SOUNDS_SETTING).reset()

    wait_until(
        lambda: _site_globals(test_site, remote_site_wato_disabled.id) == initial_site_globals,
        timeout=STORAGE_TIMEOUT,
        condition_name=(
            f"the setting '{SOUNDS_SETTING}' is stored without an override "
            f"for site '{remote_site_wato_disabled.id}'"
        ),
    )
    assert _global_settings(test_site) == initial_settings, (
        f"Removing the override of the setting '{SOUNDS_SETTING}' for site "
        f"'{remote_site_wato_disabled.id}' changed the global settings"
    )
