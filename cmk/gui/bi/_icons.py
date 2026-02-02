#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.type_defs import DynamicIcon, IconNames, Row, StaticIcon
from cmk.gui.utils.html import HTML
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.views.icon import Icon, IconConfig, IconRegistry
from cmk.utils.tags import TagID

from ._compiler import is_part_of_aggregation

IconSpec = StaticIcon | DynamicIcon


def register(
    icon_and_action_registry: IconRegistry,
) -> None:
    icon_and_action_registry.register(AggregationsIcon)
    icon_and_action_registry.register(AggregationIcon)


def _render_aggregations_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
    user_permissions: UserPermissions,
    icon_config: IconConfig,
) -> None | IconSpec | HTML | tuple[IconSpec, str] | tuple[IconSpec, str, str]:
    # Link to aggregations of the host/service
    # When precompile on demand is enabled, this icon is displayed for all hosts/services
    # otherwise only for the hosts/services which are part of aggregations.
    if is_part_of_aggregation(row["host_name"], str(row.get("service_description"))):
        view_name = "aggr_%s" % what

        if not user.may("view.%s" % view_name):
            return None

        urivars = [
            ("view_name", view_name),
            ("aggr_%s_site" % what, row["site"]),
            ("aggr_%s_host" % what, row["host_name"]),
        ]
        if what == "service":
            urivars += [("aggr_service_service", row["service_description"])]
        url = makeuri_contextless(request, urivars, filename="view.py")
        return (
            StaticIcon(IconNames.aggr),
            _("BI aggregations containing this %s")
            % (what == "host" and _("Host") or _("Service")),
            url,
        )
    return None


AggregationsIcon = Icon(
    ident="aggregations",
    title=_l("Aggregations"),
    render=_render_aggregations_icon,
)


def _render_aggregation_icon(
    what: Literal["host", "service"],
    row: Row,
    tags: Sequence[TagID],
    custom_vars: Mapping[str, str],
    user_permissions: UserPermissions,
    icon_config: IconConfig,
) -> None | IconSpec | HTML | tuple[IconSpec, str] | tuple[IconSpec, str, str]:
    is_bi_aggr_check = row.get("service_check_command", "").startswith("check_mk-bi_aggregation")

    if what != "service" or not is_bi_aggr_check:
        return None

    return (
        StaticIcon(IconNames.aggr),
        _("Open this Aggregation"),
        makeuri_contextless(
            request,
            [
                ("view_name", "aggr_single"),
                ("aggr_name", row["service_description"].removeprefix("Aggr ")),
            ],
            filename="view.py",
        ),
    )


AggregationIcon = Icon(
    ident="aggregation_checks",
    title=_l("Aggregation checks"),
    host_columns=["check_command", "name", "address"],
    render=_render_aggregation_icon,
)
