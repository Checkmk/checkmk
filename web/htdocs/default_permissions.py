#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import config
loaded_with_language = False

#   .----------------------------------------------------------------------.
#   |        ____                     _         _                          |
#   |       |  _ \ ___ _ __ _ __ ___ (_)___ ___(_) ___  _ __  ___          |
#   |       | |_) / _ \ '__| '_ ` _ \| / __/ __| |/ _ \| '_ \/ __|         |
#   |       |  __/  __/ |  | | | | | | \__ \__ \ | (_) | | | \__ \         |
#   |       |_|   \___|_|  |_| |_| |_|_|___/___/_|\___/|_| |_|___/         |
#   |                                                                      |
#   +----------------------------------------------------------------------+
#   |                                                                      |
#   | Declare general permissions for Multisite                            |
#   '----------------------------------------------------------------------'

def load():
    global loaded_with_language
    if loaded_with_language == current_language:
        return

    config.declare_permission_section("general", _('General Permissions'), 10)

    config.declare_permission("general.use",
         _("Use Multisite at all"),
         _("Users without this permission are not let in at all"),
         [ "admin", "user", "guest" ])

    config.declare_permission("general.see_all",
         _("See all Nagios objects"),
         _("See all objects regardless of contacts and contact groups. "
           "If combined with 'perform commands' then commands may be done on all objects."),
         [ "admin", "guest" ])

    config.declare_permission("general.edit_views",
         _("Customize views and use them"),
         _("Allows to create own views, customize builtin views and use them."),
         [ "admin", "user" ])

    config.declare_permission("general.publish_views",
         _("Publish views"),
         _("Make views visible and usable for other users"),
         [ "admin", "user" ])

    config.declare_permission("general.force_views",
         _("Modify builtin views"),
         _("Make own published views override builtin views for all users"),
         [ "admin" ])

    config.declare_permission("general.view_option_columns",
         _("Change view display columns"),
         _("Interactively change the number of columns being displayed by a view (does not edit or customize the view)"),
         [ "admin", "user", "guest" ])

    config.declare_permission("general.view_option_refresh",
         _("Change view display refresh"),
         _("Interactively change the automatic browser reload of a view being displayed (does not edit or customize the view)"),
         [ "admin", "user" ])

    config.declare_permission("general.painter_options",
         _("Change column display options"),
         _("Some of the display columns offer options for customizing their output. "
         "For example time stamp columns can be displayed absolute, relative or "
         "in a mixed style. This permission allows the user to modify display options"),
         [ "admin", "user", "guest" ])

    config.declare_permission("general.act",
         _("Perform commands"),
         _("Allows users to perform Nagios commands. If no further permissions "
           "are granted, actions can only be done on objects one is a contact for"),
         [ "admin", "user" ])

    config.declare_permission("general.see_sidebar",
         _("Use Check_MK sidebar"),
         _("Without this permission the Check_MK sidebar will be invisible"),
         [ "admin", "user", "guest" ])

    config.declare_permission("general.configure_sidebar",
         _("Configure sidebar"),
         _("This allows the user to add, move and remove sidebar snapins."),
         [ "admin", "user" ])

    config.declare_permission('general.edit_profile',
        _('Edit the user profile'),
        _('Permits the user to change the user profile settings.'),
        [ 'admin', 'user' ]
    )

    config.declare_permission('general.edit_notifications',
        _('Edit personal notification settings'),
        _('This allows a user to edit his personal notification settings. You also need the permission '
          '<i>Edit the user profile</i> in order to do this.'),
        [ 'admin', 'user' ]
    )

    config.declare_permission('general.edit_user_attributes',
        _('Edit personal user attributes'),
        _('This allows a user to edit his personal user attributes. You also need the permission '
          '<i>Edit the user profile</i> in order to do this.'),
        [ 'admin', 'user' ]
    )

    config.declare_permission('general.change_password',
        _('Edit the user password'),
        _('Permits the user to change the password.'),
        [ 'admin', 'user' ]
    )

    config.declare_permission('general.logout',
        _('Logout'),
        _('Permits the user to logout.'),
        [ 'admin', 'user', 'guest' ]
    )

    config.declare_permission("general.ignore_soft_limit",
         _("Ignore soft query limit"),
         _("Allows to ignore the soft query limit imposed upon the number of datasets returned by a query"),
         [ "admin", "user" ])

    config.declare_permission("general.ignore_hard_limit",
         _("Ignore hard query limit"),
         _("Allows to ignore the hard query limit imposed upon the number of datasets returned by a query"),
         [ "admin" ])

    loaded_with_language = current_language
