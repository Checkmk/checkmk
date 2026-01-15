#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from collections.abc import Sequence
from typing import Literal, Protocol

import livestatus

import cmk.ccc.version as cmk_version

from cmk.utils import paths
from cmk.utils.hostaddress import HostName
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables.hosts import Hosts
from cmk.utils.servicename import ServiceName

from cmk.gui import sites
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
from cmk.gui.utils import escaping
from cmk.gui.utils.html import HTML
from cmk.gui.utils.time import timezone_utc_offset_str
from cmk.gui.utils.urls import makeuri, makeuri_contextless
from cmk.gui.valuespec import AbsoluteDate, Age, Checkbox, DatePicker, Dictionary, TimePicker
from cmk.gui.view_utils import render_cre_upgrade_button
from cmk.gui.watolib.downtime import determine_downtime_mode, DowntimeSchedule

from cmk.bi.trees import CompiledAggrLeaf, CompiledAggrRule, CompiledAggrTree

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
    command_registry.register(
        CommandScheduleDowntimes(
            recurring_downtimes=NoRecurringDowntimes(),
        )
    )
    command_registry.register(CommandRemoveDowntimesHostServicesTable)
    command_registry.register(CommandRemoveDowntimesDowntimesTable)
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


def command_reschedule_confirm_dialog_additions(
    cmdtag: Literal["HOST", "SVC"],
    row: Row,
    action_rows: Rows,
) -> HTML:
    return (
        HTMLWriter.render_br()
        + HTMLWriter.render_br()
        + "Spreading: %s minutes" % request.var("_resched_spread")
    )


def command_reschedule_render(what: str) -> None:
    html.open_div(class_="group")
    html.write_text_permissive(_("Spread over") + " ")
    html.text_input("_resched_spread", default_value="5", size=3, cssclass="number", required=True)
    html.write_text_permissive(" " + _("minutes"))
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


def command_reschedule_action(
    command: Command,
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
                "_resched_spread", _("Spread should be a positive number: %s") % spread
            )

        t = time.time()
        if spread:
            t += spread * 60.0 * row_index / len(action_rows)

        cmd = "SCHEDULE_FORCED_" + cmdtag + "_CHECK;%s;%d" % (spec, int(t))
        return cmd, command.confirm_dialog_options(
            cmdtag,
            row,
            action_rows,
        )
    return None


CommandReschedule = Command(
    ident="reschedule",
    title=_l("Reschedule active checks"),
    confirm_title=_l("Reschedule active checks immediately?"),
    confirm_button=_l("Reschedule"),
    permission=PermissionActionReschedule,
    group=CommandGroupVarious,
    tables=["host", "service"],
    icon_name="service_duration",
    render=command_reschedule_render,
    action=command_reschedule_action,
    confirm_dialog_additions=command_reschedule_confirm_dialog_additions,
)


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


def command_notifications_confirm_dialog_additions(
    cmdtag: Literal["HOST", "SVC"],
    row: Row,
    action_rows: Rows,
) -> HTML:
    return (
        HTMLWriter.render_br()
        + HTMLWriter.render_br()
        + (
            _("Notifications will be sent according to the notification rules")
            if request.var("_enable_notifications")
            else _("This will suppress all notifications")
        )
    )


def command_notifications_confirm_dialog_icon_class() -> Literal["question", "warning"]:
    if request.var("_enable_notifications"):
        return "question"
    return "warning"


def command_notifications_render(what: str) -> None:
    html.open_div(class_="group")
    html.button("_enable_notifications", _("Enable"), cssclass="border_hot")
    html.button("_disable_notifications", _("Disable"), cssclass="border_hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_notifications_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if request.var("_enable_notifications"):
        return (
            "ENABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    if request.var("_disable_notifications"):
        return (
            "DISABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    return None


CommandNotifications = Command(
    ident="notifications",
    title=_l("Enable/disable notifications"),
    confirm_title=lambda: (
        _l("Enable notifications?")
        if request.var("_enable_notifications")
        else _l("Disable notifications?")
    ),
    confirm_button=lambda: _l("Enable") if request.var("_enable_notifications") else _l("Disable"),
    permission=PermissionActionNotifications,
    tables=["host", "service"],
    group=CommandGroupVarious,
    confirm_dialog_additions=command_notifications_confirm_dialog_additions,
    confirm_dialog_icon_class=command_notifications_confirm_dialog_icon_class,
    render=command_notifications_render,
    action=command_notifications_action,
)

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


def command_toggle_active_checks_render(what: str) -> None:
    html.open_div(class_="group")
    html.button("_enable_checks", _("Enable"), cssclass="border_hot")
    html.button("_disable_checks", _("Disable"), cssclass="border_hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_toggle_active_checks_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if request.var("_enable_checks"):
        return (
            "ENABLE_" + cmdtag + "_CHECK;%s" % spec,
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    if request.var("_disable_checks"):
        return (
            "DISABLE_" + cmdtag + "_CHECK;%s" % spec,
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    return None


CommandToggleActiveChecks = Command(
    ident="toggle_active_checks",
    title=_l("Enable/Disable active checks"),
    confirm_title=lambda: (
        _l("Enable active checks") if request.var("_enable_checks") else _l("Disable active checks")
    ),
    confirm_button=lambda: _l("Enable") if request.var("_enable_checks") else _l("Disable"),
    permission=PermissionActionEnableChecks,
    group=CommandGroupVarious,
    tables=["host", "service"],
    confirm_dialog_icon_class=lambda: "warning",
    render=command_toggle_active_checks_render,
    action=command_toggle_active_checks_action,
)

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


def command_toggle_passive_checks_render(what: str) -> None:
    html.open_div(class_="group")
    html.button("_enable_passive_checks", _("Enable"), cssclass="border_hot")
    html.button("_disable_passive_checks", _("Disable"), cssclass="border_hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_toggle_passive_checks_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if request.var("_enable_passive_checks"):
        return (
            "ENABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec,
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    if request.var("_disable_passive_checks"):
        return (
            "DISABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec,
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    return None


CommandTogglePassiveChecks = Command(
    ident="toggle_passive_checks",
    title=_l("Enable/Disable passive checks"),
    confirm_title=lambda: (
        _l("Enable passive checks")
        if request.var("_enable_passive_checks")
        else _l("Disable passive checks")
    ),
    confirm_button=lambda: _l("Enable") if request.var("_enable_passive_checks") else _l("Disable"),
    permission=PermissionActionEnableChecks,
    group=CommandGroupVarious,
    tables=["host", "service"],
    confirm_dialog_icon_class=lambda: "warning",
    render=command_toggle_passive_checks_render,
    action=command_toggle_passive_checks_action,
)

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


def command_clear_modified_attributes_render(what: str) -> None:
    html.open_div(class_="group")
    html.button("_clear_modattr", _("Reset attributes"), cssclass="hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_clear_modified_attributes_confirm_dialog_additions(
    cmdtag: Literal["HOST", "SVC"],
    row: Row,
    action_rows: Rows,
) -> HTML:
    return (
        HTMLWriter.render_br()
        + HTMLWriter.render_br()
        + _("Resets the commands '%s', '%s' and '%s' to the default state")
        % (
            CommandToggleActiveChecks.title,
            CommandTogglePassiveChecks.title,
            CommandNotifications.title,
        )
    )


def command_clear_modified_attributes_action(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if request.var("_clear_modattr"):
        return (
            "CHANGE_" + cmdtag + "_MODATTR;%s;0" % spec,
            command.confirm_dialog_options(cmdtag, row, action_rows),
        )
    return None


CommandClearModifiedAttributes = Command(
    ident="clear_modified_attributes",
    title=_l("Reset modified attributes"),
    confirm_button=_l("Reset"),
    permission=PermissionActionClearModifiedAttributes,
    group=CommandGroupVarious,
    tables=["host", "service"],
    render=command_clear_modified_attributes_render,
    action=command_clear_modified_attributes_action,
    confirm_dialog_additions=command_clear_modified_attributes_confirm_dialog_additions,
)

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


def _get_target_state() -> str:
    state = request.var("_state")
    statename = request.var(f"_state_{state}")

    return "" if statename is None else statename


def command_fake_check_result_render(what: str) -> None:
    _render_test_notification_tip()

    html.open_div(class_="group")
    html.open_table(class_=["fake_check_result"])

    html.open_tr()
    html.open_td()
    html.write_text_permissive(_("Result") + " &nbsp; ")
    html.close_td()
    html.open_td()
    html.open_span(class_="inline_radio_group")
    for value, description in _get_states(what):
        html.radiobutton("_state", str(value), value == 0, description)
        html.hidden_field(f"_state_{value}", description)
    html.close_span()
    html.close_td()
    html.close_tr()

    html.open_tr()
    html.open_td()
    html.write_text_permissive(_("Plug-in output") + " &nbsp; ")
    html.close_td()
    html.open_td()
    html.text_input("_fake_output", "", size=60, placeholder=_("What is the purpose?"))
    html.close_td()
    html.close_tr()

    html.open_tr()
    html.open_td()
    html.write_text_permissive(_("Performance data") + " &nbsp; ")
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


def _link_to_test_notifications() -> HTML:
    return html.render_a(
        _("Test notification"),
        makeuri_contextless(request, [("mode", "test_notifications")], filename="wato.py"),
    )


def _render_test_notification_tip() -> None:
    html.open_div(class_="info")
    html.icon("toggle_details")
    html.write_text_permissive(
        " &nbsp; "
        + _(
            "If you are looking for a way to test your notification settings, try '%s' in Setup > Test notifications"
        )
        % _link_to_test_notifications()
    )
    html.close_div()


def _get_states(what: str) -> list[tuple[int, str]]:
    if what == "host":
        return [(0, _("Up")), (1, _("Down"))]

    return [(0, _("OK")), (1, _("Warning")), (2, _("Critical")), (3, _("Unknown"))]


def command_fake_check_result_action(
    command: Command,
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

        cmd = "PROCESS_{}_CHECK_RESULT;{};{};{}".format(
            "SERVICE" if cmdtag == "SVC" else cmdtag,
            spec,
            state,
            livestatus.lqencode(pluginoutput),
        )

        return cmd, command.confirm_dialog_options(cmdtag, row, action_rows)

    return None


CommandFakeCheckResult = Command(
    ident="fake_check_result",
    title=_l("Fake check results"),
    confirm_title=lambda: _l("Set fake check result to ‘%s’?") % _get_target_state(),
    confirm_button=lambda: _l("Set to '%s'") % _get_target_state(),
    permission=PermissionActionFakeChecks,
    tables=["host", "service"],
    group=CommandGroupFakeCheck,
    icon_name="fake_check_result",
    is_show_more=True,
    render=command_fake_check_result_render,
    action=command_fake_check_result_action,
)


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


def command_custom_notification_render(what: str) -> None:
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


def command_custom_notification_action(
    command: Command,
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
        cmd = f"SEND_CUSTOM_{cmdtag}_NOTIFICATION;{spec};{broadcast + forced};{user.id};{livestatus.lqencode(comment)}"
        return cmd, command.confirm_dialog_options(cmdtag, row, action_rows)
    return None


CommandCustomNotification = Command(
    ident="send_custom_notification",
    title=_l("Send custom notification"),
    confirm_title=_l("Send custom notification?"),
    confirm_button=_l("Send"),
    icon_name="notifications",
    permission=PermissionActionCustomNotification,
    group=CommandGroupVarious,
    tables=["host", "service"],
    is_show_more=True,
    render=command_custom_notification_render,
    action=command_custom_notification_action,
)

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


def command_acknowledge_confirm_dialog_additions(
    cmdtag: Literal["HOST", "SVC"],
    row: Row,
    action_rows: Rows,
) -> HTML:
    if request.var("_ack_expire"):
        date = request.get_str_input("_ack_expire_date")
        time_ = request.get_str_input("_ack_expire_time")
        timestamp = time.mktime(time.strptime(f"{date} {time_}", "%Y-%m-%d %H:%M"))
        formatted_datetime_str = _confirm_dialog_date_and_time_format(timestamp)

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


def command_acknowledge_render(what: str) -> None:
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
        html.write_text_permissive("(")
        html.a(_("Edit defaults"), _action_defaults_url())
        html.write_text_permissive(")")
        html.close_span()

    date, time_ = _expiration_date_and_time(
        active_config.acknowledge_problems.get("ack_expire", 3600)
    )
    is_raw_edition: bool = cmk_version.edition(paths.omd_root) is cmk_version.Edition.CRE
    html.open_div(class_="disabled" if is_raw_edition else "")
    html.checkbox(
        "_ack_expire",
        False,
        label=_("Expire on"),
        onclick="cmk.page_menu.ack_problems_update_expiration_active_state(this);",
    )
    html.open_div(class_="date_time_picker")
    _vs_date().render_input("_ack_expire_date", date)
    _vs_time().render_input("_ack_expire_time", time_)
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
            % _link_to_notification_rules(),
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


def _action_defaults_url() -> str:
    return makeuri_contextless(
        request,
        [("mode", "edit_configvar"), ("varname", "acknowledge_problems")],
        filename="wato.py",
    )


def _link_to_notification_rules() -> HTML:
    return html.render_a(
        _("notification rules"),
        makeuri_contextless(request, [("mode", "notifications")], filename="wato.py"),
    )


def _expiration_date_and_time(time_until_exp: int) -> tuple[str, str]:
    exp_time = time.localtime(time.time() + time_until_exp)
    return time.strftime("%Y-%m-%d", exp_time), time.strftime("%H:%M", exp_time)


def command_acknowledge_action(  # pylint: disable=too-many-branches
    command: Command,
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
            expire_date = _vs_date().from_html_vars("_ack_expire_date")
            expire_time = _vs_time().from_html_vars("_ack_expire_time")
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
            commands = [(site, make_command_ack(spec_, cmdtag_)) for site, spec_, cmdtag_ in specs]
        else:
            commands = [make_command_ack(spec, cmdtag)]

        return commands, command.confirm_dialog_options(cmdtag, row, action_rows)

    return None


CommandAcknowledge = Command(
    ident="acknowledge",
    title=_l("Acknowledge problems"),
    confirm_title=_l("Acknowledge problems?"),
    confirm_button=_l("Yes, acknowledge"),
    cancel_button=_l("No, discard"),
    deny_button=_l("No, adjust settings"),
    deny_js_function='() => cmk.page_menu.toggle_popup("popup_command_acknowledge")',
    icon_name="ack",
    is_shortcut=True,
    is_suggested=True,
    permission=PermissionActionAcknowledge,
    group=CommandGroupAcknowledge,
    tables=["host", "service", "aggr"],
    render=command_acknowledge_render,
    action=command_acknowledge_action,
    confirm_dialog_additions=command_acknowledge_confirm_dialog_additions,
)


def _vs_date() -> DatePicker:
    return DatePicker(
        title=_("Acknowledge problems date picker"),
        onchange="cmk.page_menu.ack_problems_update_expiration_active_state(this);",
    )


def _vs_time() -> TimePicker:
    return TimePicker(
        title=_("Acknowledge problems time picker"),
        onchange="cmk.page_menu.ack_problems_update_expiration_active_state(this);",
    )


def command_remove_acknowledgements_confirm_dialog_additions(
    cmdtag: Literal["HOST", "SVC"],
    row: Row,
    action_rows: Rows,
) -> HTML:
    if (acks := _number_of_acknowledgements(row, action_rows, cmdtag)) is None:
        return HTML.empty()

    return html.render_div(_("Acknowledgments: ") + str(acks))


def command_remove_acknowledgements_action(
    command: Command,
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

    return commands, command.confirm_dialog_options(cmdtag, row, action_rows)


def _number_of_acknowledgements(
    row: Row, action_rows: Rows, cmdtag: Literal["HOST", "SVC"]
) -> int | None:
    # TODO: Can we also find out the number of acknowledgments for BI aggregation rows?
    if "aggr_tree" in row:  # BI mode
        return None

    return len(
        _unique_acknowledgements(action_rows, what="host" if cmdtag == "HOST" else "service")
    )


def _unique_acknowledgements(action_rows: Rows, what: str) -> set[tuple[str, str]]:
    unique_acknowledgments: set[tuple[str, str]] = set()
    for row in action_rows:
        unique_acknowledgments.update(
            {
                # take author and timestamp as unique acknowledgment key
                # comment_spec = [id, author, comment, type, timestamp]
                (comment_spec[1], comment_spec[4])
                for comment_spec in row.get(f"{what}_comments_with_extra_info", [])
            }
        )
    return unique_acknowledgments


CommandRemoveAcknowledgments = Command(
    ident="remove_acknowledgments",
    title=_l("Remove acknowledgments"),
    confirm_title=_l("Remove all acknowledgments?"),
    confirm_button=_l("Remove all"),
    icon_name="ack",
    permission=PermissionActionAcknowledge,
    group=CommandGroupAcknowledge,
    tables=["host", "service", "aggr"],
    show_command_form=False,
    render=lambda _unused: None,
    action=command_remove_acknowledgements_action,
    confirm_dialog_additions=command_remove_acknowledgements_confirm_dialog_additions,
)

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


def command_add_comment_render(what: str) -> None:
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


def command_add_comment_action(
    command: Command,
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
        cmd = (
            "ADD_"
            + cmdtag
            + f"_COMMENT;{spec};1;{user.id}"
            + (";%s" % livestatus.lqencode(comment))
        )
        return cmd, command.confirm_dialog_options(cmdtag, row, action_rows)
    return None


CommandAddComment = Command(
    ident="add_comment",
    title=_l("Add comment"),
    confirm_title=_l("Add comment?"),
    confirm_button=_l("Add"),
    icon_name="comment",
    permission=PermissionActionAddComment,
    tables=["host", "service"],
    group=CommandGroupVarious,
    render=command_add_comment_render,
    action=command_add_comment_action,
)

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
    def __init__(self, recurring_downtimes: RecurringDowntimes) -> None:
        super().__init__(
            ident="schedule_downtimes",
            title=_l("Schedule downtimes"),
            confirm_title=_l("Schedule a downtime?"),
            confirm_button=_l("Yes, schedule"),
            cancel_button=_l("No, discard"),
            deny_button=_l("No, adjust settings"),
            deny_js_function='() => cmk.page_menu.toggle_popup("popup_command_schedule_downtimes")',
            icon_name="downtime",
            is_shortcut=True,
            is_suggested=True,
            permission=PermissionActionDowntimes,
            group=CommandGroupDowntimes,
            tables=["host", "service", "aggr"],
            render=CommandScheduleDowntimesForm(recurring_downtimes).render,
            action=CommandScheduleDowntimesForm(recurring_downtimes).action,
            confirm_dialog_additions=CommandScheduleDowntimesForm(
                recurring_downtimes
            ).confirm_dialog_additions,
        )

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


class CommandScheduleDowntimesForm:
    def __init__(self, recurring_downtimes: RecurringDowntimes) -> None:
        self.recurring_downtimes = recurring_downtimes

    def render(self, what: str) -> None:
        if self._adhoc_downtime_configured():
            self._render_adhoc_comment(what)
        self._render_comment()
        self._render_date_and_time()
        self._render_advanced_options(what)
        self._render_confirm_buttons(what)

    def _render_adhoc_comment(self, what: str) -> None:
        adhoc_duration = active_config.adhoc_downtime.get("duration")
        adhoc_comment = active_config.adhoc_downtime.get("comment", "")
        html.open_div(class_="group")
        html.button("_down_adhoc", _("Ad hoc for %d minutes") % adhoc_duration)
        html.nbsp()
        html.write_text_permissive(_("Comment") + ": " + adhoc_comment)
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
        html.write_text_permissive(_("Start"))
        html.close_td()
        html.open_td()
        _vs_date().render_input("_down_from_date", time.strftime("%Y-%m-%d"))
        _vs_time().render_input("_down_from_time", time.strftime("%H:%M"))
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
        html.write_text_permissive(_("End"))
        html.close_td()
        html.open_td()
        _vs_date().render_input("_down_to_date", time.strftime("%Y-%m-%d"))
        default_endtime: float = time.time() + 7200
        _vs_time().render_input(
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
        html.write_text_permissive(_("Repeat"))
        html.close_td()
        html.open_td()
        self.recurring_downtimes.show_input_elements(default="0")

        html.close_td()

        html.close_table()
        html.close_div()

    def _get_duration_options(self) -> HTML:
        duration_options = HTML.empty()
        for nr, time_range in enumerate(active_config.user_downtime_timeranges):
            css_class = ["button", "duration"]
            time_range_end = time_range["end"]
            if nr == 0:
                end_time = time_interval_end(time_range_end, self._current_local_time())
                html.final_javascript(
                    f'cmk.utils.update_time("date__down_to_date","{time.strftime("%Y-%m-%d", time.localtime(end_time))}");'
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
            f'cmk.utils.update_time("date__down_from_date","{time.strftime("%Y-%m-%d", time.localtime(start_time))}");'
            f'cmk.utils.update_time("time__down_from_time","{time.strftime("%H:%M", time.localtime(start_time))}");'
            f'cmk.utils.update_time("date__down_to_date","{time.strftime("%Y-%m-%d", time.localtime(end_time))}");'
            f'cmk.utils.update_time("time__down_to_time","{time.strftime("%H:%M", time.localtime(end_time))}");'
        )

    def _render_advanced_options(self, what: str) -> None:
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

    def _render_confirm_buttons(self, what: str) -> None:
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

    def action(  # pylint: disable=too-many-arguments
        self,
        command: Command,
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
            cmdtag, specs, action_rows = self._downtime_specs(cmdtag, row, action_rows, spec)
            if "aggr_tree" in row:  # BI mode
                node: CompiledAggrTree = row["aggr_tree"]
                return (
                    _bi_commands(downtime, node),
                    command.confirm_dialog_options(cmdtag, row, action_rows),
                )
            return (
                [downtime.livestatus_command(spec_, cmdtag) for spec_ in specs],
                command.confirm_dialog_options(cmdtag, row, action_rows),
            )

        return None

    def _get_adhoc_end_time(self, start_time: float) -> float:
        return start_time + active_config.adhoc_downtime.get("duration", 0) * 60

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        action_rows: Rows,
    ) -> HTML:
        start_at = self._custom_start_time()
        additions = HTMLWriter.render_table(
            HTMLWriter.render_tr(
                HTMLWriter.render_td(_("Start:"))
                + HTMLWriter.render_td(_confirm_dialog_date_and_time_format(start_at))
            )
            + HTMLWriter.render_tr(
                HTMLWriter.render_td(_("End:"))
                + HTMLWriter.render_td(
                    _confirm_dialog_date_and_time_format(
                        self._get_adhoc_end_time(start_at)
                        if request.var("_down_adhoc")
                        else self._custom_end_time(start_at)
                    )
                )
            )
        )

        attributes = HTML.empty()
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
                len(action_rows),
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
                duration := duration_from_html.get("_down_duration", 0), "_down_duration"
            )
            delayed_duration = duration
        else:
            delayed_duration = 0
        return delayed_duration

    def _comment(self) -> str:
        comment = (
            active_config.adhoc_downtime.get("comment", "")
            if request.var("_down_adhoc")
            else request.get_str_input("_down_comment")
        )
        if not comment:
            raise MKUserError("_down_comment", _("You need to supply a comment for your downtime."))
        return comment

    def _current_local_time(self) -> float:
        return time.time()

    def _custom_start_time(self) -> float:
        vs_date = _vs_date()
        raw_start_date = vs_date.from_html_vars("_down_from_date")
        vs_date.validate_value(raw_start_date, "_down_from_date")

        vs_time = _vs_time()
        raw_start_time = vs_time.from_html_vars("_down_from_time")
        vs_time.validate_value(raw_start_time, "_down_from_time")

        down_from = time.mktime(
            time.strptime(f"{raw_start_date} {raw_start_time}", "%Y-%m-%d %H:%M")
        )
        self._vs_down_from().validate_value(down_from, "_down_from")
        return down_from

    def _custom_end_time(self, start_time: float) -> float:
        vs_date = _vs_date()
        raw_end_date = vs_date.from_html_vars("_down_to_date")
        vs_date.validate_value(raw_end_date, "_down_to_date")

        vs_time = _vs_time()
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
    ) -> tuple[Literal["HOST", "SVC"], list[str], Rows]:
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
            # We do not want to count the services but the affected hosts in this case.
            # Since we can not get actual host rows here, we use one row per affected host
            # as an approximation. This is good enough to count the affected hosts.

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

            seen: set[str] = set()
            host_action_rows = []
            for action_row in action_rows:
                if downtime_from_bi_aggregation:
                    hosts = {hostname for ar in action_rows for _, hostname in ar["aggr_hosts"]}
                    if unseen_hosts := hosts - seen:
                        seen.update(unseen_hosts)
                        host_action_rows.append(action_row)
                elif action_row["host_name"] not in seen:
                    seen.add(action_row["host_name"])
                    host_action_rows.append(action_row)
            action_rows = host_action_rows

        else:
            specs = [spec]
        return cmdtag, specs, action_rows

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


def _confirm_dialog_date_and_time_format(timestamp: float, show_timezone: bool = True) -> str:
    """Return date, time and if show_timezone is True the local timezone in the format of e.g.
    'Mon, 01. January 2042 at 01:23 [UTC+01:00]'"""
    local_time = time.localtime(timestamp)
    return (
        time.strftime(_("%a, %d. %B %Y at %H:%M"), local_time)
        + (" " + timezone_utc_offset_str(timestamp))
        if show_timezone
        else ""
    )


def _bi_commands(downtime: DowntimeSchedule, node: CompiledAggrTree) -> Sequence[CommandSpec]:
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


def _find_all_leaves(
    node: CompiledAggrRule | CompiledAggrLeaf,
) -> list[tuple[livestatus.SiteId | None, HostName, ServiceName | None]]:
    # From BICompiledLeaf (see also eval_result_node)
    if node["type"] == 1:
        site, host = node["host"]
        return [(livestatus.SiteId(site), host, node.get("service"))]

    # From BICompiledRule (see also eval_result_node)
    if node["type"] == 2:
        entries: list[tuple[livestatus.SiteId | None, HostName, ServiceName | None]] = []
        for n in node["nodes"]:
            entries += _find_all_leaves(n)
        return entries

    # place holders
    return []


def time_interval_end(
    time_value: int | Literal["next_day", "next_week", "next_month", "next_year"], start_time: float
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


def command_remove_downtime_render(what: str) -> None:
    html.button("_remove_downtimes", _("Remove"))


def command_remove_downtime_action(  # pylint: disable=too-many-arguments
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    row_index: int,
    action_rows: Rows,
) -> CommandActionResult:
    if request.has_var("_remove_downtimes"):
        if "downtime_id" in row:
            return _rm_downtime_from_downtime_datasource(command, cmdtag, spec, row, action_rows)
        return _rm_downtime_from_hst_or_svc_datasource(command, cmdtag, row, action_rows)
    return None


def _rm_downtime_from_downtime_datasource(
    command: Command,
    cmdtag: Literal["HOST", "SVC"],
    spec: str,
    row: Row,
    action_rows: Rows,
) -> CommandActionResult:
    return (
        f"DEL_{cmdtag}_DOWNTIME;{spec}",
        command.confirm_dialog_options(
            cmdtag,
            row,
            action_rows,
        ),
    )


def _rm_downtime_from_hst_or_svc_datasource(
    command: Command, cmdtag: Literal["HOST", "SVC"], row: Row, action_rows: Rows
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
    return commands, command.confirm_dialog_options(cmdtag, row, action_rows)


CommandRemoveDowntimesHostServicesTable = Command(
    ident="remove_downtimes_hosts_services",
    title=_l("Remove downtimes"),
    confirm_title=_l("Remove scheduled downtimes?"),
    confirm_button=_l("Remove"),
    permission=PermissionActionDowntimes,
    group=CommandGroupDowntimes,
    tables=["host", "service"],
    is_shortcut=False,
    is_suggested=False,
    render=command_remove_downtime_render,
    action=command_remove_downtime_action,
)

CommandRemoveDowntimesDowntimesTable = Command(
    ident="remove_downtimes",
    title=_l("Remove downtimes"),
    confirm_title=_l("Remove scheduled downtimes?"),
    confirm_button=_l("Remove"),
    permission=PermissionActionDowntimes,
    group=CommandGroupDowntimes,
    tables=["downtime"],
    is_shortcut=True,
    is_suggested=True,
    render=command_remove_downtime_render,
    action=command_remove_downtime_action,
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


def command_remove_comments_confirm_dialog_additions(
    cmdtag: Literal["HOST", "SVC"],
    row: Row,
    action_rows: Rows,
) -> HTML:
    if len(action_rows) > 1:
        return HTML.without_escaping(_("Total comments: %d") % len(action_rows))
    return HTML.without_escaping(_("Author: ")) + row["comment_author"]


def command_remove_comments_render(what: str) -> None:
    html.open_div(class_="group")
    html.button("_delete_comments", _("Delete"), cssclass="hot")
    html.button("_cancel", _("Cancel"))
    html.close_div()


def command_remove_comments_action(
    command: Command,
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
                rm_ack = (
                    f"REMOVE_SVC_ACKNOWLEDGEMENT;{row['host_name']};{row['service_description']}"
                )
            commands.append(rm_ack)
    # Nevertheless, we need the general command, too, even for acknowledgements: The
    # acknowledgement might be persistent, so REMOVE_FOO_ACKNOWLEDGEMENT leaves the comment
    # itself, that's the whole point of being persistent. The only way to get rid of such a
    # comment is via DEL_FOO_COMMENT.
    del_cmt = f"DEL_HOST_COMMENT;{spec}" if cmdtag == "HOST" else f"DEL_SVC_COMMENT;{spec}"
    commands.append(del_cmt)
    return commands, command.confirm_dialog_options(
        cmdtag,
        row,
        action_rows,
    )


CommandRemoveComments = Command(
    ident="remove_comments",
    title=_l("Delete comments"),
    confirm_title=_l("Delete comments?"),
    confirm_button=_l("Delete"),
    is_shortcut=True,
    is_suggested=True,
    permission=PermissionActionAddComment,
    group=CommandGroupVarious,
    tables=["comment"],
    affected_output_cb=lambda _a, _b: HTML.empty(),
    render=command_remove_comments_render,
    action=command_remove_comments_action,
    confirm_dialog_additions=command_remove_comments_confirm_dialog_additions,
)
