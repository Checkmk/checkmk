#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.plugins.userdb.utils import (
    show_mode_choices,
    user_attribute_registry,
    UserAttribute,
    validate_start_url,
)
from cmk.gui.utils.theme import theme_choices
from cmk.gui.valuespec import (
    AbsoluteDate,
    Alternative,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    TextInput,
    Transform,
    Tuple,
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
            title=_("Visibility of hosts/services"),
            label=_("Only show hosts and services the user is a contact for"),
            help=_(
                "When this option is checked, then the status GUI will only "
                "display hosts and services that the user is a contact for - "
                "even if he has the permission for seeing all objects."
            ),
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
        return Transform(
            valuespec=Dictionary(
                title=_("Disable notifications"),
                help=_(
                    "When this option is active you will not get <b>any</b> "
                    "alerts or other notifications via email, SMS or similar. "
                    "This overrides all other notification settings and rules, so make "
                    "sure that you know what you do. Moreover you can specify a timerange "
                    "where no notifications are generated."
                ),
                elements=[
                    (
                        "disable",
                        FixedValue(
                            value=True,
                            title=_("Temporarily disable <b>all</b> notifications!"),
                            totext="",
                        ),
                    ),
                    (
                        "timerange",
                        Tuple(
                            title=_("Customize timerange"),
                            elements=[
                                AbsoluteDate(title=_("From:"), include_time=True),
                                AbsoluteDate(title=_("To:"), include_time=True),
                            ],
                        ),
                    ),
                ],
            ),
            forth=lambda x: {} if x is None else x,
        )

    def permission(self):
        return "general.disable_notifications"

    def domain(self) -> str:
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
            valuespec=Alternative(
                title=_("Start URL to display in main frame"),
                orientation="horizontal",
                elements=[
                    FixedValue(
                        value=None,
                        title=_("Use the default start URL"),
                        totext="",
                    ),
                    TextInput(
                        title=_("Use this custom start URL"),
                        help=_(
                            "When you point your browser to the Check_MK GUI, usually the dashboard "
                            "is shown in the main (right) frame. You can replace this with any other "
                            "URL you like here."
                        ),
                        size=80,
                        default_value="dashboard.py",
                        allow_empty=False,
                        validate=validate_start_url,
                    ),
                ],
            ),
            forth=lambda v: None if v == "" else v,
        )

    def domain(self) -> str:
        return "multisite"


@user_attribute_registry.register
class UIThemeUserAttribute(UserAttribute):
    @classmethod
    def name(cls):
        return "ui_theme"

    def topic(self):
        return "interface"

    def valuespec(self):
        return Alternative(
            title=_("User interface theme"),
            orientation="horizontal",
            elements=[
                FixedValue(
                    value=None,
                    title=_("Use the default theme"),
                    totext="",
                ),
                DropdownChoice(
                    title=_("Set custom theme"),
                    choices=theme_choices(),
                ),
            ],
        )

    def domain(self) -> str:
        return "multisite"


@user_attribute_registry.register
class UISidebarPosition(UserAttribute):
    @classmethod
    def name(cls):
        return "ui_sidebar_position"

    def topic(self):
        return "interface"

    def valuespec(self):
        return DropdownChoice(
            title=_("Sidebar position"),
            # FIXME: Why isn't this simply a bool instead of an Optional[Literal["left"]]?
            choices=[(None, _("Right")), ("left", _("Left"))],
        )

    def domain(self) -> str:
        return "multisite"


@user_attribute_registry.register
class UIIconTitle(UserAttribute):
    @classmethod
    def name(cls):
        return "nav_hide_icons_title"

    def topic(self):
        return "interface"

    def valuespec(self):
        return DropdownChoice(
            title=_("Navigation bar icons"),
            help=_(
                "With this option you can define if icons in the navigation "
                "bar should show a title or not. This gives you the possibility "
                "to save some space in the UI."
            ),
            # FIXME: Why isn't this simply a bool instead of an Optional[Literal["hide"]]?
            choices=[(None, _("Show title")), ("hide", _("Do not show title"))],
        )


@user_attribute_registry.register
class UIIconPlacement(UserAttribute):
    @classmethod
    def name(cls):
        return "icons_per_item"

    def topic(self):
        return "interface"

    def valuespec(self):
        return DropdownChoice(
            title=_("Mega menu icons"),
            help=_(
                "In the mega menus you can select between two options: "
                "Have a green icon only for the headlines – the 'topics' – "
                "for lean design. Or have a colored icon for every entry so that "
                "over time you can zoom in more quickly to a specific entry."
            ),
            # FIXME: Why isn't this simply a bool instead of an Optional[Literal["entry"]]?
            choices=[(None, _("Per topic")), ("entry", _("Per entry"))],
        )

    def domain(self) -> str:
        return "multisite"


@user_attribute_registry.register
class UIBasicAdvancedToggle(UserAttribute):
    @classmethod
    def name(cls):
        return "show_mode"

    def topic(self):
        return "interface"

    def valuespec(self):
        return Alternative(
            title=_("Show more / Show less"),
            orientation="horizontal",
            help=_(
                "In some places like e.g. the main menu Checkmk divides "
                "features, filters, input fields etc. in two categories, showing "
                "more or less entries. With this option you can set a default "
                "mode for unvisited menus. Alternatively, you can enforce to "
                "show more, so that the round button with the three dots is not "
                "shown at all."
            ),
            elements=[
                FixedValue(
                    value=None,
                    title=_("Use the default show mode"),
                    totext="",
                ),
                DropdownChoice(
                    title=_("Set custom show mode"),
                    choices=show_mode_choices(),
                ),
            ],
        )

    def domain(self) -> str:
        return "multisite"
