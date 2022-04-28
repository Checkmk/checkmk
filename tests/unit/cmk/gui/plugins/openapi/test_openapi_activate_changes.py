#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from tests.unit.cmk.gui.conftest import WebTestAppForCMK

from cmk.utils.livestatus_helpers.testing import MockLiveStatusConnection

from cmk.automations.results import DeleteHostsResult

from cmk.gui.plugins.openapi.restful_objects import constructors

CMK_WAIT_FOR_COMPLETION = "cmk/wait-for-completion"


def test_openapi_show_activations(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"
    aut_user_auth_wsgi_app.call_method(
        "get",
        base + "/objects/activation_run/asdf/actions/wait-for-completion/invoke",
        status=404,
        headers={"Accept": "application/json"},
    )


def test_openapi_list_currently_running_activations(aut_user_auth_wsgi_app: WebTestAppForCMK):
    base = "/NO_SITE/check_mk/api/1.0"
    aut_user_auth_wsgi_app.call_method(
        "get",
        base + constructors.collection_href("activation_run", "running"),
        status=200,
        headers={"Accept": "application/json"},
    )


def test_openapi_activate_changes(
    monkeypatch: pytest.MonkeyPatch,
    aut_user_auth_wsgi_app: WebTestAppForCMK,
    mock_livestatus: MockLiveStatusConnection,
):
    base = "/NO_SITE/check_mk/api/1.0"

    # We create a host
    live = mock_livestatus

    host_created = aut_user_auth_wsgi_app.call_method(
        "post",
        base + "/domain-types/host_config/collections/all",
        params='{"host_name": "foobar", "folder": "/"}',
        headers={"Accept": "application/json"},
        status=200,
        content_type="application/json",
    )

    with live(expect_status_query=True):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=400,
            params='{"sites": ["asdf"]}',
            headers={"Accept": "application/json"},
            content_type="application/json",
        )
        assert "Unknown site" in repr(resp.json), resp.json

        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=200,
            headers={"Accept": "application/json"},
            content_type="application/json",
        )

    with live(expect_status_query=True):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            status=302,
            params='{"redirect": true}',
            headers={"Accept": "application/json"},
            content_type="application/json",
        )

    for _ in range(10):
        resp = aut_user_auth_wsgi_app.follow_link(
            resp,
            CMK_WAIT_FOR_COMPLETION,
        )
        if resp.status_code == 204:
            break

    # We delete the host again
    monkeypatch.setattr(
        "cmk.gui.plugins.openapi.endpoints.host_config.delete_hosts",
        lambda *args, **kwargs: DeleteHostsResult(),
    )
    aut_user_auth_wsgi_app.follow_link(
        host_created,
        ".../delete",
        status=204,
        headers={"If-Match": host_created.headers["ETag"], "Accept": "application/json"},
        content_type="application/json",
    )

    # And activate the changes

    with live(expect_status_query=True):
        resp = aut_user_auth_wsgi_app.call_method(
            "post",
            base + "/domain-types/activation_run/actions/activate-changes/invoke",
            headers={"Accept": "application/json"},
            content_type="application/json",
        )

    for _ in range(10):
        resp = aut_user_auth_wsgi_app.follow_link(
            resp,
            CMK_WAIT_FOR_COMPLETION,
            headers={"Accept": "application/json"},
        )
        if resp.status_code == 204:
            break
