#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
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
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import cmk.gui.utils as utils
from cmk.gui.config import theme_choices
from cmk.gui.valuespec import (
    DropdownChoice,
    FixedValue,
    Alternative,
    Transform,
    TextAscii,
    AbsoluteDate,
    Tuple,
    Dictionary,
    Checkbox,
)
from cmk.gui.i18n import _
from cmk.gui.plugins.userdb import (
    UserAttribute,
    user_attribute_registry,
)


@user_attribute_registry.register
class ForceAuthUserUserAttribute(UserAttribute):
    @classmethod
    def name(cls):
        return "force_authuser"

    def topic(self):
        return "personal"

    def valuespec(self):
        return Checkbox(
            title=_("Visibility of Hosts/Services"),
            label=_("Only show hosts and services the user is a contact for"),
            help=_("When this option is checked, then the status GUI will only "
                   "display hosts and services that the user is a contact for - "
                   "even if he has the permission for seeing all objects."),
        )

    def permission(self):
        return "general.see_all"


@user_attribute_registry.register
class DisableNotificationsUserAttribute(UserAttribute):
    @classmethod
    def name(cls):
        return "disable_notifications"

    def topic(self):
        return "personal"

    def valuespec(self):
        return Transform(Dictionary(
            title=_("Disable Notifications"),
            help=_("When this option is active you will not get <b>any</b> "
                   "alerts or other notifications via email, SMS or similar. "
                   "This overrides all other notification settings and rules, so make "
                   "sure that you know what you do. Moreover you can specify a timerange "
                   "where no notifications are generated."),
            elements=[("disable",
                       FixedValue(
                           True,
                           title=_("Temporarily disable <b>all</b> notifications!"),
                           totext="",
                       )),
                      ("timerange",
                       Tuple(title=_("Customize timerange"),
                             elements=[
                                 AbsoluteDate(title=_("From:"), include_time=True),
                                 AbsoluteDate(title=_("To:"), include_time=True),
                             ]))],
        ),
                         forth=self._transform_disable_notification)

    def _transform_disable_notification(self, p):
        if p is None:
            return {}
        if isinstance(p, bool):
            if p:
                return {"disable": True}
            return {}
        return p

    def permission(self):
        return "general.disable_notifications"

    def domain(self):
        return "check_mk"


@user_attribute_registry.register
class StartURLUserAttribute(UserAttribute):
    @classmethod
    def name(cls):
        return "start_url"

    def topic(self):
        return "personal"

    def valuespec(self):
        return Transform(
            Alternative(
                title=_("Start URL to display in main frame"),
                style="dropdown",
                orientation="horizontal",
                elements=[
                    FixedValue(
                        None,
                        title=_("Use the default start URL"),
                        totext="",
                    ),
                    TextAscii(
                        title=_("Use this custom start URL"),
                        help=
                        _("When you point your browser to the Check_MK GUI, usually the dashboard "
                          "is shown in the main (right) frame. You can replace this with any other "
                          "URL you like here."),
                        size=80,
                        default_value="dashboard.py",
                        attrencode=True,
                        allow_empty=False,
                        validate=utils.validate_start_url,
                    ),
                ],
            ),
            forth=lambda v: None if v == "" else v,
        )

    def domain(self):
        return "multisite"


@user_attribute_registry.register
class UIThemeUserAttribute(UserAttribute):
    @classmethod
    def name(cls):
        return "ui_theme"

    def topic(self):
        return "personal"

    def valuespec(self):
        return Alternative(
            title=_("User interface theme"),
            style="dropdown",
            orientation="horizontal",
            elements=[
                FixedValue(
                    None,
                    title=_("Use the default theme"),
                    totext="",
                ),
                DropdownChoice(
                    title=_("Set custom theme"),
                    choices=theme_choices(),
                ),
            ],
        )

    def domain(self):
        return "multisite"
