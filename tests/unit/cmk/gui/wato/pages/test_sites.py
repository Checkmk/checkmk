#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from livestatus import SiteConfigurations

from cmk.ccc.site import SiteId
from cmk.gui.wato.pages.sites import StatusHostFormSpecAdapter
from cmk.gui.watolib.config_domains import ConfigDomainGUI
from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

ADAPTER = StatusHostFormSpecAdapter(SiteConfigurations({}))


@pytest.mark.parametrize(
    "model",
    [
        None,
        (SiteId("central"), "myhost"),
    ],
)
def test_status_host_round_trip(model: tuple[SiteId, str] | None) -> None:
    assert ADAPTER.from_form_spec(ADAPTER.to_form_spec(model)) == model


def test_status_host_to_form_spec() -> None:
    assert ADAPTER.to_form_spec(None) == ("disabled", None)
    assert ADAPTER.to_form_spec((SiteId("central"), "myhost")) == (
        "enabled",
        (SiteId("central"), "myhost"),
    )


def test_status_host_from_form_spec_accepts_list_payload() -> None:
    # Parsed frontend data may carry the inner pair as a list
    assert ADAPTER.from_form_spec(("enabled", ["central", "myhost"])) == (
        SiteId("central"),
        "myhost",
    )


def test_status_host_from_form_spec_rejects_unknown_shape() -> None:
    with pytest.raises(ValueError):
        ADAPTER.from_form_spec(("central", "myhost"))


@pytest.mark.usefixtures("patch_omd_site", "remote_site", "patch_theme")
def test_the_sites_list_counts_the_registered_variables_pushed_to_a_remote_site(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
) -> None:
    ConfigDomainGUI().save_site_globals({"start_url": "dashboard.py", "wato_enabled": True})

    response = logged_in_admin_wsgi_app.get("/NO_SITE/check_mk/wato.py?mode=sites", status=200)

    assert "1 specific settings" in response.text
