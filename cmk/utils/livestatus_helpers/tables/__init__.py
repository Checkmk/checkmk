#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.livestatus_helpers.tables.comments import Comments
from cmk.utils.livestatus_helpers.tables.downtimes import Downtimes
from cmk.utils.livestatus_helpers.tables.eventconsoleevents import Eventconsoleevents
from cmk.utils.livestatus_helpers.tables.hostgroups import Hostgroups
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.livestatus_helpers.tables.servicegroups import Servicegroups
from cmk.utils.livestatus_helpers.tables.services import Services
from cmk.utils.livestatus_helpers.tables.status import Status

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
