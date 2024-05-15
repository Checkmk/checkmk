#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Sequence

from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.utils.urls import makeuri_contextless

from .store import get_all_dashboards


def find_usages_of_contact_group_in_dashboards(
    name: str, _settings: GlobalSettings
) -> list[tuple[str, str]]:
    used_in: list[tuple[str, str]] = []

    for (dashboard_owner, dashboard_name), board in get_all_dashboards().items():
        public_value: bool | tuple[str, Sequence[str]] = board["public"]
        if isinstance(public_value, tuple) and name in public_value[1]:
            title = "{}: {}".format(_("Dashboard of user %s") % dashboard_owner, dashboard_name)
            used_in.append(
                (
                    title,
                    makeuri_contextless(
                        request,
                        [
                            ("load_name", dashboard_name),
                            ("mode", "edit"),
                            ("owner", dashboard_owner),
                        ],
                        filename="edit_dashboard.py",
                    ),
                )
            )
    return used_in
