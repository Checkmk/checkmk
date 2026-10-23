#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from http import HTTPStatus
from urllib.parse import urljoin

import pytest

from tests.testlib.unit.gui.web_test_app import WebTestAppForCMK

_BASE = "/NO_SITE/check_mk/api/1.0/"


@pytest.mark.usefixtures("patch_theme")
def test_agent_controller_certificates_settings_ok(
    logged_in_admin_wsgi_app: WebTestAppForCMK,
) -> None:
    assert set(
        logged_in_admin_wsgi_app.get(
            urljoin(_BASE, "agent_controller_certificates_settings"),
            status=HTTPStatus.OK,
            headers={"Accept": "application/json"},
        ).json_body
    ) == {"lifetime_in_months"}


@pytest.mark.usefixtures("patch_theme")
def test_agent_controller_certificates_settings_unauthorized(
    logged_in_wsgi_app: WebTestAppForCMK,
) -> None:
    assert (
        logged_in_wsgi_app.get(
            urljoin(_BASE, "agent_controller_certificates_settings"),
            status=HTTPStatus.FORBIDDEN,
            headers={"Accept": "application/json"},
        ).json_body["title"]
        == "Unauthorized"
    )
