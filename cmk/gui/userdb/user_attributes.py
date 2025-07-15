#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.utils.rulesets.definition import RuleGroup
from cmk.utils.urls import is_allowed_url

from cmk.gui.exceptions import MKUserError
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.theme.choices import theme_choices
from cmk.gui.utils.temperate_unit import temperature_unit_choices
from cmk.gui.utils.urls import makeuri_contextless
from cmk.gui.valuespec import (
    AbsoluteDate,
    Alternative,
    Checkbox,
    Dictionary,
    DropdownChoice,
    FixedValue,
    MigrateNotUpdated,
    TextInput,
    Tuple,
    ValueSpec,
)

from ._user_attribute import UserAttribute, UserAttributeRegistry


def register(user_attribute_registry: UserAttributeRegistry) -> None:
    user_attribute_registry.register(TemperatureUnitUserAttribute)
    user_attribute_registry.register(ForceAuthUserUserAttribute)
    user_attribute_registry.register(DisableNotificationsUserAttribute)
    user_attribute_registry.register(StartURLUserAttribute)
    user_attribute_registry.register(UIThemeUserAttribute)
    user_attribute_registry.register(UISidebarPosition)
    user_attribute_registry.register(UIIconTitle)
    user_attribute_registry.register(UIIconPlacement)
    user_attribute_registry.register(UIBasicAdvancedToggle)
    user_attribute_registry.register(ContextualHelpIcon)


class TemperatureUnitUserAttribute(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "temperature_unit"

    def topic(self) -> str:
        return "personal"

    def valuespec(self) -> Alternative:
        return Alternative(
            title=_("Temperature unit"),
            orientation="horizontal",
            help=_(
                "Set the temperature unit used for graphs and perfometers. The default unit can be "
                "configured <a href='%s'>here</a>. Note that this setting does not affect the "
                "temperature unit used in service outputs, which can however be configured in "
                "<a href='%s'>this ruleset</a>."
            )
            % (
                makeuri_contextless(
                    request,
                    [
                        ("mode", "edit_configvar"),
                        ("varname", "default_temperature_unit"),
                    ],
                    filename="wato.py",
                ),
                makeuri_contextless(
                    request,
                    [
                        ("mode", "edit_ruleset"),
                        (
                            "varname",
                            RuleGroup.CheckgroupParameters("temperature"),
                        ),
                    ],
                    filename="wato.py",
                ),
            ),
            elements=[
                FixedValue(
                    value=None,
                    title=_("Use the default temperature unit"),
                    totext="",
                ),
                DropdownChoice(
                    title=_("Set custom temperature unit"),
                    choices=temperature_unit_choices(),
                ),
            ],
        )


class ForceAuthUserUserAttribute(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "force_authuser"

    def topic(self) -> str:
        return "personal"

    def valuespec(self) -> ValueSpec:
        return Checkbox(
            title=_("Visibility of hosts/services"),
            label=_("Only show hosts and services the user is a contact for"),
            help=_(
                "When this option is checked, the status GUI will only "
                "display hosts and services that the user is a contact for - "
                "even they have the permission for seeing all objects."
            ),
        )

    def permission(self) -> None | str:
        return "general.see_all"


class DisableNotificationsUserAttribute(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "disable_notifications"

    def topic(self) -> str:
        return "personal"

    def valuespec(self) -> ValueSpec:
        return MigrateNotUpdated(
            valuespec=Dictionary(
                title=_("Disable notifications"),
                help=_(
                    "When this option is active you will not get <b>any</b> "
                    "alerts or other notifications via email, SMS or similar. "
                    "This overrides all other notification settings and rules, so make "
                    "sure that you know what you do. Moreover you can specify a time range "
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
                            title=_("Customize time range"),
                            elements=[
                                AbsoluteDate(title=_("From:"), include_time=True),
                                AbsoluteDate(title=_("To:"), include_time=True),
                            ],
                        ),
                    ),
                ],
            ),
            migrate=lambda x: {} if x is None else x,
        )

    def permission(self) -> None | str:
        return "general.disable_notifications"

    def domain(self) -> str:
        return "check_mk"


class StartURLUserAttribute(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "start_url"

    def topic(self) -> str:
        return "personal"

    def valuespec(self) -> ValueSpec:
        return MigrateNotUpdated(
            valuespec=Alternative(
                title=_("Start URL to display in main frame"),
                orientation="horizontal",
                elements=[
                    FixedValue(
                        value=None,
                        title=_("Default start URL"),
                        totext="",
                    ),
                    FixedValue(
                        value="welcome.py",
                        title=_("Get started (Welcome)"),
                        totext="",
                    ),
                    TextInput(
                        title=_("Custom start URL"),
                        help=_(
                            "When you point your browser to the Checkmk GUI, usually the dashboard "
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
            migrate=lambda v: None if v == "" else v,
        )

    def domain(self) -> str:
        return "multisite"


def validate_start_url(value: str, varprefix: str) -> None:
    if not is_allowed_url(value):
        raise MKUserError(
            varprefix,
            _(
                "The given value is not allowed. You may only configure "
                "relative URLs like <tt>dashboard.py?name=my_dashboard</tt>."
            ),
        )


class UIThemeUserAttribute(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "ui_theme"

    def topic(self) -> str:
        return "interface"

    def valuespec(self) -> ValueSpec:
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


class UISidebarPosition(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "ui_sidebar_position"

    def topic(self) -> str:
        return "interface"

    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Sidebar position"),
            # FIXME: Why isn't this simply a bool instead of an Literal["left"] | None?
            choices=[(None, _("Right")), ("left", _("Left"))],
        )

    def domain(self) -> str:
        return "multisite"


class UIIconTitle(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "nav_hide_icons_title"

    def topic(self) -> str:
        return "interface"

    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Navigation bar icons"),
            help=_(
                "With this option you can define if icons in the navigation "
                "bar should show a title or not. This gives you the possibility "
                "to save some space in the UI."
            ),
            # FIXME: Why isn't this simply a bool instead of an Literal["hide"] | None?
            choices=[(None, _("Show title")), ("hide", _("Hide title"))],
        )


class UIIconPlacement(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "icons_per_item"

    def topic(self) -> str:
        return "interface"

    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Mega menu icons"),
            help=_(
                "In the main menus you can select between two options: "
                "Have a green icon only for the headlines – the 'topics' – "
                "for lean design. Or have a colored icon for every entry so that "
                "over time you can zoom in more quickly to a specific entry."
            ),
            # FIXME: Why isn't this simply a bool instead of an Literal["entry"] | None?
            choices=[(None, _("Per topic")), ("entry", _("Per entry"))],
        )

    def domain(self) -> str:
        return "multisite"


class UIBasicAdvancedToggle(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "show_mode"

    def topic(self) -> str:
        return "interface"

    def valuespec(self) -> ValueSpec:
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


class ContextualHelpIcon(UserAttribute):
    @classmethod
    def name(cls) -> str:
        return "contextual_help_icon"

    def topic(self) -> str:
        return "interface"

    def valuespec(self) -> ValueSpec:
        return DropdownChoice(
            title=_("Contextual help icon"),
            help=_("Some help text"),
            choices=[(None, _("Show icon")), ("hide_icon", _("Hide icon"))],
        )

    def domain(self) -> str:
        return "multisite"


def show_mode_choices() -> list[tuple[str | None, str]]:
    return [
        ("default_show_less", _("Default to show less")),
        ("default_show_more", _("Default to show more")),
        ("enforce_show_more", _("Enforce show more")),
    ]
