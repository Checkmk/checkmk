#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""End-to-end coverage of the settings pages, driven through 'Sounds in views'.

Covers the round trip of a global setting toggled on the overview and reset in its editor,
and the round trip of a site-specific override saved and removed on a site's settings page.
"""

from typing import cast

import pytest

from tests.system.gui.settings.settings_files import (
    GUI_SETTINGS_REL_PATH,
    SITE_SPECIFIC_SETTINGS_REL_PATH,
)
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.setup.global_settings import (
    GlobalSettings,
    SiteSpecificSettings,
)
from tests.testlib.common.utils import wait_until
from tests.testlib.site import Site

SOUNDS_SETTING = "Sounds in views"
SOUNDS_VARNAME = "enable_sounds"

STORAGE_TIMEOUT = 10


def _global_settings(central_site: Site) -> dict[str, object]:
    if not central_site.file_exists(GUI_SETTINGS_REL_PATH):
        return {}
    return central_site.read_global_settings(GUI_SETTINGS_REL_PATH)


def _site_globals(central_site: Site, site_id: str) -> dict[str, object]:
    if not central_site.file_exists(SITE_SPECIFIC_SETTINGS_REL_PATH):
        return {}
    sites = central_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)["sites"]
    return cast(dict[str, object], sites.get(site_id, {}).get("globals", {}))


@pytest.mark.usefixtures("backed_up_settings")
def test_setting_toggled_on_the_overview_is_stored_and_reset_in_the_editor(
    test_site: Site,
    dashboard_page: MainDashboard,
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


@pytest.mark.usefixtures("backed_up_settings")
def test_site_override_comes_and_goes_alone(
    test_site: Site,
    remote_site_wato_disabled: Site,
    dashboard_page: MainDashboard,
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
