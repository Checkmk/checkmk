#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-any-return"
# mypy: disable-error-code="no-untyped-def"

import time
from typing import Any

import cmk.ccc.version as cmk_version
from cmk.ccc.exceptions import MKGeneralException
from cmk.ccc.user import UserId
from cmk.gui import visuals
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.hooks import request_memoize
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.permissions import permission_registry
from cmk.gui.type_defs import ColumnSpec, DashboardEmbeddedViewSpec, SorterSpec
from cmk.gui.user_async_replication import user_profile_async_replication_page
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.views.store import internal_view_to_runtime_view
from cmk.utils import paths

from .builtin_dashboards import (
    builtin_dashboard_extender_registry,
    builtin_dashboards,
)
from .type_defs import DashboardConfig, DashboardName, DashletConfig, DashletId


# TODO: Same as in cmk.gui.plugins.views.utils.ViewStore and ReportStore, centralize implementation?
class DashboardStore:
    @classmethod
    @request_memoize()
    def get_instance(cls):
        """Load dashboards only once for each request"""
        return cls()

    def __init__(self) -> None:
        user_permissions = UserPermissions.from_config(active_config, permission_registry)
        self.all = self._load_all()
        self.permitted = self._load_permitted(self.all, user_permissions)
        self.permitted_by_owner = self._load_permitted_by_owner(self.all, user_permissions)

    def _load_all(self) -> dict[tuple[UserId, DashboardName], DashboardConfig]:
        """Loads all definitions from disk and returns them"""
        return visuals.load(
            "dashboards",
            builtin_dashboard_extender_registry[cmk_version.edition(paths.omd_root).short].callable(
                builtin_dashboards, active_config
            ),
            _internal_dashboard_to_runtime_dashboard,
        )

    def _load_permitted(
        self,
        all_dashboards: dict[tuple[UserId, DashboardName], DashboardConfig],
        user_permissions: UserPermissions,
    ) -> dict[DashboardName, DashboardConfig]:
        """Returns all definitions that a user is allowed to use"""
        return visuals.available("dashboards", all_dashboards, user_permissions)

    def _load_permitted_by_owner(
        self,
        all_dashboards: dict[tuple[UserId, DashboardName], DashboardConfig],
        user_permissions: UserPermissions,
    ) -> dict[DashboardName, dict[UserId, DashboardConfig]]:
        """Returns all definitions that a user is allowed to use"""
        return visuals.available_by_owner("dashboards", all_dashboards, user_permissions)


def _internal_dashboard_to_runtime_dashboard(raw_dashboard: dict[str, Any]) -> DashboardConfig:
    raw_dashboard["packaged"] = False
    raw_dashboard.setdefault("main_menu_search_terms", [])
    return {
        # Need to assume that we are right for now. We will have to introduce parsing there to do a
        # real conversion in one of the following typing steps
        **raw_dashboard,  # type: ignore[typeddict-item]
        "dashlets": [
            (
                internal_view_to_runtime_view(dashlet_spec)
                if dashlet_spec["type"] == "view"
                else dashlet_spec
            )
            for dashlet_spec in raw_dashboard["dashlets"]
        ],
        "embedded_views": {
            embedded_id: _internal_embedded_view_to_runtime_embedded_view(embedded_view)
            for embedded_id, embedded_view in raw_dashboard.get("embedded_views", {}).items()
        },
    }


def _internal_embedded_view_to_runtime_embedded_view(
    raw_embedded_view: dict[str, Any],
) -> DashboardEmbeddedViewSpec:
    spec = DashboardEmbeddedViewSpec(**raw_embedded_view)  # type: ignore[typeddict-item]
    spec["painters"] = [ColumnSpec.from_raw(x) for x in raw_embedded_view.get("painters", [])]
    spec["group_painters"] = [
        ColumnSpec.from_raw(x) for x in raw_embedded_view.get("group_painters", [])
    ]
    spec["sorters"] = [SorterSpec(*x) for x in raw_embedded_view.get("sorters", [])]
    return spec


def save_all_dashboards(owner: UserId | None = None) -> None:
    visuals.save("dashboards", get_all_dashboards(), owner)


def save_and_replicate_all_dashboards(
    owner: UserId | None = None, back: str = "edit_dashboards.py"
) -> None:
    save_all_dashboards(owner)
    user_profile_async_replication_page(back_url=request.get_url_input("back", back))


def get_all_dashboards() -> dict[tuple[UserId, DashboardName], DashboardConfig]:
    return DashboardStore.get_instance().all


def get_permitted_dashboards() -> dict[DashboardName, DashboardConfig]:
    return DashboardStore.get_instance().permitted


def get_permitted_dashboards_by_owners() -> dict[DashboardName, dict[UserId, DashboardConfig]]:
    return DashboardStore.get_instance().permitted_by_owner


def load_dashboard(
    permitted_dashboards: dict[DashboardName, DashboardConfig],
    name: DashboardName,
) -> DashboardConfig:
    return visuals.get_permissioned_visual(
        name,
        request.get_validated_type_input(UserId, "owner"),
        "dashboard",
        permitted_dashboards,
        get_all_dashboards(),
    )


def get_dashlet(board: DashboardName, ident: DashletId) -> DashletConfig:
    try:
        dashboard = get_permitted_dashboards()[board]
    except KeyError:
        raise MKUserError("name", _("The requested dashboard does not exist."))

    try:
        return dashboard["dashlets"][ident]
    except IndexError:
        raise MKGeneralException(_("The dashboard element does not exist."))


def add_dashlet(dashlet_spec: DashletConfig, dashboard: DashboardConfig) -> None:
    dashboard["dashlets"].append(dashlet_spec)
    dashboard["mtime"] = int(time.time())
    save_and_replicate_all_dashboards(dashboard["owner"])
