#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.livestatus_client.tables.comments import Comments
from cmk.livestatus_client.tables.downtimes import Downtimes
from cmk.livestatus_client.tables.eventconsoleevents import Eventconsoleevents
from cmk.livestatus_client.tables.hostgroups import Hostgroups
from cmk.livestatus_client.tables.hosts import Hosts
from cmk.livestatus_client.tables.servicegroups import Servicegroups
from cmk.livestatus_client.tables.services import Services
from cmk.livestatus_client.tables.status import Status

REST_API_DOC_TABLES = [
    "Downtimes",
    "Hostgroups",
    "Hosts",
    "Servicegroups",
    "Services",
    "Comments",
    "Eventconsoleevents",
]

__all__ = [
    "Downtimes",
    "Hostgroups",
    "Hosts",
    "Servicegroups",
    "Services",
    "Status",
    "Comments",
    "Eventconsoleevents",
    "REST_API_DOC_TABLES",
]
