#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.i18n import _
from cmk.gui.openapi.framework.model._api_field import api_field
from cmk.gui.openapi.framework.model._api_model import api_model

from .._models import Host
from ._urls import host_view_link


@api_model
class ModeInfo:
    icon_name: str = api_field(description="Icon to render for this mode", example="downtime")
    link: str = api_field(
        description="URL the mode icon links to",
        example="view.py?view_name=downtimes_of_host&host=web-server-01",
    )
    title: str = api_field(
        description="Tooltip shown for the mode icon", example="In scheduled downtime"
    )


def build_host_modes(host: Host) -> list[ModeInfo]:
    modes: list[ModeInfo] = []
    if host.in_downtime:
        modes.append(
            ModeInfo(
                icon_name="downtime",
                link=host_view_link("downtimes_of_host", host),
                title=_("In scheduled downtime"),
            )
        )
    if host.acknowledged:
        modes.append(
            ModeInfo(
                icon_name="ack",
                link=host_view_link("host", host),
                title=_("Problem acknowledged"),
            )
        )
    return modes
