#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-def"

from collections.abc import Iterator

import pytest

import cmk.gui.mkeventd.wato as mkeventd
from cmk.automations.results import DeleteHostsResult
from cmk.ccc.hostaddress import HostName
from cmk.gui.script_helpers import session_wsgi_app
from cmk.gui.session import SuperUserContext
from cmk.gui.watolib import groups
from cmk.gui.watolib.groups import HostAttributeContactGroups
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.wsgi.blueprints import checkmk, rest_api
from tests.testlib.gui.web_test_app import WebTestAppForCMK, WebTestAppRequestHandler
from tests.testlib.rest_api_client import RestApiClient


@pytest.fixture()
def api_client(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base_without_version: str
) -> RestApiClient:
    return RestApiClient(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base_without_version)


@pytest.fixture()
def with_groups(monkeypatch, request_context, with_admin_login, suppress_remote_automation_calls):
    groups.add_group("windows", "host", {"alias": "windows"}, pprint_value=False, use_git=False)
    groups.add_group("routers", "service", {"alias": "routers"}, pprint_value=False, use_git=False)
    groups.add_group("admins", "contact", {"alias": "admins"}, pprint_value=False, use_git=False)
    yield
    groups.delete_group("windows", "host", pprint_value=False, use_git=False)
    groups.delete_group("routers", "service", pprint_value=False, use_git=False)
    monkeypatch.setattr(mkeventd, "_get_rule_stats_from_ec", lambda: {})
    groups.delete_group("admins", "contact", pprint_value=False, use_git=False)


@pytest.fixture(name="sample_host")
def fixture_sample_host(request_context: None) -> Iterator[str]:
    host_name = "test_host"
    root_folder = folder_tree().root_folder()
    contact_groups = HostAttributeContactGroups().default_value()
    contact_groups["groups"] = ["all"]
    with SuperUserContext():
        root_folder.create_hosts(
            [(HostName(host_name), HostAttributes(contactgroups=contact_groups), None)],
            pprint_value=False,
            use_git=False,
        )
    try:
        yield host_name
    finally:
        with SuperUserContext():
            root_folder.delete_hosts(
                [HostName(host_name)],
                automation=lambda _automation_config, _hosts, _debug: DeleteHostsResult(),
                pprint_value=False,
                debug=False,
                use_git=False,
            )


@pytest.fixture(name="fresh_app_instance", scope="function")
def clear_caches_flask_app():
    session_wsgi_app.cache_clear()
    rest_api.app_instance.cache_clear()
    checkmk.app_instance.cache_clear()
