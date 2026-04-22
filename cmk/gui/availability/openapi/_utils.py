#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import datetime as dt
from http import HTTPStatus

from livestatus import lqencode, OnlySites

from cmk.ccc.hostaddress import HostName
from cmk.ccc.site import SiteId
from cmk.gui.availability.options import get_default_avoptions
from cmk.gui.availability.type_defs import AVOptions
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.utils import permission_verification as permissions

PERMISSIONS = permissions.AllPerm([permissions.Perm("general.see_availability")])


def build_avoptions(time_range_from: dt.datetime, time_range_until: dt.datetime) -> AVOptions:
    if time_range_from >= time_range_until:
        raise ProblemException(
            title="Invalid time range",
            detail="time_range_from must be before time_range_until.",
            status=HTTPStatus.BAD_REQUEST,
        )
    return get_default_avoptions(
        range_spec=(time_range_from.timestamp(), time_range_until.timestamp())
    )


def build_only_sites(site_id: SiteId | None) -> OnlySites:
    return [site_id] if site_id else None


def build_host_filterheader(host_name: HostName) -> str:
    return f"Filter: host_name = {lqencode(host_name)}\n"


def build_service_filterheader(host_name: HostName, service_name: str) -> str:
    return (
        f"Filter: host_name = {lqencode(host_name)}\n"
        f"Filter: service_description = {lqencode(service_name)}\n"
    )
