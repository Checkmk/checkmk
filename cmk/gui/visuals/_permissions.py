#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.config import default_authorized_builtin_role_ids
from cmk.gui.i18n import _
from cmk.gui.permissions import declare_permission
from cmk.gui.type_defs import VisualTypeName


# TODO: This has been obsoleted by pagetypes.py
def declare_visual_permissions(what: VisualTypeName, what_plural: str) -> None:
    declare_permission(
        "general.edit_" + what,
        _("Customize %s and use them") % what_plural,
        _("Allows to create own %s, customize built-in %s and use them.")
        % (what_plural, what_plural),
        ["admin", "user"],
    )

    declare_permission(
        "general.publish_" + what,
        _("Publish %s") % what_plural,
        _("Make %s visible and usable for all users.") % what_plural,
        ["admin", "user"],
    )

    declare_permission(
        "general.publish_" + what + "_to_groups",
        _("Publish %s to allowed contact groups") % what_plural,
        _(
            "Make %s visible and usable for users of contact groups the publishing user is a member of."
        )
        % what_plural,
        ["admin", "user"],
    )

    declare_permission(
        "general.publish_" + what + "_to_foreign_groups",
        _("Publish %s to foreign contact groups") % what_plural,
        _(
            "Make %s visible and usable for users of contact groups the publishing user is not a member of."
        )
        % what_plural,
        ["admin"],
    )

    declare_permission(
        "general.publish_" + what + "_to_sites",
        ("Publish %s to users of selected sites") % what_plural,
        _("Make %s visible and usable for users of sites the publishing user has selected.")
        % what_plural,
        ["admin"],
    )

    declare_permission(
        "general.see_user_" + what,
        _("See user %s") % what_plural,
        _("Is needed for seeing %s that other users have created.") % what_plural,
        default_authorized_builtin_role_ids,
    )

    declare_permission(
        "general.see_packaged_" + what,
        _("See packaged %s") % what_plural,
        _("Is needed for seeing %s that are provided via extension packages.") % what_plural,
        default_authorized_builtin_role_ids,
    )

    declare_permission(
        "general.force_" + what,
        _("Modify built-in %s") % what_plural,
        _("Make own published %s override built-in %s for all users.") % (what_plural, what_plural),
        ["admin"],
    )

    declare_permission(
        "general.edit_foreign_" + what,
        _("Edit foreign %s") % what_plural,
        _("Allows to edit %s created by other users.") % what_plural,
        ["admin"],
    )

    declare_permission(
        "general.delete_foreign_" + what,
        _("Delete foreign %s") % what_plural,
        _("Allows to delete %s created by other users.") % what_plural,
        ["admin"],
    )
