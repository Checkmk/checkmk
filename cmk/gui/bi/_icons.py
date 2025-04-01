#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import shlex
from collections.abc import Mapping, Sequence
from typing import Literal

from cmk.utils.tags import TagID

from cmk.gui.http import request
from cmk.gui.i18n import _, _l
from cmk.gui.logged_in import user
from cmk.gui.type_defs import Icon as IconSpec
from cmk.gui.type_defs import Row
from cmk.gui.utils.html import HTML
from cmk.gui.utils.urls import makeuri_contextless, urlencode
from cmk.gui.views.icon import Icon, IconRegistry

from ._compiler import is_part_of_aggregation


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
            "aggr",
            _("BI Aggregations containing this %s")
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
) -> None | IconSpec | HTML | tuple[IconSpec, str] | tuple[IconSpec, str, str]:
    # service_check_command looks like:
    # u"check_mk_active-bi_aggr!... '-b' 'http://localhost/$HOSTNAME$' ... '-a' 'Host foobar' ..."
    if what == "service" and row.get("service_check_command", "").startswith(
        "check_mk_active-bi_aggr!"
    ):
        command = row["service_check_command"]
        args = shlex.split(command)
        base_url = args[1]
        base_url = base_url.replace("$HOSTADDRESS$", row["host_address"])
        base_url = base_url.replace("$HOSTNAME$", row["host_name"])

        aggr_name = args[3]
        aggr_name = aggr_name.replace("$HOSTADDRESS$", row["host_address"])
        aggr_name = aggr_name.replace("$HOSTNAME$", row["host_name"])

        url = f"{base_url}/check_mk/view.py?view_name=aggr_single&aggr_name={urlencode(aggr_name)}"

        return "aggr", _("Open this Aggregation"), url
    return None


AggregationIcon = Icon(
    ident="aggregation_checks",
    title=_l("Aggregation checks"),
    host_columns=["check_command", "name", "address"],
    render=_render_aggregation_icon,
)
