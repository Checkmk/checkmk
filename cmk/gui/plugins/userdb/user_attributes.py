#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

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


@user_attribute_registry.register
class UISidebarPosition(UserAttribute):
    @classmethod
    def name(cls):
        return "ui_sidebar_position"

    def topic(self):
        return "personal"

    def valuespec(self):
        return DropdownChoice(
            title=_("Sidebar position"),
            choices=[(None, _("Right")), ("left", _("Left"))],
            no_preselect_value=False,
        )

    def domain(self):
        return "multisite"


@user_attribute_registry.register
class UIIconPlacement(UserAttribute):
    @classmethod
    def name(cls):
        return "icons_per_item"

    def topic(self):
        return "personal"

    def valuespec(self):
        return DropdownChoice(
            title=_("Main menu icons"),
            choices=[(None, _("Per topic")), ("entry", _("Per entry"))],
            no_preselect_value=False,
        )

    def domain(self):
        return "multisite"


@user_attribute_registry.register
class UIBasicAdvancedToggle(UserAttribute):
    @classmethod
    def name(cls):
        return "ui_basic_advanced_mode"

    def topic(self):
        return "personal"

    def valuespec(self):
        return DropdownChoice(
            title=_("Basic / advanced mode"),
            help=_(
                "In some places like e.g. the main menu Checkmk divides features, "
                "filters, input fields etc. in two categories - basic and advanced. With this"
                "option you can set a default mode for unvisited menus. Alternatively, you can "
                "enforce one mode so that the round button with the three dots is not shown at all."
            ),
            choices=[
                (None, _("Default to basic mode")),
                ("default_advanced", _("Default to advanced mode")),
                ("enforce_basic", _("Enforce basic mode")),
                ("enforce_advanced", _("Enforce advanced mode")),
            ],
        )

    def domain(self):
        return "multisite"
