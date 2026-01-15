#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Sequence
from typing import Any, Literal, Protocol

import livestatus

import cmk.utils.version as cmk_version
from cmk.utils.hostaddress import HostName
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.render import SecondsRenderer
from cmk.utils.servicename import ServiceName

import cmk.gui.sites as sites
import cmk.gui.utils.escaping as escaping
from cmk.gui.config import active_config
from cmk.gui.exceptions import MKUserError
from cmk.gui.forms import open_submit_button_container_div
from cmk.gui.hooks import request_memoize
from cmk.gui.htmllib.foldable_container import foldable_container
from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _, _l, _u, ungettext
from cmk.gui.logged_in import user
from cmk.gui.permissions import (
    Permission,
    PermissionRegistry,
    PermissionSection,
    PermissionSectionRegistry,
)
from cmk.gui.type_defs import Choices, Row, Rows
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.time import timezone_utc_offset_str
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.valuespec import (
    AbsoluteDate,
    Age,
    Checkbox,
    DatePicker,
    Dictionary,
    TimePicker,
)
from cmk.gui.view_utils import render_cre_upgrade_button
from cmk.gui.watolib.downtime import determine_downtime_mode, DowntimeSchedule

from .base import Command, CommandActionResult, CommandConfirmDialogOptions, CommandSpec
from .group import CommandGroup, CommandGroupRegistry
from .registry import CommandRegistry


def register(
    command_group_registry: CommandGroupRegistry,
    command_registry: CommandRegistry,
    permission_section_registry: PermissionSectionRegistry,
    permission_registry: PermissionRegistry,
) -> None:
    command_group_registry.register(CommandGroupVarious)
    command_group_registry.register(CommandGroupFakeCheck)
    command_group_registry.register(CommandGroupAcknowledge)
    command_group_registry.register(CommandGroupDowntimes)
    command_registry.register(CommandReschedule)
    command_registry.register(CommandNotifications)
    command_registry.register(CommandToggleActiveChecks)
    command_registry.register(CommandTogglePassiveChecks)
    command_registry.register(CommandClearModifiedAttributes)
    command_registry.register(CommandFakeCheckResult)
    command_registry.register(CommandCustomNotification)
    command_registry.register(CommandAcknowledge)
    command_registry.register(CommandRemoveAcknowledgments)
    command_registry.register(CommandAddComment)
    command_registry.register(CommandScheduleDowntimes)
    command_registry.register(CommandRemoveDowntime)
    command_registry.register(CommandRemoveComments)
    permission_section_registry.register(PermissionSectionAction)
    permission_registry.register(PermissionActionReschedule)
    permission_registry.register(PermissionActionNotifications)
    permission_registry.register(PermissionActionEnableChecks)
    permission_registry.register(PermissionActionClearModifiedAttributes)
    permission_registry.register(PermissionActionFakeChecks)
    permission_registry.register(PermissionActionCustomNotification)
    permission_registry.register(PermissionActionAcknowledge)
    permission_registry.register(PermissionActionAddComment)
    permission_registry.register(PermissionActionDowntimes)
    permission_registry.register(PermissionRemoveAllDowntimes)


class CommandGroupVarious(CommandGroup):
    @property
    def ident(self) -> str:
        return "various"

    @property
    def title(self) -> str:
        return _("Various Commands")

    @property
    def sort_index(self) -> int:
        return 20


class PermissionSectionAction(PermissionSection):
    @property
    def name(self) -> str:
        return "action"

    @property
    def title(self) -> str:
        return _("Commands on host and services")

    @property
    def do_sort(self):
        return True


#   .--Reschedule----------------------------------------------------------.
#   |          ____                _              _       _                |
#   |         |  _ \ ___  ___  ___| |__   ___  __| |_   _| | ___           |
#   |         | |_) / _ \/ __|/ __| '_ \ / _ \/ _` | | | | |/ _ \          |
#   |         |  _ <  __/\__ \ (__| | | |  __/ (_| | |_| | |  __/          |
#   |         |_| \_\___||___/\___|_| |_|\___|\__,_|\__,_|_|\___|          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionActionReschedule = Permission(
    section=PermissionSectionAction,
    name="reschedule",
    title=_l("Reschedule checks"),
    description=_l("Reschedule host and service checks"),
    defaults=["user", "admin"],
)


class CommandReschedule(Command):
    @property
    def ident(self) -> str:
        return "reschedule"

    @property
    def title(self) -> str:
        return _("Reschedule active checks")

    @property
    def confirm_title(self) -> str:
        return _("Reschedule active checks immediately?")

    @property
    def confirm_button(self) -> LazyString:
        return _l("Reschedule")

    @property
    def icon_name(self):
        return "service_duration"

    @property
    def permission(self) -> Permission:
        return PermissionActionReschedule

    @property
    def tables(self):
        return ["host", "service"]

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
    ) -> HTML:
        return HTML("<br><br>") + "Spreading: %s minutes" % request.var("_resched_spread")

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.write_text(_("Spread over") + " ")
        html.text_input(
            "_resched_spread",
            default_value="5",
            size=3,
            cssclass="number",
            required=True,
        )
        html.write_text(" " + _("minutes"))
        html.help(
            _(
                "Spreading distributes checks evenly over the specified period. "
                "This helps to avoid short-term peaks in CPU usage and "
                "therefore, performance problems."
            )
        )
        html.close_div()

        html.open_div(class_="group")
        html.button("_resched_checks", _("Reschedule"), cssclass="hot")
        html.button("_cancel", _("Cancel"))
        html.close_div()

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.var("_resched_checks"):
            spread = request.get_validated_type_input_mandatory(int, "_resched_spread")
            if spread < 0:
                raise MKUserError(
                    "_resched_spread",
                    _("Spread should be a positive number: %s") % spread,
                )

            t = time.time()
            if spread:
                t += spread * 60.0 * row_index / len(action_rows)

            command = "SCHEDULE_FORCED_" + cmdtag + "_CHECK;%s;%d" % (spec, int(t))
            return command, self.confirm_dialog_options(
                cmdtag,
                row,
                len(action_rows),
            )
        return None


# .
#   .--Enable/Disable Notifications----------------------------------------.
#   |           _____          ______  _           _     _                 |
#   |          | ____|_ __    / /  _ \(_)___  __ _| |__ | | ___            |
#   |          |  _| | '_ \  / /| | | | / __|/ _` | '_ \| |/ _ \           |
#   |          | |___| | | |/ / | |_| | \__ \ (_| | |_) | |  __/           |
#   |          |_____|_| |_/_/  |____/|_|___/\__,_|_.__/|_|\___|           |
#   |                                                                      |
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionActionNotifications = Permission(
    section=PermissionSectionAction,
    name="notifications",
    title=_l("Enable/disable notifications"),
    description=_l("Enable and disable notifications on hosts and services"),
    defaults=[],
)


class CommandNotifications(Command):
    @property
    def ident(self) -> str:
        return "notifications"

    @property
    def title(self) -> str:
        return _("Enable/disable notifications")

    @property
    def confirm_title(self) -> str:
        return (
            _("Enable notifications?")
            if request.var("_enable_notifications")
            else _("Disable notifications?")
        )

    @property
    def confirm_button(self) -> LazyString:
        return _l("Enable") if request.var("_enable_notifications") else _l("Disable")

    @property
    def permission(self) -> Permission:
        return PermissionActionNotifications

    @property
    def tables(self):
        return ["host", "service"]

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
    ) -> HTML:
        return HTML(
            "<br><br>"
            + (
                _("Notifications will be sent according to the notification rules")
                if request.var("_enable_notifications")
                else _("This will suppress all notifications")
            )
        )

    def confirm_dialog_icon_class(self) -> Literal["question", "warning"]:
        if request.var("_enable_notifications"):
            return "question"
        return "warning"

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.button("_enable_notifications", _("Enable"), cssclass="border_hot")
        html.button("_disable_notifications", _("Disable"), cssclass="border_hot")
        html.button("_cancel", _("Cancel"))
        html.close_div()

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.var("_enable_notifications"):
            return (
                "ENABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
                self.confirm_dialog_options(
                    cmdtag,
                    row,
                    len(action_rows),
                ),
            )
        if request.var("_disable_notifications"):
            return (
                "DISABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
                self.confirm_dialog_options(
                    cmdtag,
                    row,
                    len(action_rows),
                ),
            )
        return None


# .
#   .--Enable/Disable Active Checks----------------------------------------.
#   |           _____          ______  _           _     _                 |
#   |          | ____|_ __    / /  _ \(_)___  __ _| |__ | | ___            |
#   |          |  _| | '_ \  / /| | | | / __|/ _` | '_ \| |/ _ \           |
#   |          | |___| | | |/ / | |_| | \__ \ (_| | |_) | |  __/           |
#   |          |_____|_| |_/_/  |____/|_|___/\__,_|_.__/|_|\___|           |
#   |                                                                      |
#   |       _        _   _              ____ _               _             |
#   |      / \   ___| |_(_)_   _____   / ___| |__   ___  ___| | _____      |
#   |     / _ \ / __| __| \ \ / / _ \ | |   | '_ \ / _ \/ __| |/ / __|     |
#   |    / ___ \ (__| |_| |\ V /  __/ | |___| | | |  __/ (__|   <\__ \     |
#   |   /_/   \_\___|\__|_| \_/ \___|  \____|_| |_|\___|\___|_|\_\___/     |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionActionEnableChecks = Permission(
    section=PermissionSectionAction,
    name="enablechecks",
    title=_l("Enable/disable checks"),
    description=_l("Enable and disable active or passive checks on hosts and services"),
    defaults=[],
)


class CommandToggleActiveChecks(Command):
    @property
    def ident(self) -> str:
        return "toggle_active_checks"

    @property
    def title(self) -> str:
        return _("Enable/Disable active checks")

    @property
    def confirm_title(self) -> str:
        return (
            _("Enable active checks")
            if request.var("_enable_checks")
            else _("Disable active checks")
        )

    @property
    def confirm_button(self) -> LazyString:
        return _l("Enable") if request.var("_enable_checks") else _l("Disable")

    @property
    def permission(self) -> Permission:
        return PermissionActionEnableChecks

    @property
    def tables(self):
        return ["host", "service"]

    def confirm_dialog_icon_class(self) -> Literal["question", "warning"]:
        return "warning"

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.button("_enable_checks", _("Enable"), cssclass="border_hot")
        html.button("_disable_checks", _("Disable"), cssclass="border_hot")
        html.button("_cancel", _("Cancel"))
        html.close_div()

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.var("_enable_checks"):
            return (
                "ENABLE_" + cmdtag + "_CHECK;%s" % spec,
                self.confirm_dialog_options(
                    cmdtag,
                    row,
                    len(action_rows),
                ),
            )
        if request.var("_disable_checks"):
            return (
                "DISABLE_" + cmdtag + "_CHECK;%s" % spec,
                self.confirm_dialog_options(
                    cmdtag,
                    row,
                    len(action_rows),
                ),
            )
        return None


# .
#   .--Enable/Disable Passive Checks---------------------------------------.
#   |           _____          ______  _           _     _                 |
#   |          | ____|_ __    / /  _ \(_)___  __ _| |__ | | ___            |
#   |          |  _| | '_ \  / /| | | | / __|/ _` | '_ \| |/ _ \           |
#   |          | |___| | | |/ / | |_| | \__ \ (_| | |_) | |  __/           |
#   |          |_____|_| |_/_/  |____/|_|___/\__,_|_.__/|_|\___|           |
#   |                                                                      |
#   |   ____               _              ____ _               _           |
#   |  |  _ \ __ _ ___ ___(_)_   _____   / ___| |__   ___  ___| | _____    |
#   |  | |_) / _` / __/ __| \ \ / / _ \ | |   | '_ \ / _ \/ __| |/ / __|   |
#   |  |  __/ (_| \__ \__ \ |\ V /  __/ | |___| | | |  __/ (__|   <\__ \   |
#   |  |_|   \__,_|___/___/_| \_/ \___|  \____|_| |_|\___|\___|_|\_\___/   |
#   |                                                                      |
#   '----------------------------------------------------------------------'


class CommandTogglePassiveChecks(Command):
    @property
    def ident(self) -> str:
        return "toggle_passive_checks"

    @property
    def title(self) -> str:
        return _("Enable/Disable passive checks")

    @property
    def confirm_title(self) -> str:
        return (
            _("Enable passive checks")
            if request.var("_enable_passive_checks")
            else _("Disable passive checks")
        )

    @property
    def confirm_button(self) -> LazyString:
        return _l("Enable") if request.var("_enable_passive_checks") else _l("Disable")

    @property
    def permission(self) -> Permission:
        return PermissionActionEnableChecks

    @property
    def tables(self):
        return ["host", "service"]

    def confirm_dialog_icon_class(self) -> Literal["question", "warning"]:
        return "warning"

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.button("_enable_passive_checks", _("Enable"), cssclass="border_hot")
        html.button("_disable_passive_checks", _("Disable"), cssclass="border_hot")
        html.button("_cancel", _("Cancel"))
        html.close_div()

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.var("_enable_passive_checks"):
            return (
                "ENABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec,
                self.confirm_dialog_options(
                    cmdtag,
                    row,
                    len(action_rows),
                ),
            )
        if request.var("_disable_passive_checks"):
            return (
                "DISABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec,
                self.confirm_dialog_options(
                    cmdtag,
                    row,
                    len(action_rows),
                ),
            )
        return None


# .
#   .--Clear Modified Attributes-------------------------------------------.
#   |            ____ _                   __  __           _               |
#   |           / ___| | ___  __ _ _ __  |  \/  | ___   __| |              |
#   |          | |   | |/ _ \/ _` | '__| | |\/| |/ _ \ / _` |              |
#   |          | |___| |  __/ (_| | |    | |  | | (_) | (_| |_             |
#   |           \____|_|\___|\__,_|_|    |_|  |_|\___/ \__,_(_)            |
#   |                                                                      |
#   |              _   _   _        _ _           _                        |
#   |             / \ | |_| |_ _ __(_) |__  _   _| |_ ___  ___             |
#   |            / _ \| __| __| '__| | '_ \| | | | __/ _ \/ __|            |
#   |           / ___ \ |_| |_| |  | | |_) | |_| | ||  __/\__ \            |
#   |          /_/   \_\__|\__|_|  |_|_.__/ \__,_|\__\___||___/            |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionActionClearModifiedAttributes = Permission(
    section=PermissionSectionAction,
    name="clearmodattr",
    title=_l("Reset modified attributes"),
    description=_l(
        "Reset all manually modified attributes of a host "
        "or service (like disabled notifications)"
    ),
    defaults=[],
)


class CommandClearModifiedAttributes(Command):
    @property
    def ident(self) -> str:
        return "clear_modified_attributes"

    @property
    def title(self) -> str:
        return _("Reset modified attributes")

    @property
    def confirm_button(self) -> LazyString:
        return _l("Reset")

    @property
    def permission(self) -> Permission:
        return PermissionActionClearModifiedAttributes

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.button("_clear_modattr", _("Reset attributes"), cssclass="hot")
        html.button("_cancel", _("Cancel"))
        html.close_div()

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
    ) -> HTML:
        return HTML(
            "<br><br>"
            + _("Resets the commands '%s', '%s' and '%s' to the default state")
            % (
                CommandToggleActiveChecks().title,
                CommandTogglePassiveChecks().title,
                CommandNotifications().title,
            )
        )

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.var("_clear_modattr"):
            return (
                "CHANGE_" + cmdtag + "_MODATTR;%s;0" % spec,
                self.confirm_dialog_options(
                    cmdtag,
                    row,
                    len(action_rows),
                ),
            )
        return None


# .
#   .--Fake Checks---------------------------------------------------------.
#   |         _____     _           ____ _               _                 |
#   |        |  ___|_ _| | _____   / ___| |__   ___  ___| | _____          |
#   |        | |_ / _` | |/ / _ \ | |   | '_ \ / _ \/ __| |/ / __|         |
#   |        |  _| (_| |   <  __/ | |___| | | |  __/ (__|   <\__ \         |
#   |        |_|  \__,_|_|\_\___|  \____|_| |_|\___|\___|_|\_\___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionActionFakeChecks = Permission(
    section=PermissionSectionAction,
    name="fakechecks",
    title=_l("Fake check results"),
    description=_l("Manually submit check results for host and service checks"),
    defaults=["admin"],
)


class CommandGroupFakeCheck(CommandGroup):
    @property
    def ident(self) -> str:
        return "fake_check"

    @property
    def title(self) -> str:
        return _("Fake check results")

    @property
    def sort_index(self) -> int:
        return 15


class CommandFakeCheckResult(Command):
    @property
    def ident(self) -> str:
        return "fake_check_result"

    @property
    def title(self) -> str:
        return _("Fake check results")

    @property
    def confirm_title(self) -> str:
        return _("Set fake check result to ‘%s’?") % self._get_target_state()

    def _get_target_state(self) -> str:
        state = request.var("_state")
        statename = request.var(f"_state_{state}")

        return "" if statename is None else statename

    @property
    def confirm_button(self) -> LazyString:
        return _l("Set to '%s'") % self._get_target_state()

    @property
    def icon_name(self):
        return "fake_check_result"

    @property
    def permission(self) -> Permission:
        return PermissionActionFakeChecks

    @property
    def tables(self):
        return ["host", "service"]

    @property
    def group(self) -> type[CommandGroup]:
        return CommandGroupFakeCheck

    @property
    def is_show_more(self) -> bool:
        return True

    def _link_to_test_notifications(self):
        return html.render_a(
            _("Test notification"),
            makeuri_contextless(request, [("mode", "notifications")], filename="wato.py"),
        )

    def _render_test_notification_tip(self):
        html.open_div(class_="info")
        html.icon("toggle_details")
        html.write_text(
            " &nbsp; "
            + _(
                "If you are looking for a way to test your notification settings, try '%s' in Setup > Notifications"
            )
            % self._link_to_test_notifications()
        )
        html.close_div()

    def _get_states(self, what):
        if what == "host":
            return [(0, _("Up")), (1, _("Down"))]

        return [(0, _("OK")), (1, _("Warning")), (2, _("Critical")), (3, _("Unknown"))]

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        self._render_test_notification_tip()

        html.open_div(class_="group")
        html.open_table(class_=["fake_check_result"])

        html.open_tr()
        html.open_td()
        html.write_text(_("Result") + " &nbsp; ")
        html.close_td()
        html.open_td()
        html.open_span(class_="inline_radio_group")
        for value, description in self._get_states(what):
            html.radiobutton("_state", value, value == 0, description)
            html.hidden_field(f"_state_{value}", description)
        html.close_span()
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Plug-in output") + " &nbsp; ")
        html.close_td()
        html.open_td()
        html.text_input("_fake_output", "", size=60, placeholder=_("What is the purpose?"))
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Performance data") + " &nbsp; ")
        html.close_td()
        html.open_td()
        html.text_input(
            "_fake_perfdata",
            "",
            size=60,
            placeholder=_("Enter performance data to show in notifications etc. ..."),
        )
        html.close_td()
        html.close_tr()

        html.close_table()
        html.close_div()

        html.open_div(class_="group")
        html.button("_fake_check_result", _("Fake check result"), cssclass="hot")
        html.button("_cancel", _("Cancel"))
        html.close_div()

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.var("_fake_check_result"):
            state = request.var("_state")
            statename = request.var(f"_state_{state}")
            pluginoutput = request.get_str_input_mandatory("_fake_output").strip()

            if not pluginoutput:
                pluginoutput = _("Manually set to %s by %s") % (
                    escaping.escape_attribute(statename),
                    user.id,
                )

            perfdata = request.var("_fake_perfdata")
            if perfdata:
                pluginoutput += "|" + perfdata

            command = "PROCESS_{}_CHECK_RESULT;{};{};{}".format(
                "SERVICE" if cmdtag == "SVC" else cmdtag,
                spec,
                state,
                livestatus.lqencode(pluginoutput),
            )

            return command, self.confirm_dialog_options(
                cmdtag,
                row,
                len(action_rows),
            )

        return None


# .
#   .--Custom Notifications------------------------------------------------.
#   |                   ____          _                                    |
#   |                  / ___|   _ ___| |_ ___  _ __ ___                    |
#   |                 | |  | | | / __| __/ _ \| '_ ` _ \                   |
#   |                 | |__| |_| \__ \ || (_) | | | | | |                  |
#   |                  \____\__,_|___/\__\___/|_| |_| |_|                  |
#   |                                                                      |
#   |       _   _       _   _  __ _           _   _                        |
#   |      | \ | | ___ | |_(_)/ _(_) ___ __ _| |_(_) ___  _ __  ___        |
#   |      |  \| |/ _ \| __| | |_| |/ __/ _` | __| |/ _ \| '_ \/ __|       |
#   |      | |\  | (_) | |_| |  _| | (_| (_| | |_| | (_) | | | \__ \       |
#   |      |_| \_|\___/ \__|_|_| |_|\___\__,_|\__|_|\___/|_| |_|___/       |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionActionCustomNotification = Permission(
    section=PermissionSectionAction,
    name="customnotification",
    title=_l("Send custom notification"),
    description=_l(
        "Manually let the core send a notification to a host or service in order "
        "to test if notifications are setup correctly"
    ),
    defaults=["user", "admin"],
)


class CommandCustomNotification(Command):
    @property
    def ident(self) -> str:
        return "send_custom_notification"

    @property
    def title(self) -> str:
        return _("Send custom notification")

    @property
    def confirm_title(self) -> str:
        return "%s?" % self.title

    @property
    def confirm_button(self) -> LazyString:
        return _l("Send")

    @property
    def icon_name(self):
        return "notifications"

    @property
    def permission(self) -> Permission:
        return PermissionActionCustomNotification

    @property
    def tables(self):
        return ["host", "service"]

    @property
    def is_show_more(self) -> bool:
        return True

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.text_input(
            "_cusnot_comment",
            id_="cusnot_comment",
            size=60,
            submit="_customnotification",
            label=_("Comment"),
            placeholder=_("Enter your message here"),
        )
        html.close_div()

        html.open_div(class_="group")
        html.checkbox(
            "_cusnot_forced",
            False,
            label=_(
                "Send regardless of restrictions, e.g. notification period or disabled notifications (forced)"
            ),
        )
        html.close_div()
        html.open_div(class_="group")
        html.checkbox(
            "_cusnot_broadcast",
            False,
            label=_("Send to all contacts of the selected hosts/services (broadcast)"),
        )
        html.close_div()

        html.open_div(class_="group")
        html.button("_customnotification", _("Send"), cssclass="hot")
        html.button("_cancel", _("Cancel"))
        html.close_div()

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.var("_customnotification"):
            comment = request.get_str_input_mandatory("_cusnot_comment")
            broadcast = 1 if html.get_checkbox("_cusnot_broadcast") else 0
            forced = 2 if html.get_checkbox("_cusnot_forced") else 0
            command = "SEND_CUSTOM_{}_NOTIFICATION;{};{};{};{}".format(
                cmdtag,
                spec,
                broadcast + forced,
                user.id,
                livestatus.lqencode(comment),
            )
            return command, self.confirm_dialog_options(
                cmdtag,
                row,
                len(action_rows),
            )
        return None


# .
#   .--Acknowledge---------------------------------------------------------.
#   |       _        _                        _          _                 |
#   |      / \   ___| | ___ __   _____      _| | ___  __| | __ _  ___      |
#   |     / _ \ / __| |/ / '_ \ / _ \ \ /\ / / |/ _ \/ _` |/ _` |/ _ \     |
#   |    / ___ \ (__|   <| | | | (_) \ V  V /| |  __/ (_| | (_| |  __/     |
#   |   /_/   \_\___|_|\_\_| |_|\___/ \_/\_/ |_|\___|\__,_|\__, |\___|     |
#   |                                                      |___/           |
#   '----------------------------------------------------------------------'

PermissionActionAcknowledge = Permission(
    section=PermissionSectionAction,
    name="acknowledge",
    title=_l("Acknowledge"),
    description=_l("Acknowledge host and service problems and remove acknowledgements"),
    defaults=["user", "admin"],
)


class CommandGroupAcknowledge(CommandGroup):
    @property
    def ident(self) -> str:
        return "acknowledge"

    @property
    def title(self) -> str:
        return _("Acknowledge")

    @property
    def sort_index(self) -> int:
        return 5


class CommandAcknowledge(Command):
    @property
    def ident(self) -> str:
        return "acknowledge"

    @property
    def title(self) -> str:
        return _("Acknowledge problems")

    @property
    def confirm_title(self) -> str:
        return _("Acknowledge problems?")

    @property
    def confirm_button(self) -> LazyString:
        return _l("Yes, acknowledge")

    @property
    def cancel_button(self) -> LazyString:
        return _l("No, discard")

    @property
    def deny_button(self) -> LazyString | None:
        return _l("No, adjust settings")

    @property
    def deny_js_function(self) -> str | None:
        return '() => cmk.page_menu.toggle_popup("popup_command_acknowledge")'

    @property
    def icon_name(self):
        return "ack"

    @property
    def is_shortcut(self) -> bool:
        return True

    @property
    def is_suggested(self) -> bool:
        return True

    @property
    def permission(self) -> Permission:
        return PermissionActionAcknowledge

    @property
    def group(self) -> type[CommandGroup]:
        return CommandGroupAcknowledge

    @property
    def tables(self):
        return ["host", "service", "aggr"]

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
    ) -> HTML:
        if request.var("_ack_expire"):
            date = request.get_str_input("_ack_expire_date")
            time_ = request.get_str_input("_ack_expire_time")
            timestamp = time.mktime(time.strptime(f"{date} {time_}", "%Y-%m-%d %H:%M"))
            formatted_datetime_str = self.confirm_dialog_date_and_time_format(timestamp)

        expire_conditions_li = html.render_li(
            _("On recovery (OK/UP)")
            if request.var("_ack_sticky")
            else _("If state changes OR on recovery (OK/UP)")
        )
        expire_time_li = html.render_li(
            _("On %s (server time).") % formatted_datetime_str
            if request.var("_ack_expire")
            else _("No expiration date")
        )
        persistent_comment_div = html.render_div(
            (
                _("Comment will be kept after acknowledgment expires.")
                if request.var("_ack_persistent")
                else _("Comment will be removed after acknowledgment expires.")
            ),
            class_="confirm_block",
        )

        return html.render_div(
            content=html.render_div(_("Acknowledgment expires:"), class_="confirm_block")
            + expire_conditions_li
            + expire_time_li
            + persistent_comment_div,
            class_="confirm_block",
        )

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        submit_id = "_acknowledge"
        html.open_div(class_="group")
        html.text_input(
            "_ack_comment",
            id_="ack_comment",
            size=60,
            submit=submit_id,
            label=_("Comment"),
            required=True,
            placeholder=_("e.g. ticket ID"),
            oninput=f"cmk.forms.enable_submit_buttons_on_nonempty_input(this, ['{submit_id}']);",
        )
        if request.get_str_input("_ack_comment"):
            html.final_javascript(
                f"cmk.forms.enable_submit_buttons_on_nonempty_input(document.getElementById('ack_comment'), ['{submit_id}']);"
            )

        html.close_div()

        html.open_div(class_="group ack_command_options")
        html.heading(_("Options"))
        if user.may("wato.global"):
            html.open_span()
            html.write_text("(")
            html.a(_("Edit defaults"), self._action_defaults_url())
            html.write_text(")")
            html.close_span()

        date, time_ = self._expiration_date_and_time(
            active_config.acknowledge_problems.get("ack_expire", 3600)
        )
        is_raw_edition: bool = cmk_version.edition() is cmk_version.Edition.CRE
        html.open_div(class_="disabled" if is_raw_edition else "")
        html.checkbox(
            "_ack_expire",
            False,
            label=_("Expire on"),
            onclick="cmk.page_menu.ack_problems_update_expiration_active_state(this);",
        )
        html.open_div(class_="date_time_picker")
        self._vs_date().render_input("_ack_expire_date", date)
        self._vs_time().render_input("_ack_expire_time", time_)
        html.close_div()

        html.span(
            timezone_utc_offset_str()
            + " "
            + _("Server time (currently: %s)")
            % time.strftime("%m/%d/%Y %H:%M", time.localtime(time.time())),
            class_="server_time",
        )
        if is_raw_edition:
            render_cre_upgrade_button()
        html.help(
            _("Note: Expiration of acknowledgements only works when using the Checkmk Micro Core.")
        )
        html.close_div()

        html.open_div()
        html.checkbox(
            "_ack_sticky",
            active_config.acknowledge_problems["ack_sticky"],
            label=_("Ignore status changes until services/hosts are OK/UP again (sticky)"),
        )
        html.div(
            "<b>"
            + _("Example:")
            + "</b> "
            + _("Service was WARN and goes CRIT - acknowledgment doesn't expire."),
            class_="example",
        )
        html.close_div()

        html.div(
            html.render_checkbox(
                "_ack_persistent",
                active_config.acknowledge_problems["ack_persistent"],
                label=_("Keep comment after acknowledgment expires (persistent comment)"),
            )
        )

        html.div(
            html.render_checkbox(
                "_ack_notify",
                active_config.acknowledge_problems["ack_notify"],
                label=_("Notify affected users if %s are in place (send notifications)")
                % self._link_to_notification_rules(),
            )
        )
        html.close_div()

        html.open_div(class_="group buttons")
        tooltip_submission_disabled = _("Enter a comment to acknowledge problems")
        open_submit_button_container_div(tooltip_submission_disabled)
        html.button(
            submit_id,
            _("Acknowledge problems"),
            cssclass="hot disabled",
        )
        html.close_div()

        html.buttonlink(makeuri(request, [], delvars=["filled_in"]), _("Cancel"))
        html.close_div()

    def _action_defaults_url(self) -> str:
        return makeuri_contextless(
            request,
            [("mode", "edit_configvar"), ("varname", "acknowledge_problems")],
            filename="wato.py",
        )

    def _link_to_notification_rules(self) -> HTML:
        return html.render_a(
            _("notification rules"),
            makeuri_contextless(request, [("mode", "notifications")], filename="wato.py"),
        )

    def _expiration_date_and_time(self, time_until_exp: int) -> tuple[str, str]:
        exp_time = time.localtime(time.time() + time_until_exp)
        return time.strftime("%Y-%m-%d", exp_time), time.strftime("%H:%M", exp_time)

    def _action(  # pylint: disable=too-many-branches
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if "aggr_tree" in row:  # BI mode
            specs = []
            for site, host, service in _find_all_leaves(row["aggr_tree"]):
                if service:
                    spec = f"{host};{service}"
                    cmdtag = "SVC"
                else:
                    spec = host
                    cmdtag = "HOST"
                specs.append((site, spec, cmdtag))

        if request.var("_acknowledge"):
            comment = request.get_str_input("_ack_comment")
            if not comment:
                raise MKUserError("_ack_comment", _("You need to supply a comment."))
            if ";" in comment:
                raise MKUserError("_ack_comment", _("The comment must not contain semicolons."))
            non_empty_comment = comment

            sticky = 2 if request.var("_ack_sticky") else 0
            sendnot = 1 if request.var("_ack_notify") else 0
            perscomm = 1 if request.var("_ack_persistent") else 0

            if request.var("_ack_expire"):
                expire_date = self._vs_date().from_html_vars("_ack_expire_date")
                expire_time = self._vs_time().from_html_vars("_ack_expire_time")
                expire_timestamp = int(
                    time.mktime(
                        time.strptime(f"{expire_date} {expire_time}", "%Y-%m-%d %H:%M"),
                    )
                )

                if expire_timestamp < time.time():
                    raise MKUserError(
                        "_ack_expire",
                        _("You cannot set an expiration date and time that is in the past:")
                        + f' "{expire_date} {expire_time}"',
                    )
                expire_text = ";%d" % expire_timestamp
            else:
                expire_text = ""

            def make_command_ack(spec, cmdtag):
                return (
                    "ACKNOWLEDGE_"
                    + cmdtag
                    + "_PROBLEM;%s;%d;%d;%d;%s" % (spec, sticky, sendnot, perscomm, user.id)
                    + (";%s" % livestatus.lqencode(non_empty_comment))
                    + expire_text
                )

            if "aggr_tree" in row:  # BI mode
                commands = [
                    (site, make_command_ack(spec_, cmdtag_)) for site, spec_, cmdtag_ in specs
                ]
            else:
                commands = [make_command_ack(spec, cmdtag)]

            return commands, self.confirm_dialog_options(
                cmdtag,
                row,
                len(action_rows),
            )

        return None

    def _vs_date(self) -> DatePicker:
        return DatePicker(
            title=_("Acknowledge problems date picker"),
            onchange="cmk.page_menu.ack_problems_update_expiration_active_state(this);",
        )

    def _vs_time(self) -> TimePicker:
        return TimePicker(
            title=_("Acknowledge problems time picker"),
            onchange="cmk.page_menu.ack_problems_update_expiration_active_state(this);",
        )


class CommandRemoveAcknowledgments(Command):
    @property
    def ident(self) -> str:
        return "remove_acknowledgments"

    @property
    def title(self) -> str:
        return _("Remove acknowledgments")

    @property
    def confirm_title(self) -> str:
        return _("Remove all acknowledgments?")

    @property
    def confirm_button(self) -> LazyString:
        return _l("Remove all")

    @property
    def icon_name(self):
        return "ack"

    @property
    def permission(self) -> Permission:
        return PermissionActionAcknowledge

    @property
    def group(self) -> type[CommandGroup]:
        return CommandGroupAcknowledge

    @property
    def tables(self):
        return ["host", "service", "aggr"]

    @property
    def show_command_form(self) -> bool:
        return False

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
    ) -> HTML:
        return (
            html.render_div(_("Acknowledgments: ") + str(self._number_of_acknowledgments))
            if self._number_of_acknowledgments
            else HTML()
        )

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if not request.var("_remove_acknowledgments"):
            return None

        def make_command_rem(spec, cmdtag):
            return "REMOVE_" + cmdtag + "_ACKNOWLEDGEMENT;%s" % spec

        # TODO: Can we also find out the number of acknowledgments for BI aggregation rows?
        self._number_of_acknowledgments: int | None = None
        if "aggr_tree" in row:  # BI mode
            specs = []
            for site, host, service in _find_all_leaves(row["aggr_tree"]):
                if service:
                    spec = f"{host};{service}"
                    cmdtag = "SVC"
                else:
                    spec = host
                    cmdtag = "HOST"
                specs.append((site, spec, cmdtag))
            commands = [(site, make_command_rem(spec, cmdtag)) for site, spec_, cmdtag_ in specs]
        else:
            commands = [make_command_rem(spec, cmdtag)]

            what = "host" if cmdtag == "HOST" else "service"
            unique_acknowledgments: set[tuple[str, str]] = set()
            for row_ in action_rows:
                unique_acknowledgments.update(
                    {
                        # take author and timestamp as unique acknowledgment key
                        # comment_spec = [id, author, comment, type, timestamp]
                        (comment_spec[1], comment_spec[4])
                        for comment_spec in row_.get(f"{what}_comments_with_extra_info", [])
                    }
                )
            self._number_of_acknowledgments = len(unique_acknowledgments)

        return commands, self.confirm_dialog_options(cmdtag, row, len(action_rows))


# .
#   .--Comments------------------------------------------------------------.
#   |           ____                                     _                 |
#   |          / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___           |
#   |         | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|          |
#   |         | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \          |
#   |          \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionActionAddComment = Permission(
    section=PermissionSectionAction,
    name="addcomment",
    title=_l("Add comments"),
    description=_l("Add comments to hosts or services, and remove comments"),
    defaults=["user", "admin"],
)


class CommandAddComment(Command):
    @property
    def ident(self) -> str:
        return "add_comment"

    @property
    def title(self) -> str:
        return _("Add comment")

    @property
    def confirm_title(self) -> str:
        return _("Add comment?")

    @property
    def confirm_button(self) -> LazyString:
        return _l("Add")

    @property
    def icon_name(self):
        return "comment"

    @property
    def permission(self) -> Permission:
        return PermissionActionAddComment

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.text_input(
            "_comment",
            id_="comment",
            size=60,
            submit="_add_comment",
            label=_("Comment"),
            required=True,
        )
        html.close_div()

        html.open_div(class_="group")
        html.button("_add_comment", _("Add comment"), cssclass="hot")
        html.jsbutton(
            "_cancel",
            _("Cancel"),
            onclick="cmk.page_menu.close_popup(this);document.getElementById('comment').value=''",
        )
        html.close_div()

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.var("_add_comment"):
            comment = request.get_str_input("_comment")
            if not comment:
                raise MKUserError("_comment", _("You need to supply a comment."))
            command = (
                "ADD_"
                + cmdtag
                + f"_COMMENT;{spec};1;{user.id}"
                + (";%s" % livestatus.lqencode(comment))
            )
            return command, self.confirm_dialog_options(cmdtag, row, len(action_rows))
        return None


# .
#   .--Downtimes-----------------------------------------------------------.
#   |         ____                      _   _                              |
#   |        |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___          |
#   |        | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|         |
#   |        | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \         |
#   |        |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

PermissionActionDowntimes = Permission(
    section=PermissionSectionAction,
    name="downtimes",
    title=_l("Set/remove downtimes"),
    description=_l("Schedule and remove downtimes on hosts and services"),
    defaults=["user", "admin"],
)

PermissionRemoveAllDowntimes = Permission(
    section=PermissionSectionAction,
    name="remove_all_downtimes",
    title=_l("Remove all downtimes"),
    description=_l('Allow the user to use the action "Remove all" downtimes'),
    defaults=["user", "admin"],
)


def hosts_user_can_see(users_sites: list[livestatus.SiteId] | None = None) -> Sequence[str]:
    """Returns a list of hostnames that the logged in user can see filtering
    on the action rows sites if they are provided."""
    hosts_query_result = Query([Hosts.name]).fetchall(
        sites=sites.live(),
        only_sites=users_sites,
    )
    return list({host["name"] for host in hosts_query_result})


class CommandGroupDowntimes(CommandGroup):
    @property
    def ident(self) -> str:
        return "downtimes"

    @property
    def title(self) -> str:
        return _("Schedule downtimes")

    @property
    def sort_index(self) -> int:
        return 10


class RecurringDowntimes(Protocol):
    def choices(self) -> Choices: ...

    def show_input_elements(self, default: str) -> None: ...

    def number(self) -> int: ...

    def title_prefix(self, recurring_number: int) -> str: ...


class NoRecurringDowntimes:
    def choices(self) -> Choices:
        return [("0", "never")]

    def show_input_elements(self, default: str) -> None:
        html.open_div(class_="group")
        html.dropdown(
            "_down_recurring",
            self.choices(),
            deflt=default,
            read_only=True,
        )
        render_cre_upgrade_button()
        html.close_div()

    def number(self) -> int:
        return 0

    def title_prefix(self, recurring_number: int) -> str:
        return _("Schedule an immediate downtime")


class CommandScheduleDowntimes(Command):
    recurring_downtimes: RecurringDowntimes = NoRecurringDowntimes()

    @property
    def ident(self) -> str:
        return "schedule_downtimes"

    @property
    def title(self) -> str:
        return _("Schedule downtimes")

    @property
    def confirm_title(self) -> str:
        return _("Schedule downtime?")

    @property
    def confirm_button(self) -> LazyString:
        return _l("Yes, schedule")

    @property
    def cancel_button(self) -> LazyString:
        return _l("No, discard")

    @property
    def deny_button(self) -> LazyString | None:
        return _l("No, adjust settings")

    @property
    def deny_js_function(self) -> str | None:
        return '() => cmk.page_menu.toggle_popup("popup_command_schedule_downtimes")'

    @property
    def icon_name(self):
        return "downtime"

    @property
    def is_shortcut(self) -> bool:
        return True

    @property
    def is_suggested(self) -> bool:
        return True

    @property
    def permission(self) -> Permission:
        return PermissionActionDowntimes

    @property
    def group(self) -> type[CommandGroup]:
        return CommandGroupDowntimes

    @property
    def tables(self):
        return ["host", "service", "aggr"]

    def user_confirm_options(
        self, len_rows: int, cmdtag: Literal["HOST", "SVC"]
    ) -> list[tuple[str, str]]:
        if cmdtag == "SVC" and not request.var("_down_remove"):
            return [
                (
                    _("Schedule downtime for %d %s")
                    % (len_rows, ungettext("service", "services", len_rows)),
                    "_do_confirm_service_downtime",
                ),
                (_("Schedule downtime on host"), "_do_confirm_host_downtime"),
            ]
        return super().user_confirm_options(len_rows, cmdtag)

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        if self._adhoc_downtime_configured():
            self._render_adhoc_comment(what)
        self._render_comment()
        self._render_date_and_time()
        self._render_advanced_options(what)
        self._render_confirm_buttons(what)

    def _render_adhoc_comment(self, what) -> None:  # type: ignore[no-untyped-def]
        adhoc_duration = active_config.adhoc_downtime.get("duration")
        adhoc_comment = active_config.adhoc_downtime.get("comment", "")
        html.open_div(class_="group")
        html.button("_down_adhoc", _("Ad hoc for %d minutes") % adhoc_duration)
        html.nbsp()
        html.write_text(_("Comment") + ": " + adhoc_comment)
        html.hr()
        html.close_div()

    def _render_comment(self) -> None:
        html.open_div(class_="group")
        html.text_input(
            "_down_comment",
            id_="down_comment",
            size=60,
            label=_("Comment"),
            required=not self._adhoc_downtime_configured(),
            placeholder=_("What is the occasion?"),
            submit="_down_custom",
            oninput="cmk.forms.enable_submit_buttons_on_nonempty_input(this, ['_down_host', '_down_service']);",
        )
        if request.get_str_input("_down_comment"):
            html.final_javascript(
                "cmk.forms.enable_submit_buttons_on_nonempty_input(document.getElementById('down_comment'), ['_down_host', '_down_service']);"
            )
        html.close_div()

    def _render_date_and_time(self) -> None:  # pylint: disable=too-many-statements
        html.open_div(class_="group")
        html.heading(_("Date and time"))

        html.open_table(class_=["down_date_and_time"])

        # Duration section
        html.open_tr()
        html.td(_("Duration"))
        html.open_td(class_="down_duration")
        html.write_html(self._get_duration_options())
        html.a(_("(Edit presets)"), href=self._get_presets_url(), class_="down_presets")
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Start"))
        html.close_td()
        html.open_td()
        self._vs_date().render_input("_down_from_date", time.strftime("%Y-%m-%d"))
        self._vs_time().render_input("_down_from_time", time.strftime("%H:%M"))
        html.span(
            timezone_utc_offset_str()
            + " "
            + _("Server time (currently: %s)") % time.strftime("%m/%d/%Y %H:%M", time.localtime()),
            class_="server_time",
        )
        html.close_td()
        html.close_tr()

        # End section
        html.open_tr()
        html.open_td()
        html.write_text(_("End"))
        html.close_td()
        html.open_td()
        self._vs_date().render_input("_down_to_date", time.strftime("%Y-%m-%d"))
        default_endtime: float = time.time() + 7200
        self._vs_time().render_input(
            "_down_to_time", time.strftime("%H:%M", time.localtime(default_endtime))
        )
        html.span(
            timezone_utc_offset_str(default_endtime) + " " + _("Server time"),
            class_="server_time",
        )
        html.close_td()

        # Repeat section
        html.open_tr()
        html.open_td()
        html.write_text(_("Repeat"))
        html.close_td()
        html.open_td()
        self.recurring_downtimes.show_input_elements(default="0")

        html.close_td()

        html.close_table()
        html.close_div()

    def _get_duration_options(self) -> HTML:
        duration_options = HTML("")
        for nr, time_range in enumerate(active_config.user_downtime_timeranges):
            css_class = ["button", "duration"]
            time_range_end = time_range["end"]
            if nr == 0:
                end_time = time_interval_end(time_range_end, self._current_local_time())
                html.final_javascript(
                    f'cmk.utils.update_time("date__down_to_date","{time.strftime("%Y-%m-%d",time.localtime(end_time))}");'
                )
                html.final_javascript(
                    f'cmk.utils.update_time("time__down_to_time","{time.strftime("%H:%M", time.localtime(end_time))}");'
                )
                css_class += ["active"]

            duration_options += html.render_input(
                name=(varname := f'_downrange__{time_range["end"]}'),
                type_="button",
                id_=varname,
                class_=css_class,
                value=_u(time_range["title"]),
                onclick=self._get_onclick(time_range_end, varname),
                submit="_set_date_and_time",
            )
        return duration_options

    def _get_presets_url(self) -> str:
        return makeuri_contextless(
            request,
            [("mode", "edit_configvar"), ("varname", "user_downtime_timeranges")],
            filename="wato.py",
        )

    def _vs_date(self) -> DatePicker:
        return DatePicker(
            title=_("Downtime date picker"),
            onchange="cmk.page_menu.update_down_duration_button();",
        )

    def _vs_time(self) -> TimePicker:
        return TimePicker(
            title=_("Downtime time picker"),
            onchange="cmk.page_menu.update_down_duration_button();",
        )

    def _get_onclick(
        self,
        time_range_end: int | Literal["next_day", "next_week", "next_month", "next_year"],
        id_: str,
    ) -> str:
        start_time = self._current_local_time()
        end_time = time_interval_end(time_range_end, start_time)

        return (
            f'cmk.page_menu.update_down_duration_button("{id_}");'
            f'cmk.utils.update_time("date__down_from_date","{time.strftime("%Y-%m-%d",time.localtime(start_time))}");'
            f'cmk.utils.update_time("time__down_from_time","{time.strftime("%H:%M",time.localtime(start_time))}");'
            f'cmk.utils.update_time("date__down_to_date","{time.strftime("%Y-%m-%d",time.localtime(end_time))}");'
            f'cmk.utils.update_time("time__down_to_time","{time.strftime("%H:%M", time.localtime(end_time))}");'
        )

    def _render_advanced_options(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.open_div(class_="down_advanced")
        with foldable_container(
            treename="advanced_down_options",
            id_="adv_down_opts",
            isopen=False,
            title=_("Advanced options"),
            indent=False,
        ):
            html.open_div(class_="down_advanced_option")
            if what == "host":
                self._vs_host_downtime().render_input("_include_children", None)

            self._vs_flexible_options().render_input("_down_duration", None)
            html.close_div()

        html.close_div()
        html.close_div()

    def _render_confirm_buttons(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        tooltip_submission_disabled = _("Enter a comment to schedule downtime")

        is_service = what == "service"

        if is_service:
            open_submit_button_container_div(tooltip=tooltip_submission_disabled)
            html.button(
                "_down_service", _("On service: Schedule downtime"), cssclass="hot disabled"
            )
            html.close_div()

        open_submit_button_container_div(tooltip=tooltip_submission_disabled)
        if what == "host" or user.may("general.see_all") or hosts_user_can_see():
            html.button(
                "_down_host",
                _("On host: Schedule downtime"),
                cssclass="disabled" + ("" if is_service else " hot"),
            )
        html.close_div()

        html.buttonlink(makeuri(request, [], delvars=["filled_in"]), _("Cancel"))
        html.close_div()

    def _vs_host_downtime(self) -> Dictionary:
        return Dictionary(
            title="Host downtime options",
            elements=[
                (
                    "_include_children",
                    Checkbox(
                        title=_("Only for hosts: Set child hosts in downtime"),
                        label=_("Include indirectly connected hosts (recursively)"),
                    ),
                ),
            ],
        )

    def _vs_flexible_options(self) -> Dictionary:
        return Dictionary(
            title=_("Flexible downtime options"),
            elements=[
                (
                    "_down_duration",
                    Age(
                        display=["hours", "minutes"],
                        title=_(
                            "Only start downtime if host/service goes "
                            "DOWN/UNREACH during the defined start and end time "
                            "(flexible)"
                        ),
                        cssclass="inline",
                        label=_("Max. duration after downtime starts: "),
                        footer="<b>"
                        + _("Warning: ")
                        + "</b>"
                        + _("Downtime can extend beyond the previously defined end date and time"),
                        default_value=7200,
                    ),
                ),
            ],
        )

    def _action(  # pylint: disable=too-many-arguments
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        """Prepares the livestatus command for any received downtime information through WATO"""
        recurring_number = self.recurring_downtimes.number()
        if request.var("_down_host", request.var("_down_service", request.var("_down_adhoc"))):
            if request.var("_down_adhoc"):
                start_time = self._current_local_time()
                end_time = self._get_adhoc_end_time(start_time)
            else:
                start_time = self._custom_start_time()
                end_time = self._custom_end_time(start_time)

            if recurring_number == 8 and not 1 <= time.localtime(start_time).tm_mday <= 28:
                raise MKUserError(
                    None,
                    _(
                        "The start of a recurring downtime can only be set for "
                        "days 1-28 of a month."
                    ),
                )

            comment = self._comment()
            delayed_duration = self._flexible_option()
            mode = determine_downtime_mode(recurring_number, delayed_duration)
            downtime = DowntimeSchedule(start_time, end_time, mode, delayed_duration, comment)
            cmdtag, specs, len_action_rows = self._downtime_specs(cmdtag, row, action_rows, spec)
            if "aggr_tree" in row:  # BI mode
                node = row["aggr_tree"]
                return (
                    _bi_commands(downtime, node),
                    self.confirm_dialog_options(
                        cmdtag,
                        row,
                        len(action_rows),
                    ),
                )
            return (
                [downtime.livestatus_command(spec_, cmdtag) for spec_ in specs],
                self._confirm_dialog_options(
                    cmdtag,
                    row,
                    len_action_rows,
                    _("Schedule a downtime?"),
                ),
            )

        return None

    def _confirm_dialog_options(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
        title: str,
    ) -> CommandConfirmDialogOptions:
        return CommandConfirmDialogOptions(
            title,
            self.affected(len_action_rows, cmdtag),
            self.confirm_dialog_additions(cmdtag, row, len_action_rows),
            self.confirm_dialog_icon_class(),
            self.confirm_button,
            self.cancel_button,
            self.deny_button,
            self.deny_js_function,
        )

    def _get_adhoc_end_time(self, start_time: float) -> float:
        return start_time + active_config.adhoc_downtime.get("duration", 0) * 60

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
    ) -> HTML:
        start_at = self._custom_start_time()
        additions = HTMLWriter.render_table(
            HTMLWriter.render_tr(
                HTMLWriter.render_td(_("Start:"))
                + HTMLWriter.render_td(self.confirm_dialog_date_and_time_format(start_at))
            )
            + HTMLWriter.render_tr(
                HTMLWriter.render_td(_("End:"))
                + HTMLWriter.render_td(
                    self.confirm_dialog_date_and_time_format(
                        self._get_adhoc_end_time(start_at)
                        if request.var("_down_adhoc")
                        else self._custom_end_time(start_at)
                    )
                )
            )
        )

        attributes = HTML("")
        if recurring_number_from_html := self.recurring_downtimes.number():
            attributes += HTMLWriter.render_li(
                _("Repeats every %s")
                % self.recurring_downtimes.choices()[recurring_number_from_html][1]
            )

        vs_host_downtime = self._vs_host_downtime()
        included_from_html = vs_host_downtime.from_html_vars("_include_children")
        vs_host_downtime.validate_value(included_from_html, "_include_children")
        if "_include_children" in included_from_html:
            if included_from_html.get("_include_children") is True:
                attributes += HTMLWriter.render_li(
                    _("Child hosts also go in downtime (recursively).")
                )
            else:
                attributes += HTMLWriter.render_li(_("Child hosts also go in downtime."))

        if duration := self._flexible_option():
            hours, remaining_seconds = divmod(duration, 3600)
            minutes, _seconds = divmod(remaining_seconds, 60)
            attributes += HTMLWriter.render_li(
                _(
                    "Starts if host/service goes DOWN/UNREACH with a max. duration of %d hours and %d %s."
                )
                % (
                    hours,
                    minutes,
                    ungettext(
                        "minute",
                        "minutes",
                        minutes,
                    ),
                )
            )

        if attributes:
            additions = (
                additions
                + HTMLWriter.render_p(_("Downtime attributes:"))
                + HTMLWriter.render_ul(attributes)
            )

        return additions + HTMLWriter.render_p(
            _("<u>Info</u>: Downtime also applies to all services of the %s.")
            % ungettext(
                "host",
                "hosts",
                len_action_rows,
            )
            if cmdtag == "HOST"
            else _("<u>Info</u>: Downtime does not apply to host.")
        )

    def _flexible_option(self) -> int:
        vs_flexible_options = self._vs_flexible_options()
        duration_from_html = vs_flexible_options.from_html_vars("_down_duration")
        vs_flexible_options.validate_value(duration_from_html, "_down_duration")
        if duration_from_html:
            self._vs_duration().validate_value(
                duration := duration_from_html.get("_down_duration", 0),
                "_down_duration",
            )
            delayed_duration = duration
        else:
            delayed_duration = 0
        return delayed_duration

    def _comment(self):
        comment = (
            active_config.adhoc_downtime.get("comment", "")
            if request.var("_down_adhoc")
            else request.get_str_input("_down_comment")
        )
        if not comment:
            raise MKUserError("_down_comment", _("You need to supply a comment for your downtime."))
        return comment

    def _current_local_time(self):
        return time.time()

    def _custom_start_time(self):
        vs_date = self._vs_date()
        raw_start_date = vs_date.from_html_vars("_down_from_date")
        vs_date.validate_value(raw_start_date, "_down_from_date")

        vs_time = self._vs_time()
        raw_start_time = vs_time.from_html_vars("_down_from_time")
        vs_time.validate_value(raw_start_time, "_down_from_time")

        down_from = time.mktime(
            time.strptime(f"{raw_start_date} {raw_start_time}", "%Y-%m-%d %H:%M")
        )
        self._vs_down_from().validate_value(down_from, "_down_from")
        return down_from

    def _custom_end_time(self, start_time):
        vs_date = self._vs_date()
        raw_end_date = vs_date.from_html_vars("_down_to_date")
        vs_date.validate_value(raw_end_date, "_down_to_date")

        vs_time = self._vs_time()
        raw_end_time = vs_time.from_html_vars("_down_to_time")
        vs_time.validate_value(raw_end_time, "_down_to_time")

        end_time = time.mktime(time.strptime(f"{raw_end_date} {raw_end_time}", "%Y-%m-%d %H:%M"))
        self._vs_down_to().validate_value(end_time, "_down_to")

        if end_time < time.time():
            raise MKUserError(
                "_down_to",
                _(
                    "You cannot set a downtime that ends in the past. "
                    "This incident will be reported."
                ),
            )

        if end_time < start_time:
            raise MKUserError("_down_to", _("Your end date is before your start date."))

        return end_time

    def _downtime_specs(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        action_rows: Rows,
        spec: str,
    ) -> tuple[Literal["HOST", "SVC"], list[str], int]:
        len_action_rows = len(action_rows)

        vs_host_downtime = self._vs_host_downtime()
        included_from_html = vs_host_downtime.from_html_vars("_include_children")
        vs_host_downtime.validate_value(included_from_html, "_include_children")

        # INFO: it's necessary to check if a downtime command originates from the "All aggregations"
        # view in BI because its "Row" payload differs from that of the "Host" and "Service" views.
        downtime_from_bi_aggregation = "aggr_hosts" in row

        if "_include_children" in included_from_html:  # only for hosts
            if (recurse := included_from_html.get("_include_children")) is not None:
                specs = [spec] + self._get_child_hosts(row["site"], [spec], recurse=recurse)
        elif request.var("_down_host"):  # set on hosts instead of services
            specs = [spec.split(";")[0]]
            cmdtag = "HOST"
            if not user.may("general.see_all"):
                user_hosts = hosts_user_can_see(
                    users_sites=list({livestatus.SiteId(row["site"]) for row in action_rows})
                )
                specs = [spec for spec in specs if spec in user_hosts]
                if downtime_from_bi_aggregation:
                    action_rows = [
                        ar
                        for ar in action_rows
                        if all(host[1] in user_hosts for host in ar["aggr_hosts"])
                    ]
                else:
                    action_rows = [ar for ar in action_rows if ar["host_name"] in user_hosts]

            if downtime_from_bi_aggregation:
                unique_hosts = {hostname for ar in action_rows for _, hostname in ar["aggr_hosts"]}
            else:
                unique_hosts = {ar["host_name"] for ar in action_rows}

            len_action_rows = len(unique_hosts)
        else:
            specs = [spec]
        return cmdtag, specs, len_action_rows

    def _vs_down_from(self) -> AbsoluteDate:
        return AbsoluteDate(
            title=_("From"),
            include_time=True,
            submit_form_name="_down_custom",
        )

    def _vs_down_to(self) -> AbsoluteDate:
        return AbsoluteDate(
            title=_("Until"),
            include_time=True,
            submit_form_name="_down_custom",
        )

    def _vs_duration(self) -> Age:
        return Age(
            display=["hours", "minutes"],
            title=_("Duration"),
            cssclass="inline",
        )

    def _get_child_hosts(self, site, hosts, recurse):
        hosts = set(hosts)

        sites.live().set_only_sites([site])
        query = "GET hosts\nColumns: name\n"
        query += "".join([f"Filter: parents >= {host}\n" for host in hosts])
        query += f"Or: {len(hosts)}\n"
        children = sites.live().query_column(query)
        sites.live().set_only_sites(None)

        # Recursion, but try to avoid duplicate work
        new_children = set(children) - hosts
        if new_children and recurse:
            rec_childs = self._get_child_hosts(site, new_children, True)
            new_children.update(rec_childs)
        return list(new_children)

    def _adhoc_downtime_configured(self) -> bool:
        return bool(active_config.adhoc_downtime and active_config.adhoc_downtime.get("duration"))


def _bi_commands(downtime: DowntimeSchedule, node: Any) -> Sequence[CommandSpec]:
    """Generate the list of downtime command strings for the BI module"""
    commands_aggr = []
    for site, host, service in _find_all_leaves(node):
        if service:
            spec = f"{host};{service}"
            cmdtag: Literal["HOST", "SVC"] = "SVC"
        else:
            spec = host
            cmdtag = "HOST"
        commands_aggr.append((site, downtime.livestatus_command(spec, cmdtag)))
    return commands_aggr


def _find_all_leaves(  # type: ignore[no-untyped-def]
    node,
) -> list[tuple[livestatus.SiteId | None, HostName, ServiceName | None]]:
    # leaf node
    if node["type"] == 1:
        site, host = node["host"]
        return [(livestatus.SiteId(site), host, node.get("service"))]

    # rule node
    if node["type"] == 2:
        entries: list[Any] = []
        for n in node["nodes"]:
            entries += _find_all_leaves(n)
        return entries

    # place holders
    return []


def time_interval_end(
    time_value: int | Literal["next_day", "next_week", "next_month", "next_year"],
    start_time: float,
) -> float | None:
    now = time.localtime(start_time)
    if isinstance(time_value, int):
        return start_time + time_value
    if time_value == "next_day":
        return (
            time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 23, 59, 59, 0, 0, now.tm_isdst)) + 1
        )
    if time_value == "next_week":
        wday = now.tm_wday
        days_plus = 6 - wday
        res = (
            time.mktime((now.tm_year, now.tm_mon, now.tm_mday, 23, 59, 59, 0, 0, now.tm_isdst)) + 1
        )
        res += days_plus * 24 * 3600
        return res
    if time_value == "next_month":
        new_month = now.tm_mon + 1
        if new_month == 13:
            new_year = now.tm_year + 1
            new_month = 1
        else:
            new_year = now.tm_year
        return time.mktime((new_year, new_month, 1, 0, 0, 0, 0, 0, now.tm_isdst))
    if time_value == "next_year":
        return time.mktime((now.tm_year, 12, 31, 23, 59, 59, 0, 0, now.tm_isdst)) + 1
    return None


def time_interval_to_human_readable(next_time_interval, prefix):
    """Generate schedule downtime text from next time interval information

    Args:
        next_time_interval:
            string representing the next time interval. Can either be a periodic interval or the
            duration value
        prefix:
            prefix for the downtime title

    Examples:
        >>> time_interval_to_human_readable("next_day", "schedule an immediate downtime")
        '<b>schedule an immediate downtime until 24:00:00</b>?'
        >>> time_interval_to_human_readable("next_year", "schedule an immediate downtime")
        '<b>schedule an immediate downtime until end of year</b>?'

    Returns:
        string representing the schedule downtime title
    """
    downtime_titles = {
        "next_day": _("<b>%s until 24:00:00</b>?"),
        "next_week": _("<b>%s until sunday night</b>?"),
        "next_month": _("<b>%s until end of month</b>?"),
        "next_year": _("<b>%s until end of year</b>?"),
    }
    try:
        title = downtime_titles[next_time_interval]
    except KeyError:
        duration = int(next_time_interval)
        title = _("<b>%%s of %s length</b>?") % SecondsRenderer.detailed_str(duration)
    return title % prefix


class CommandRemoveDowntime(Command):
    @property
    def ident(self) -> str:
        return "remove_downtimes"

    @property
    def title(self) -> str:
        return _("Remove downtimes")

    @property
    def confirm_title(self) -> str:
        return _("Remove downtimes?")

    @property
    def confirm_button(self) -> LazyString:
        return _l("Remove")

    @property
    def permission(self) -> Permission:
        return PermissionActionDowntimes

    @property
    def group(self) -> type[CommandGroup]:
        return CommandGroupDowntimes

    @property
    def tables(self):
        return ["host", "service", "downtime"]

    # we only want to show the button and shortcut in the explicit downtime
    # view
    @property
    def is_shortcut(self) -> bool:
        return self.is_suggested

    @property
    def is_suggested(self) -> bool:
        return request.var("view_name", "") in [
            "downtimes",
            "downtimes_of_host",
            "downtimes_of_service",
        ]

    def _confirm_dialog_options(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
        title: str,
    ) -> CommandConfirmDialogOptions:
        return CommandConfirmDialogOptions(
            title,
            self.affected(len_action_rows, cmdtag),
            self.confirm_dialog_additions(cmdtag, row, len_action_rows),
            self.confirm_dialog_icon_class(),
            self.confirm_button,
            self.cancel_button,
            self.deny_button,
            self.deny_js_function,
        )

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.button("_remove_downtimes", _("Remove"))

    def _action(  # pylint: disable=too-many-arguments
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if request.has_var("_remove_downtimes"):
            if "downtime_id" in row:
                return self._rm_downtime_from_downtime_datasource(cmdtag, spec, row, action_rows)
            return self._rm_downtime_from_hst_or_svc_datasource(cmdtag, row, action_rows)
        return None

    def _rm_downtime_from_downtime_datasource(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        action_rows: Rows,
    ) -> CommandActionResult:
        return (
            f"DEL_{cmdtag}_DOWNTIME;{spec}",
            self.confirm_dialog_options(
                cmdtag,
                row,
                len(action_rows),
            ),
        )

    def _rm_downtime_from_hst_or_svc_datasource(
        self, cmdtag: Literal["HOST", "SVC"], row: Row, action_rows: Rows
    ) -> tuple[list[str], CommandConfirmDialogOptions] | None:
        if not user.may("action.remove_all_downtimes"):
            return None

        downtime_ids = []
        if cmdtag == "HOST":
            prefix = "host_"
        else:
            prefix = "service_"
        for id_ in row[prefix + "downtimes"]:
            if id_ != "":
                downtime_ids.append(int(id_))
        commands = []
        for dtid in downtime_ids:
            commands.append(f"DEL_{cmdtag}_DOWNTIME;{dtid}\n")
        title = _("Remove scheduled downtimes?")
        return commands, self._confirm_dialog_options(
            cmdtag,
            row,
            len(action_rows),
            title,
        )


@request_memoize()
def _ack_host_comments() -> set[str]:
    return {
        str(comment)
        for comment in sites.live().query_column(
            "GET comments\n"
            "Columns: comment_id\n"
            "Filter: is_service = 0\n"
            "Filter: entry_type = 4"
        )
    }


@request_memoize()
def _ack_service_comments() -> set[str]:
    return {
        str(comment)
        for comment in sites.live().query_column(
            "GET comments\n"
            "Columns: comment_id\n"
            "Filter: is_service = 1\n"
            "Filter: entry_type = 4"
        )
    }


def _acknowledgement_needs_removal(
    cmdtag: Literal["HOST", "SVC"], comments_to_be_removed: set[str]
) -> bool:
    return (cmdtag == "HOST" and _ack_host_comments().issubset(comments_to_be_removed)) or (
        cmdtag == "SVC" and _ack_service_comments().issubset(comments_to_be_removed)
    )


class CommandRemoveComments(Command):
    @property
    def ident(self) -> str:
        return "remove_comments"

    @property
    def title(self) -> str:
        return _("Delete comments")

    @property
    def confirm_title(self) -> str:
        return "%s?" % self.title

    @property
    def confirm_button(self) -> LazyString:
        return _l("Delete")

    @property
    def is_shortcut(self) -> bool:
        return True

    @property
    def is_suggested(self) -> bool:
        return True

    @property
    def permission(self) -> Permission:
        return PermissionActionAddComment

    @property
    def tables(self):
        return ["comment"]

    def affected(self, len_action_rows: int, cmdtag: Literal["HOST", "SVC"]) -> HTML:
        return HTML("")

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
    ) -> HTML:
        if len_action_rows > 1:
            return HTML(_("Total comments: %d") % len_action_rows)
        return HTML(_("Author: %s") % row["comment_author"])

    def render(self, what) -> None:  # type: ignore[no-untyped-def]
        html.open_div(class_="group")
        html.button("_delete_comments", _("Delete"), cssclass="hot")
        html.button("_cancel", _("Cancel"))
        html.close_div()

    def _action(
        self,
        cmdtag: Literal["HOST", "SVC"],
        spec: str,
        row: Row,
        row_index: int,
        action_rows: Rows,
    ) -> CommandActionResult:
        if not request.has_var("_delete_comments"):
            return None
        # NOTE: To remove an acknowledgement, we have to use the specialized command, not only the
        # general one. The latter one only removes the comment itself, not the "acknowledged" state.
        # NOTE: We get the commend ID (an int) as a str via the spec parameter (why???), but we need
        # the specification of the host or service for REMOVE_FOO_ACKNOWLEDGEMENT.
        commands = []
        if row.get("comment_entry_type") == 4:  # an acknowledgement
            # NOTE: REMOVE_FOO_ACKNOWLEDGEMENT removes all non-persistent acknowledgement comments.
            # This means if we remove some acknowledgement comments, we should only fire
            # REMOVE_FOO_ACKNOWLEDGEMENT if there are no other acknowledgement comments left.
            comments_to_be_removed = {str(r["comment_id"]) for r in action_rows}
            if _acknowledgement_needs_removal(cmdtag, comments_to_be_removed):
                if cmdtag == "HOST":
                    rm_ack = f"REMOVE_HOST_ACKNOWLEDGEMENT;{row['host_name']}"
                else:
                    rm_ack = f"REMOVE_SVC_ACKNOWLEDGEMENT;{row['host_name']};{row['service_description']}"
                commands.append(rm_ack)
        # Nevertheless, we need the general command, too, even for acknowledgements: The
        # acknowledgement might be persistent, so REMOVE_FOO_ACKNOWLEDGEMENT leaves the comment
        # itself, that's the whole point of being persistent. The only way to get rid of such a
        # comment is via DEL_FOO_COMMENT.
        del_cmt = f"DEL_HOST_COMMENT;{spec}" if cmdtag == "HOST" else f"DEL_SVC_COMMENT;{spec}"
        commands.append(del_cmt)
        return commands, self.confirm_dialog_options(
            cmdtag,
            row,
            len(action_rows),
        )
