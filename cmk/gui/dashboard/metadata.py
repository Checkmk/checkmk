#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass
from typing import Literal

from cmk.ccc.user import UserId
from cmk.gui.logged_in import user
from cmk.gui.type_defs import AnnotatedUserId
from cmk.gui.utils.roles import UserPermissions

from .breadcrumb import dashboard_topic_breadcrumb
from .type_defs import DashboardConfig

type DashboardLayoutType = Literal["relative_grid", "responsive_grid"]


@dataclass
class BreadcrumbItem:
    title: str
    link: str | None


@dataclass
class Topic:
    name: str
    breadcrumb: list[BreadcrumbItem]


@dataclass
class DashboardDisplay:
    title: str
    topic: Topic
    hidden: bool
    sort_index: int


@dataclass
class DashboardMetadataObject:
    """In sync with API DashboardMetadata"""

    name: str
    owner: AnnotatedUserId | None
    is_built_in: bool
    is_editable: bool
    layout_type: DashboardLayoutType
    display: DashboardDisplay

    @classmethod
    def from_dashboard_config(
        cls, dashboard: DashboardConfig, user_permissions: UserPermissions
    ) -> "DashboardMetadataObject":
        layout_type: DashboardLayoutType = (
            "relative_grid" if dashboard_uses_relative_grid(dashboard) else "responsive_grid"
        )
        is_built_in = dashboard["owner"] == UserId.builtin()
        # Note: from legacy build page header code it seems that permission edit_foreign_dashboards
        # are not taken into account to determine if the user is allowed to edit a dashboard.
        # This could be changed in the future.
        is_editable = (
            not is_built_in
            and user.may("general.edit_dashboards")
            and dashboard["owner"] == user.id
        )
        return cls(
            name=dashboard["name"],
            owner=dashboard["owner"] if dashboard["owner"] != UserId.builtin() else None,
            is_built_in=is_built_in,
            is_editable=is_editable,
            layout_type=layout_type,
            display=DashboardDisplay(
                title=str(dashboard["title"]),
                topic=Topic(
                    name=dashboard["topic"],
                    # LazyString to str conversion to avoid issues
                    breadcrumb=[
                        BreadcrumbItem(title=str(item.title), link=item.url)
                        for item in dashboard_topic_breadcrumb(dashboard["topic"], user_permissions)
                    ],
                ),
                hidden=dashboard["hidden"],
                sort_index=dashboard["sort_index"],
            ),
        )


def dashboard_uses_relative_grid(dashboard: DashboardConfig) -> bool:
    """Check if the given dashboard configuration uses the relative grid layout."""
    return "layout" not in dashboard or dashboard["layout"].get("type") == "relative_grid"
