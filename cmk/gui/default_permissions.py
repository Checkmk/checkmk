#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.gui.config as config
from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    Permission,
    permission_registry,
    permission_section_registry,
    PermissionSection,
)

#   .----------------------------------------------------------------------.
#   |        ____                     _         _                          |
#   |       |  _ \ ___ _ __ _ __ ___ (_)___ ___l(_) ___  _ __  ___          |
#   |       | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|         |
#   |       |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \         |
#   |       |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   | Declare general permissions for Multisite                            |
#   '----------------------------------------------------------------------'


@permission_section_registry.register
class PermissionSectionGeneral(PermissionSection):
    @property
    def name(self):
        return "general"

    @property
    def title(self):
        return _("General Permissions")

    @property
    def sort_index(self):
        return 10


PermissionGeneralUse = permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="use",
        title=_l("Use the GUI at all"),
        description=_l("Users without this permission are not let in at all"),
        defaults=config.builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="server_side_requests",
        title=_l("Perform requests from the Checkmk server"),
        description=_l(
            "Users with this permission can use GUI features that initiate network connections "
            "from the Checkmk server to other hosts on the intra/internet. Although this feature "
            "makes it e.g. easier to fetch CAs from servers it may be used to scan the internal "
            "network for open ports and running services."
        ),
        defaults=["admin"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="see_all",
        title=_l("See all host and services"),
        description=_l(
            "See all objects regardless of contacts and contact groups. "
            "If combined with 'perform commands' then commands may be done on all objects."
        ),
        defaults=["admin", "guest"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="view_option_columns",
        title=_l("Change view display columns"),
        description=_l(
            "Interactively change the number of columns being displayed by a view (does not edit or customize the view)"
        ),
        defaults=config.builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="view_option_refresh",
        title=_l("Change view display refresh"),
        description=_l(
            "Interactively change the automatic browser reload of a view being displayed (does not edit or customize the view)"
        ),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="painter_options",
        title=_l("Change column display options"),
        description=_l(
            "Some of the display columns offer options for customizing their output. "
            "For example time stamp columns can be displayed absolute, relative or "
            "in a mixed style. This permission allows the user to modify display options"
        ),
        defaults=config.builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="act",
        title=_l("Perform commands in views"),
        description=_l(
            "Allows users to perform commands on hosts and services in the views. If "
            "no further permissions are granted, actions can only be done on objects one is a contact for"
        ),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="see_sidebar",
        title=_l("Use Checkmk sidebar"),
        description=_l("Without this permission the Checkmk sidebar will be invisible"),
        defaults=config.builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="configure_sidebar",
        title=_l("Configure sidebar"),
        description=_l("This allows the user to add, move and remove sidebar snapins."),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="edit_profile",
        title=_l("Edit the user profile"),
        description=_l("Permits the user to change the user profile settings."),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="see_availability",
        title=_l("See the availability"),
        description=_l("See the availability views of hosts and services"),
        defaults=config.builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="csv_export",
        title=_l("Use CSV export"),
        description=_l("Export data of views using the CSV export"),
        defaults=config.builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="edit_notifications",
        title=_l("Edit personal notification settings"),
        description=_l(
            "This allows a user to edit his personal notification settings. You also need the permission "
            "<i>Edit the user profile</i> in order to do this."
        ),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="disable_notifications",
        title=_l("Disable all personal notifications"),
        description=_l(
            "This permissions provides a checkbox and timerange in the personal settings of the user that "
            "allows him to completely disable all of his notifications. Use with caution."
        ),
        defaults=["admin"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="edit_user_attributes",
        title=_l("Edit personal user attributes"),
        description=_l(
            "This allows a user to edit his personal user attributes. You also need the permission "
            "<i>Edit the user profile</i> in order to do this."
        ),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="change_password",
        title=_l("Edit the user password"),
        description=_l("Permits the user to change the password."),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="manage_2fa",
        title=_l("Edit the user two-factor authentication"),
        description=_l(
            "Permits the user to edit two-factor authentication (Webauthn credentials)."
        ),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="logout",
        title=_l("Logout"),
        description=_l("Permits the user to logout."),
        defaults=config.builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="ignore_soft_limit",
        title=_l("Ignore soft query limit"),
        description=_l(
            "Allows to ignore the soft query limit imposed upon the number of datasets returned by a query"
        ),
        defaults=["admin", "user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="ignore_hard_limit",
        title=_l("Ignore hard query limit"),
        description=_l(
            "Allows to ignore the hard query limit imposed upon the number of datasets returned by a query"
        ),
        defaults=["admin"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="acknowledge_werks",
        title=_l("Acknowledge Incompatible Werks"),
        description=_l(
            "In the change log of the Checkmk software version the administrator can manage change log entries "
            "(Werks) that requrire user interaction. These <i>incompatible Werks</i> can be acknowledged only "
            "if the user has this permission."
        ),
        defaults=["admin"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="see_failed_notifications_24h",
        title=_l("See failed Notifications (last 24 hours)"),
        description=_l(
            "If Checkmk is unable to notify users about problems, the site will warn about this situation "
            "very visibly inside the UI (both in the Tactical Overview and the Dashboard). This affects only "
            "users with this permission. Users with this permission will only see failed notifications "
            "that occured within the last 24 hours."
        ),
        defaults=["user"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="see_failed_notifications",
        title=_l("See failed Notifications (all)"),
        description=_l(
            "If Checkmk is unable to notify users about problems, the site will warn about this situation "
            "very visibly inside the UI (both in the Tactical Overview and the Dashboard). This affects only "
            "users with this permission. Users with this permission will see failed notifications between now "
            'and the configured <a href="wato.py?mode=edit_configvar&varname=failed_notification_horizon">Failed notification horizon</a>.'
        ),
        defaults=["admin"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="see_stales_in_tactical_overview",
        title=_l("See stale objects in tactical overview"),
        description=_l(
            "Show the column for stale host and service checks in the tactical overview snapin."
        ),
        defaults=config.builtin_role_ids,
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="see_crash_reports",
        title=_l("See crash reports"),
        description=_l(
            "In case an exception happens while Checkmk is running it may produce crash reports that you can "
            "use to track down the issues in the code or send it as report to the Checkmk team to fix this issue "
            "Only users with this permission are able to see the reports in the GUI."
        ),
        defaults=["admin"],
    )
)

permission_registry.register(
    Permission(
        section=PermissionSectionGeneral,
        name="parent_child_topology",
        title=_l("Network Topology"),
        description=_l(
            "This dashboard uses the parent relationships of your hosts to "
            "display a hierarchical map."
        ),
        defaults=config.builtin_role_ids,
    )
)
