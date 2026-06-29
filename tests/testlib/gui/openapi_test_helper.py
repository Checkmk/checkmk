#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from __future__ import annotations

from collections.abc import Iterator

import pytest

from livestatus import SiteConfigurations

import cmk.gui.mkeventd.wato as mkeventd
from cmk.automations.results import DeleteHostsResult
from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.logged_in import user
from cmk.gui.script_helpers import session_wsgi_app
from cmk.gui.session_context import SuperUserContext
from cmk.gui.watolib import groups
from cmk.gui.watolib.groups import HostAttributeContactGroups
from cmk.gui.watolib.host_attributes import HostAttributes
from cmk.gui.watolib.hosts_and_folders import folder_tree
from cmk.gui.watolib.pending_changes import PendingChanges, PendingChangesStore
from cmk.gui.wsgi.blueprints import checkmk, rest_api
from tests.testlib.rest_api_client import RestApiClient

from .web_test_app import WebTestAppForCMK, WebTestAppRequestHandler


def create_api_client(
    aut_user_auth_wsgi_app: WebTestAppForCMK, base_without_version: str
) -> RestApiClient:
    return RestApiClient(WebTestAppRequestHandler(aut_user_auth_wsgi_app), base_without_version)


def create_test_groups(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    pending_changes = _pending_changes()
    groups.add_group(
        "windows",
        "host",
        {"alias": "windows"},
        pprint_value=False,
        pending_changes=pending_changes,
    )
    groups.add_group(
        "routers",
        "service",
        {"alias": "routers"},
        pprint_value=False,
        pending_changes=pending_changes,
    )
    groups.add_group(
        "admins",
        "contact",
        {"alias": "admins"},
        pprint_value=False,
        pending_changes=pending_changes,
    )
    yield
    groups.delete_group("windows", "host", pprint_value=False, pending_changes=pending_changes)
    groups.delete_group("routers", "service", pprint_value=False, pending_changes=pending_changes)
    monkeypatch.setattr(mkeventd, "_get_rule_stats_from_ec", dict)
    groups.delete_group("admins", "contact", pprint_value=False, pending_changes=pending_changes)


def create_sample_host_context() -> Iterator[str]:
    host_name = "test_host"
    root_folder = folder_tree().root_folder()
    contact_groups = HostAttributeContactGroups().default_value()
    contact_groups["groups"] = ["all"]
    with SuperUserContext():
        root_folder.create_hosts(
            [(HostName(host_name), HostAttributes(contactgroups=contact_groups), None)],
            pprint_value=False,
            pending_changes=_pending_changes(),
            acting_user=user,
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
                pending_changes=_pending_changes(),
            )


def clear_app_instance_caches() -> None:
    session_wsgi_app.cache_clear()
    rest_api.app_instance.cache_clear()
    checkmk.app_instance.cache_clear()


def _pending_changes() -> PendingChanges:
    return PendingChanges(
        activation_sites=SiteConfigurations({}),
        local_site=SiteId("test"),
        acting_user=None,
        store=PendingChangesStore(),
        hooks=(),
    )
