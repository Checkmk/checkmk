#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui import config
from cmk.gui.i18n import _, _l
from cmk.gui.permissions import (
    Permission,
    PermissionRegistry,
    PermissionSection,
    PermissionSectionRegistry,
)


def register(
    permission_section_registry: PermissionSectionRegistry, permission_registry: PermissionRegistry
) -> None:
    permission_section_registry.register(PERMISSION_SECTION_GENERAL)
    permission_registry.register(PermissionGeneralUse)
    permission_registry.register(PermissionServerSideRequests)
    permission_registry.register(PermissionSeeAll)
    permission_registry.register(PermissionViewOptionColumns)
    permission_registry.register(PermissionViewOptionRefresh)
    permission_registry.register(PermissionPainterOptions)
    permission_registry.register(PermissionAct)
    permission_registry.register(PermissionSeeSidebar)
    permission_registry.register(PermissionConfigureSidebar)
    permission_registry.register(PermissionEditProfile)
    permission_registry.register(PermissionSeeAvailability)
    permission_registry.register(PermissionCsvExport)
    permission_registry.register(PermissionEditNotifications)
    permission_registry.register(PermissionDisableNotifications)
    permission_registry.register(PermissionEditUserAttributes)
    permission_registry.register(PermissionChangePassword)
    permission_registry.register(PermissionManage2Fa)
    permission_registry.register(PermissionLogout)
    permission_registry.register(PermissionIgnoreSoftLimit)
    permission_registry.register(PermissionIgnoreHardLimit)
    permission_registry.register(PermissionAcknowledgeWerks)
    permission_registry.register(PermissionSeeFailedNotifications24H)
    permission_registry.register(PermissionSeeFailedNotifications)
    permission_registry.register(PermissionSeeStalesInTacticalOverview)
    permission_registry.register(PermissionSeeCrashReports)
    permission_registry.register(PermissionParentChildTopology)


PERMISSION_SECTION_GENERAL = PermissionSection(
    name="general",
    title=_("General"),
    sort_index=10,
)

PermissionGeneralUse = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="use",
    title=_l("Use the GUI at all"),
    description=_l("Users without this permission are not let in at all"),
    defaults=config.default_authorized_builtin_role_ids,
)

PermissionServerSideRequests = Permission(
    section=PERMISSION_SECTION_GENERAL,
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

PermissionSeeAll = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="see_all",
    title=_l("See all host and services"),
    description=_l(
        "See all objects regardless of contacts and contact groups. "
        "If combined with 'perform commands' then commands may be done on all objects."
    ),
    defaults=["admin", "guest"],
)

PermissionViewOptionColumns = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="view_option_columns",
    title=_l("Change view display columns"),
    description=_l(
        "Interactively change the number of columns being displayed by a view (does not edit or customize the view)"
    ),
    defaults=config.default_authorized_builtin_role_ids,
)

PermissionViewOptionRefresh = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="view_option_refresh",
    title=_l("Change view display refresh"),
    description=_l(
        "Interactively change the automatic browser reload of a view being displayed (does not edit or customize the view)"
    ),
    defaults=["admin", "user"],
)

PermissionPainterOptions = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="painter_options",
    title=_l("Change column display options"),
    description=_l(
        "Some of the display columns offer options for customizing their output. "
        "For example time stamp columns can be displayed absolute, relative or "
        "in a mixed style. This permission allows the user to modify display options"
    ),
    defaults=config.default_authorized_builtin_role_ids,
)

PermissionAct = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="act",
    title=_l("Perform commands in views"),
    description=_l(
        "Allows users to perform commands on hosts and services in the views. If "
        "no further permissions are granted, actions can only be done on objects one is a contact for"
    ),
    defaults=["admin", "user"],
)

PermissionSeeSidebar = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="see_sidebar",
    title=_l("Use Checkmk sidebar"),
    description=_l("Without this permission the Checkmk sidebar will be invisible"),
    defaults=config.default_authorized_builtin_role_ids,
)

PermissionConfigureSidebar = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="configure_sidebar",
    title=_l("Configure sidebar"),
    description=_l("This allows the user to add, move and remove sidebar snap-ins."),
    defaults=["admin", "user"],
)

PermissionEditProfile = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="edit_profile",
    title=_l("Edit the user profile"),
    description=_l("Permits the user to change the user profile settings."),
    defaults=["admin", "user"],
)

PermissionSeeAvailability = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="see_availability",
    title=_l("See the availability"),
    description=_l("See the availability views of hosts and services"),
    defaults=config.default_authorized_builtin_role_ids,
)

PermissionCsvExport = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="csv_export",
    title=_l("Use CSV export"),
    description=_l("Export data of views using the CSV export"),
    defaults=config.default_authorized_builtin_role_ids,
)

PermissionEditNotifications = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="edit_notifications",
    title=_l("Edit personal notification settings"),
    description=_l(
        "This allows a user to edit his personal notification settings. You also need the permission "
        "<i>Edit the user profile</i> in order to do this."
    ),
    defaults=["admin", "user"],
)

PermissionDisableNotifications = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="disable_notifications",
    title=_l("Disable all personal notifications"),
    description=_l(
        "This permissions provides a checkbox and time range in the personal settings of the user that "
        "allows him to completely disable all of his notifications. Use with caution."
    ),
    defaults=["admin"],
)

PermissionEditUserAttributes = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="edit_user_attributes",
    title=_l("Edit personal user attributes"),
    description=_l(
        "This allows a user to edit his personal user attributes. You also need the permission "
        "<i>Edit the user profile</i> in order to do this."
    ),
    defaults=["admin", "user"],
)

PermissionChangePassword = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="change_password",
    title=_l("Edit the user password"),
    description=_l("Permits the user to change the password."),
    defaults=["admin", "user"],
)

PermissionManage2Fa = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="manage_2fa",
    title=_l("Edit the user two-factor authentication"),
    description=_l("Permits the user to edit two-factor authentication (Webauthn credentials)."),
    defaults=["admin", "user"],
)

PermissionLogout = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="logout",
    title=_l("Logout"),
    description=_l("Permits the user to logout."),
    defaults=config.default_authorized_builtin_role_ids,
)

PermissionIgnoreSoftLimit = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="ignore_soft_limit",
    title=_l("Ignore soft query limit"),
    description=_l(
        "Allows to ignore the soft query limit imposed upon the number of datasets returned by a query"
    ),
    defaults=["admin", "user"],
)

PermissionIgnoreHardLimit = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="ignore_hard_limit",
    title=_l("Ignore hard query limit"),
    description=_l(
        "Allows to ignore the hard query limit imposed upon the number of datasets returned by a query"
    ),
    defaults=["admin"],
)

PermissionAcknowledgeWerks = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="acknowledge_werks",
    title=_l("Acknowledge incompatible Werks"),
    description=_l(
        "In the change log of the Checkmk software version the administrator can manage change log entries "
        "(Werks) that requrire user interaction. These <i>incompatible Werks</i> can be acknowledged only "
        "if the user has this permission."
    ),
    defaults=["admin"],
)

PermissionSeeFailedNotifications24H = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="see_failed_notifications_24h",
    title=_l("See failed notifications (last 24 hours)"),
    description=_l(
        "If Checkmk is unable to notify users about problems, the site will warn about this situation "
        "very visibly inside the UI (both in the tactical overview and the dashboard). This affects only "
        "users with this permission. Users with this permission will only see failed notifications "
        "that occurred within the last 24 hours."
    ),
    defaults=["user"],
)

PermissionSeeFailedNotifications = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="see_failed_notifications",
    title=_l("See failed notifications (all)"),
    description=_l(
        "If Checkmk is unable to notify users about problems, the site will warn about this situation "
        "very visibly inside the UI (both in the tactical overview and the dashboard). This affects only "
        "users with this permission. Users with this permission will see failed notifications between now "
        'and the configured <a href="wato.py?mode=edit_configvar&varname=failed_notification_horizon">Failed notification horizon</a>.'
    ),
    defaults=["admin"],
)

PermissionSeeStalesInTacticalOverview = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="see_stales_in_tactical_overview",
    title=_l("See stale objects in tactical overview"),
    description=_l(
        "Show the column for stale host and service checks in the tactical overview snap-in."
    ),
    defaults=config.default_authorized_builtin_role_ids,
)

PermissionSeeCrashReports = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="see_crash_reports",
    title=_l("See crash reports"),
    description=_l(
        "In case an exception happens while Checkmk is running it may produce crash reports that you can "
        "use to track down the issues in the code or send it as report to the Checkmk team to fix this issue "
        "Only users with this permission are able to see the reports in the GUI."
    ),
    defaults=["admin"],
)

PermissionParentChildTopology = Permission(
    section=PERMISSION_SECTION_GENERAL,
    name="parent_child_topology",
    title=_l("Network topology"),
    description=_l(
        "This dashboard uses the parent relationships of your hosts to display a hierarchical map."
    ),
    defaults=config.default_authorized_builtin_role_ids,
)
