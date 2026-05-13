#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    Permission,
    PermissionRegistry,
    PermissionSection,
    PermissionSectionRegistry,
)
from cmk.gui.wato._permissions import PERMISSION_SECTION_WATO

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


PermissionBIRules = Permission(
    section=PERMISSION_SECTION_WATO,
    name="bi_rules",
    title=_l("Business Intelligence rules and aggregations"),
    description=_l(
        "Use the Setup BI module, create, modify and delete BI rules and "
        "aggregations in packs that you are a contact of."
    ),
    defaults=["admin", "user"],
)


PermissionBIAdmin = Permission(
    section=PERMISSION_SECTION_WATO,
    name="bi_admin",
    title=_l("Business Intelligence administration"),
    description=_l(
        "Edit all rules and aggregations for Business Intelligence, "
        "create, modify and delete rule packs."
    ),
    defaults=["admin"],
)


def register_permissions(
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_BI)
    permission_registry.register(PermissionBISeeAll)
    permission_registry.register(PermissionBIRules)
    permission_registry.register(PermissionBIAdmin)
