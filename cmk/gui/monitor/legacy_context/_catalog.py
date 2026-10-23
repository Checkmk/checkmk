#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The legacy filters a monitoring page can take over, by the name the legacy visuals know them
by. A legacy filter a page needs is added here once, then mapped to a field by each page."""

from collections.abc import Mapping

from cmk.gui.type_defs import FilterName

from ._filters import (
    address,
    exact_text,
    flag,
    LegacyFilter,
    name_list,
    number_range,
    site,
    site_ids,
    SiteIds,
    state_choice,
    text,
)

# Like the legacy views, only the first of the site filters that restricts the sites applies; the
# others are reported as not applied, unless they name every site the first one does.
SITE_FILTERS: Mapping[FilterName, SiteIds] = {
    "sites": site_ids("sites", separator="|"),
    "site": site_ids("site"),
    "siteopt": site_ids("site"),
}

LEGACY_FILTERS: Mapping[FilterName, LegacyFilter] = {
    **{name: site(ids) for name, ids in SITE_FILTERS.items()},
    "host": exact_text("host"),
    "hostregex": text("host_regex"),
    "hostalias": text("hostalias"),
    "host_address": address("host_address"),
    "opthostgroup": name_list("opthost_group"),
    "host_ctc": name_list("host_ctc", separator=None),
    "host_ctc_regex": text("host_ctc_regex", negatable=False),
    "opthost_contactgroup": name_list("opthost_contact_group"),
    "hoststate": state_choice(
        {"hst0": "UP", "hst1": "DOWN", "hst2": "UNREACHABLE", "hstp": "PENDING"}
    ),
    "host_staleness": flag("is_host_staleness"),
    "host_acknowledged": flag("is_host_acknowledged"),
    "host_notifications_enabled": flag("is_host_notifications_enabled"),
    "host_in_notification_period": flag("is_host_in_notification_period"),
    "host_in_service_period": flag("is_host_in_service_period"),
    "host_scheduled_downtime_depth": flag("is_host_scheduled_downtime_depth"),
    "host_num_services": number_range("host_num_services"),
}
