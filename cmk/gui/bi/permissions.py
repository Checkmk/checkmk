#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _, _l
from cmk.gui.permissions import Permission, PermissionSection

PERMISSION_SECTION_BI = PermissionSection(
    name="bi",
    title=_("BI - Checkmk Business Intelligence"),
)


PermissionBISeeAll = Permission(
    section=PERMISSION_SECTION_BI,
    name="see_all",
    title=_l("See all hosts and services"),
    description=_l(
        "With this permission set, the BI aggregation rules are applied to all "
        "hosts and services - not only those the user is a contact for. If you "
        "remove this permissions then the user will see incomplete aggregation "
        "trees with status based only on those items."
    ),
    defaults=["admin", "guest"],
)
