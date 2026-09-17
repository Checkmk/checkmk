#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Callable

import pytest
from playwright.sync_api import expect, Locator

from tests.system.gui.settings.settings_files import (
    OMD_SETTINGS_REL_PATH,
    SITE_SPECIFIC_SETTINGS_REL_PATH,
)
from tests.system.gui.testlib.playwright.pom.monitor.dashboard import MainDashboard
from tests.system.gui.testlib.playwright.pom.setup.global_settings import (
    GlobalSettings,
    SiteSpecificSettings,
)
from tests.testlib.site import Site

HUB_SETTING = "Enable piggyback-hub"

EXPECTED_ERROR = (
    "The piggyback-hub cannot be enabled for a remote site if it is disabled for the central site"
)


def _disable_hub_via_editor(settings: GlobalSettings) -> Locator:
    editor = settings.open_editor(HUB_SETTING)
    editor.container.get_by_role("checkbox").uncheck()
    editor.save(expect_success=False)
    return editor.error.filter(has_text=EXPECTED_ERROR)


def _disable_hub_via_toggle(settings: GlobalSettings) -> Locator:
    settings.toggle(HUB_SETTING, expect_success=False)
    return settings.toggle_error(HUB_SETTING).filter(has_text=EXPECTED_ERROR)


def _disable_hub_via_reset(settings: GlobalSettings) -> Locator:
    editor = settings.open_editor(HUB_SETTING)
    editor.reset(expect_success=False)
    return editor.error.filter(has_text=EXPECTED_ERROR)


@pytest.mark.usefixtures("backed_up_settings")
@pytest.mark.parametrize(
    "disable_hub_globally",
    [
        pytest.param(_disable_hub_via_editor, id="save"),
        pytest.param(_disable_hub_via_toggle, id="toggle"),
        pytest.param(_disable_hub_via_reset, id="reset"),
    ],
)
def test_disabling_the_hub_globally_is_rejected_while_a_remote_site_enables_it(
    test_site: Site,
    remote_site_wato_disabled: Site,
    dashboard_page: MainDashboard,
    disable_hub_globally: Callable[[GlobalSettings], Locator],
) -> None:
    test_site.update_global_settings(OMD_SETTINGS_REL_PATH, {"site_piggyback_hub": True})
    test_site.update_site_specific_settings(
        SITE_SPECIFIC_SETTINGS_REL_PATH,
        {remote_site_wato_disabled.id: {"globals": {"site_piggyback_hub": True}}},
    )
    original_settings = test_site.read_global_settings(OMD_SETTINGS_REL_PATH)

    rejection = disable_hub_globally(GlobalSettings(dashboard_page.page))

    expect(rejection, message="The piggyback-hub change was not rejected").to_be_visible()
    assert test_site.read_global_settings(OMD_SETTINGS_REL_PATH) == original_settings, (
        "The piggyback-hub global setting was changed although the change was rejected"
    )


@pytest.mark.usefixtures("backed_up_settings")
def test_enabling_the_hub_for_a_remote_site_is_rejected_while_it_is_globally_disabled(
    test_site: Site,
    remote_site_wato_disabled: Site,
    dashboard_page: MainDashboard,
) -> None:
    test_site.update_global_settings(OMD_SETTINGS_REL_PATH, {"site_piggyback_hub": False})
    test_site.update_site_specific_settings(
        SITE_SPECIFIC_SETTINGS_REL_PATH,
        {remote_site_wato_disabled.id: {"globals": {"site_piggyback_hub": False}}},
    )
    original_settings = test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH)

    settings = SiteSpecificSettings(dashboard_page.page, remote_site_wato_disabled.id)
    editor = settings.open_editor(HUB_SETTING)
    editor.container.get_by_role("checkbox").check()
    editor.save(expect_success=False)

    expect(
        editor.error.filter(has_text=EXPECTED_ERROR),
        message="The piggyback-hub change was not rejected",
    ).to_be_visible()
    assert (
        test_site.read_site_specific_settings(SITE_SPECIFIC_SETTINGS_REL_PATH) == original_settings
    ), (
        f"The piggyback-hub setting of site '{remote_site_wato_disabled.id}' was changed "
        "although the change was rejected"
    )
