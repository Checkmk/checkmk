#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from typing import Any

import cmk.utils.paths
from cmk.utils import store

from cmk.gui.config import active_config, builtin_role_ids
from cmk.gui.i18n import _

RoleSpec = dict[str, Any]  # TODO: Improve this type
Roles = dict[str, RoleSpec]  # TODO: Improve this type


def load_roles() -> Roles:
    roles = store.load_from_mk_file(
        os.path.join(cmk.utils.paths.default_config_dir, "multisite.d/wato/roles.mk"),
        "roles",
        default=_get_builtin_roles(),
    )

    # Make sure that "general." is prefixed to the general permissions
    # (due to a code change that converted "use" into "general.use", etc.
    # TODO: Can't we drop this? This seems to be from very early days of the GUI
    for role in roles.values():
        for pname, pvalue in role["permissions"].items():
            if "." not in pname:
                del role["permissions"][pname]
                role["permissions"]["general." + pname] = pvalue

    # Reflect the data in the roles dict kept in the config module needed
    # for instant changes in current page while saving modified roles.
    # Otherwise the hooks would work with old data when using helper
    # functions from the config module
    # TODO: load_roles() should not update global structures
    active_config.roles.update(roles)

    return roles


def _get_builtin_roles() -> Roles:
    """Returns a role dictionary containing the bultin default roles"""
    builtin_role_names = {
        "admin": _("Administrator"),
        "user": _("Normal monitoring user"),
        "guest": _("Guest user"),
        "agent_registration": _("Agent registration user"),
    }
    return {
        rid: {
            "alias": builtin_role_names.get(rid, rid),
            "permissions": {},  # use default everywhere
            "builtin": True,
        }
        for rid in builtin_role_ids
    }
