#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Mapping
from concurrent.futures.thread import ThreadPoolExecutor
from http import HTTPStatus
from typing import Any, Literal

from livestatus import SiteConfigurations

import cmk.gui.utils.permission_verification as permissions
from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.openapi.framework.model import ApiOmitted
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import VisualTypeName
from cmk.gui.user_async_replication import add_profile_replication_change
from cmk.gui.visuals._store import load_raw_visuals_of_a_user
from cmk.gui.watolib.automations import RemoteAutomationConfig
from cmk.gui.watolib.user_profile import push_user_profiles_to_site_transitional_wrapper
from cmk.gui.watolib.users import get_enabled_remote_sites_for_logged_in_user

from ._model.dashboard import DashboardResponse
from ._model.response_model import DashboardDomainObject

# if a dashboard contains view widgets, these might come up (even for reads)
PERMISSIONS_VIEW_WIDGET = permissions.Optional(
    permissions.AllPerm(
        [
            permissions.Perm("general.edit_views"),  # always required, even for reads
            # optional permissions to allow access to more views the user doesn't own
            permissions.Perm("general.see_user_views"),
            permissions.Perm("general.see_packaged_views"),
            # every view has its own permissions, all of which might be checked (and are optional)
            permissions.PrefixPerm("view"),
        ]
    )
)
PERMISSIONS_DASHBOARD = permissions.AllPerm(
    [
        permissions.Perm("general.edit_dashboards"),  # always required, even for reads
        # these 3 are optional, allowing access to more dashboards the user doesn't own
        permissions.Optional(permissions.Perm("general.force_dashboards")),
        permissions.Optional(permissions.Perm("general.see_user_dashboards")),
        permissions.Optional(permissions.Perm("general.see_packaged_dashboards")),
        # every dashboard has its own permissions, all of which might be checked (and are optional)
        permissions.PrefixPerm("dashboard"),
        # dashboards which contain view widgets need extra permissions to view/modify them
        PERMISSIONS_VIEW_WIDGET,
    ]
)


def get_permitted_user_id(owner: UserId | ApiOmitted, action: Literal["delete", "edit"]) -> UserId:
    """Get the user ID from the owner field, defaulting to the current user.

    Validates that the user has permission to perform the action on foreign dashboards.
    And that the built-in user was not chosen.
    """
    user_id = user.ident
    if isinstance(owner, ApiOmitted) or owner == user_id:
        return user_id

    if owner == UserId.builtin():
        raise ProblemException(
            status=HTTPStatus.FORBIDDEN,
            title="Forbidden",
            detail=f"You are not allowed to {action} dashboards owned by the built-in user.",
        )

    user.need_permission(f"general.{action}_foreign_dashboards")
    return owner


def serialize_dashboard(dashboard_id: str, dashboard: DashboardResponse) -> DashboardDomainObject:
    return DashboardDomainObject(
        domainType="dashboard",
        id=dashboard_id,
        title=dashboard.title.text,
        links=generate_links("dashboard", dashboard_id),
        extensions=dashboard,
    )


def sync_user_to_remotes(sites: SiteConfigurations) -> None:
    """Synchronize the logged-in user profile and their dashboards to all enabled remote sites.

    This does not handle other users or visuals."""
    if (user_id := user.id) is None:
        return

    user_remote_sites = get_enabled_remote_sites_for_logged_in_user(user, sites)
    if not user_remote_sites:
        return

    remote_configs = []
    for site_id, site in user_remote_sites.items():
        if "secret" not in site:
            add_profile_replication_change(site_id, "Not logged in.")
            continue

        remote_configs.append(RemoteAutomationConfig.from_site_config(site))

    if not remote_configs:
        return

    dashboards = load_raw_visuals_of_a_user("dashboards", user_id)
    visuals: Mapping[UserId, Mapping[VisualTypeName, Mapping[str, Any]]] = {
        user_id: {"dashboards": dashboards}
    }

    def push(automation_config: RemoteAutomationConfig) -> None:
        push_user_profiles_to_site_transitional_wrapper(
            automation_config=automation_config,
            user_profiles={user_id: user.attributes},
            visuals=visuals,
            debug=False,
        )

    with ThreadPoolExecutor(max_workers=len(remote_configs)) as executor:
        executor.map(push, remote_configs)
