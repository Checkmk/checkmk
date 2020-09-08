#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from typing import Any, Optional, Literal, List, Tuple

import livestatus

import cmk.gui.config as config
import cmk.gui.utils as utils
import cmk.gui.bi as bi
import cmk.gui.sites as sites
import cmk.gui.escaping as escaping
from cmk.gui.i18n import _u, _, _l
from cmk.gui.globals import html
from cmk.gui.htmllib import Choices
from cmk.gui.exceptions import MKUserError
from cmk.gui.valuespec import Age, AbsoluteDate, Seconds
from cmk.gui.watolib.downtime import DowntimeSchedule, determine_downtime_mode

from cmk.gui.permissions import (
    permission_section_registry,
    PermissionSection,
    permission_registry,
    Permission,
)

from cmk.gui.plugins.views import (
    command_group_registry,
    CommandGroup,
    command_registry,
    Command,
)


@command_group_registry.register
class CommandGroupVarious(CommandGroup):
    @property
    def ident(self):
        return "various"

    @property
    def title(self):
        return _("Various Commands")

    @property
    def sort_index(self):
        return 20


@permission_section_registry.register
class PermissionSectionAction(PermissionSection):
    @property
    def name(self):
        return "action"

    @property
    def title(self):
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

permission_registry.register(PermissionActionReschedule := Permission(
    section=PermissionSectionAction,
    name="reschedule",
    title=_l("Reschedule checks"),
    description=_l("Reschedule host and service checks"),
    defaults=["user", "admin"],
))


@command_registry.register
class CommandReschedule(Command):
    @property
    def ident(self):
        return "reschedule"

    @property
    def title(self):
        return _("Reschedule active checks")

    @property
    def permission(self):
        return PermissionActionReschedule

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what):
        html.button("_resched_checks", _("Reschedule"))
        html.write_text(" " + _("and spread over") + " ")
        html.text_input("_resched_spread", default_value="0", size=3, cssclass="number")
        html.write_text(" " + _("minutes") + " ")

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.var("_resched_checks"):
            spread = utils.saveint(html.request.var("_resched_spread"))
            text = "<b>" + _("reschedule an immediate check")
            if spread:
                text += _(" spread over %d minutes ") % spread

            text += "</b>" + _("of")

            t = time.time()
            if spread:
                t += spread * 60.0 * row_index / num_rows

            command = "SCHEDULE_FORCED_" + cmdtag + "_CHECK;%s;%d" % (spec, int(t))
            return command, text


#.
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

permission_registry.register(PermissionActionNotifications := Permission(
    section=PermissionSectionAction,
    name="notifications",
    title=_l("Enable/disable notifications"),
    description=_l("Enable and disable notifications on hosts and services"),
    defaults=[],
))


@command_registry.register
class CommandNotifications(Command):
    @property
    def ident(self):
        return "notifications"

    @property
    def title(self):
        return _("Notifications")

    @property
    def permission(self):
        return PermissionActionNotifications

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what):
        html.button("_enable_notifications", _("Enable"))
        html.button("_disable_notifications", _("Disable"))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.var("_enable_notifications"):
            return ("ENABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
                    _("<b>enable notifications</b> for"))
        if html.request.var("_disable_notifications"):
            return ("DISABLE_" + cmdtag + "_NOTIFICATIONS;%s" % spec,
                    _("<b>disable notifications</b> for"))


#.
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

permission_registry.register(PermissionActionEnableChecks := Permission(
    section=PermissionSectionAction,
    name="enablechecks",
    title=_l("Enable/disable checks"),
    description=_l("Enable and disable active or passive checks on hosts and services"),
    defaults=[],
))


@command_registry.register
class CommandToggleActiveChecks(Command):
    @property
    def ident(self):
        return "toggle_active_checks"

    @property
    def title(self):
        return _("Active checks")

    @property
    def permission(self):
        return PermissionActionEnableChecks

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what):
        html.button("_enable_checks", _("Enable"))
        html.button("_disable_checks", _("Disable"))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.var("_enable_checks"):
            return ("ENABLE_" + cmdtag + "_CHECK;%s" % spec, _("<b>enable active checks</b> for"))
        if html.request.var("_disable_checks"):
            return ("DISABLE_" + cmdtag + "_CHECK;%s" % spec, _("<b>disable active checks</b> for"))


#.
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


@command_registry.register
class CommandTogglePassiveChecks(Command):
    @property
    def ident(self):
        return "toggle_passive_checks"

    @property
    def title(self):
        return _("Passive checks")

    @property
    def permission(self):
        return PermissionActionEnableChecks

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what):
        html.button("_enable_passive_checks", _("Enable"))
        html.button("_disable_passive_checks", _("Disable"))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.var("_enable_passive_checks"):
            return ("ENABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec,
                    _("<b>enable passive checks</b> for"))
        if html.request.var("_disable_passive_checks"):
            return ("DISABLE_PASSIVE_" + cmdtag + "_CHECKS;%s" % spec,
                    _("<b>disable passive checks</b> for"))


#.
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

permission_registry.register(PermissionActionClearModifiedAttributes := Permission(
    section=PermissionSectionAction,
    name="clearmodattr",
    title=_l("Reset modified attributes"),
    description=_l("Reset all manually modified attributes of a host "
                   "or service (like disabled notifications)"),
    defaults=[],
))


@command_registry.register
class CommandClearModifiedAttributes(Command):
    @property
    def ident(self):
        return "clear_modified_attributes"

    @property
    def title(self):
        return _("Modified attributes")

    @property
    def permission(self):
        return PermissionActionClearModifiedAttributes

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what):
        html.button("_clear_modattr", _('Clear modified attributes'))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.var("_clear_modattr"):
            return "CHANGE_" + cmdtag + "_MODATTR;%s;0" % spec, _(
                "<b>clear the modified attributes</b> of")


#.
#   .--Fake Checks---------------------------------------------------------.
#   |         _____     _           ____ _               _                 |
#   |        |  ___|_ _| | _____   / ___| |__   ___  ___| | _____          |
#   |        | |_ / _` | |/ / _ \ | |   | '_ \ / _ \/ __| |/ / __|         |
#   |        |  _| (_| |   <  __/ | |___| | | |  __/ (__|   <\__ \         |
#   |        |_|  \__,_|_|\_\___|  \____|_| |_|\___|\___|_|\_\___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

permission_registry.register(PermissionActionFakeChecks := Permission(
    section=PermissionSectionAction,
    name="fakechecks",
    title=_l("Fake check results"),
    description=_l("Manually submit check results for host and service checks"),
    defaults=["admin"],
))


@command_group_registry.register
class CommandGroupFakeCheck(CommandGroup):
    @property
    def ident(self):
        return "fake_check"

    @property
    def title(self):
        return _("Fake check results")

    @property
    def sort_index(self):
        return 15


@command_registry.register
class CommandFakeCheckResult(Command):
    @property
    def ident(self):
        return "fake_check_result"

    @property
    def title(self):
        return _("Fake check results")

    @property
    def permission(self):
        return PermissionActionFakeChecks

    @property
    def tables(self):
        return ["host", "service"]

    @property
    def group(self):
        return CommandGroupFakeCheck

    def render(self, what):
        html.open_table()

        html.open_tr()
        html.open_td()
        html.write_text("%s: " % _("Plugin output"))
        html.close_td()
        html.open_td()
        html.text_input("_fake_output", "", size=50)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text("%s: " % _("Performance data"))
        html.close_td()
        html.open_td()
        html.text_input("_fake_perfdata", "", size=50)
        html.close_td()
        html.close_tr()

        html.open_tr()
        html.open_td()
        html.write_text(_("Result:"))
        html.close_td()
        html.open_td()
        if what == "host":
            html.button("_fake_0", _("Up"))
            html.button("_fake_1", _("Down"))
        else:
            html.button("_fake_0", _("OK"))
            html.button("_fake_1", _("Warning"))
            html.button("_fake_2", _("Critical"))
            html.button("_fake_3", _("Unknown"))
        html.close_td()
        html.close_tr()

        html.close_table()

    def action(self, cmdtag, spec, row, row_index, num_rows):
        for s in [0, 1, 2, 3]:
            statename = html.request.var("_fake_%d" % s)
            if statename:
                pluginoutput = html.request.get_unicode_input_mandatory("_fake_output").strip()
                if not pluginoutput:
                    pluginoutput = _("Manually set to %s by %s") % (
                        escaping.escape_attribute(statename), config.user.id)
                perfdata = html.request.var("_fake_perfdata")
                if perfdata:
                    pluginoutput += "|" + perfdata
                if cmdtag == "SVC":
                    cmdtag = "SERVICE"
                command = "PROCESS_%s_CHECK_RESULT;%s;%s;%s" % (cmdtag, spec, s,
                                                                livestatus.lqencode(pluginoutput))
                title = _("<b>manually set check results to %s</b> for"
                         ) % escaping.escape_attribute(statename)
                return command, title


#.
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

permission_registry.register(PermissionActionCustomNotification := Permission(
    section=PermissionSectionAction,
    name="customnotification",
    title=_l("Send custom notification"),
    description=_l("Manually let the core send a notification to a host or service in order "
                   "to test if notifications are setup correctly"),
    defaults=["user", "admin"],
))


@command_registry.register
class CommandCustomNotification(Command):
    @property
    def ident(self):
        return "send_custom_notification"

    @property
    def title(self):
        return _("Custom notification")

    @property
    def permission(self):
        return PermissionActionCustomNotification

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what):
        html.write_text(_('Comment') + ": ")
        html.text_input("_cusnot_comment", "TEST", size=20, submit="_customnotification")
        html.write_text(" &nbsp; ")
        html.checkbox("_cusnot_forced", False, label=_("forced"))
        html.checkbox("_cusnot_broadcast", False, label=_("broadcast"))
        html.write_text(" &nbsp; ")
        html.button("_customnotification", _('Send'))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.var("_customnotification"):
            comment = html.request.get_unicode_input_mandatory("_cusnot_comment")
            broadcast = 1 if html.get_checkbox("_cusnot_broadcast") else 0
            forced = 2 if html.get_checkbox("_cusnot_forced") else 0
            command = "SEND_CUSTOM_%s_NOTIFICATION;%s;%s;%s;%s" % (
                cmdtag,
                spec,
                broadcast + forced,
                config.user.id,
                livestatus.lqencode(comment),
            )
            title = _("<b>send a custom notification</b> regarding")
            return command, title


#.
#   .--Acknowledge---------------------------------------------------------.
#   |       _        _                        _          _                 |
#   |      / \   ___| | ___ __   _____      _| | ___  __| | __ _  ___      |
#   |     / _ \ / __| |/ / '_ \ / _ \ \ /\ / / |/ _ \/ _` |/ _` |/ _ \     |
#   |    / ___ \ (__|   <| | | | (_) \ V  V /| |  __/ (_| | (_| |  __/     |
#   |   /_/   \_\___|_|\_\_| |_|\___/ \_/\_/ |_|\___|\__,_|\__, |\___|     |
#   |                                                      |___/           |
#   '----------------------------------------------------------------------'

permission_registry.register(PermissionActionAcknowledge := Permission(
    section=PermissionSectionAction,
    name="acknowledge",
    title=_l("Acknowledge"),
    description=_l("Acknowledge host and service problems and remove acknowledgements"),
    defaults=["user", "admin"],
))


@command_group_registry.register
class CommandGroupAcknowledge(CommandGroup):
    @property
    def ident(self):
        return "acknowledge"

    @property
    def title(self):
        return _("Acknowledge")

    @property
    def sort_index(self):
        return 5


@command_registry.register
class CommandAcknowledge(Command):
    @property
    def ident(self):
        return "acknowledge"

    @property
    def title(self):
        return _("Acknowledge Problems")

    @property
    def permission(self):
        return PermissionActionAcknowledge

    @property
    def group(self):
        return CommandGroupAcknowledge

    @property
    def tables(self):
        return ["host", "service", "aggr"]

    def render(self, what):
        html.button("_acknowledge", _("Acknowledge"))
        html.button("_remove_ack", _("Remove Acknowledgement"))
        html.hr()
        html.checkbox("_ack_sticky", config.view_action_defaults["ack_sticky"], label=_("sticky"))
        html.checkbox("_ack_notify",
                      config.view_action_defaults["ack_notify"],
                      label=_("send notification"))
        html.checkbox("_ack_persistent",
                      config.view_action_defaults["ack_persistent"],
                      label=_('persistent comment'))
        html.hr()

        self._vs_expire().render_input("_ack_expire",
                                       config.view_action_defaults.get("ack_expire", 0))
        html.help(
            _("Note: Expiration of acknowledgements only works when using the Checkmk Micro Core."))
        html.hr()
        html.write_text(_("Comment") + ": ")
        html.text_input("_ack_comment", size=48, submit="_acknowledge")

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if "aggr_tree" in row:  # BI mode
            specs = []
            for site, host, service in bi.find_all_leaves(row["aggr_tree"]):
                if service:
                    spec = "%s;%s" % (host, service)
                    cmdtag = "SVC"
                else:
                    spec = host
                    cmdtag = "HOST"
                specs.append((site, spec, cmdtag))

        if html.request.var("_acknowledge"):
            comment = html.request.get_unicode_input("_ack_comment")
            if not comment:
                raise MKUserError("_ack_comment", _("You need to supply a comment."))
            if ";" in comment:
                raise MKUserError("_ack_comment", _("The comment must not contain semicolons."))
            non_empty_comment = comment

            sticky = 2 if html.request.var("_ack_sticky") else 0
            sendnot = 1 if html.request.var("_ack_notify") else 0
            perscomm = 1 if html.request.var("_ack_persistent") else 0

            expire_secs = self._vs_expire().from_html_vars("_ack_expire")
            if expire_secs:
                expire = int(time.time()) + expire_secs
                expire_text = ";%d" % expire
            else:
                expire_text = ""

            def make_command_ack(spec, cmdtag):
                return "ACKNOWLEDGE_" + cmdtag + "_PROBLEM;%s;%d;%d;%d;%s" % (
                    spec, sticky, sendnot, perscomm, config.user.id) + (
                        ";%s" % livestatus.lqencode(non_empty_comment)) + expire_text

            if "aggr_tree" in row:  # BI mode
                commands = [
                    (site, make_command_ack(spec_, cmdtag_)) for site, spec_, cmdtag_ in specs
                ]
            else:
                commands = [make_command_ack(spec, cmdtag)]

            title = _("<b>acknowledge the problems%s</b> of") % (
                expire_text and (_(" for a period of %s") % Age().value_to_text(expire_secs)) or "")
            return commands, title

        if html.request.var("_remove_ack"):

            def make_command_rem(spec, cmdtag):
                return "REMOVE_" + cmdtag + "_ACKNOWLEDGEMENT;%s" % spec

            if "aggr_tree" in row:  # BI mode
                commands = [(site, make_command_rem(spec, cmdtag)) for site, spec_, cmdtag_ in specs
                           ]
            else:
                commands = [make_command_rem(spec, cmdtag)]
            title = _("<b>remove acknowledgements</b> from")
            return commands, title

    def _vs_expire(self):
        return Age(
            display=["days", "hours", "minutes"],
            label=_("Expire acknowledgement after"),
        )


#.
#   .--Comments------------------------------------------------------------.
#   |           ____                                     _                 |
#   |          / ___|___  _ __ ___  _ __ ___   ___ _ __ | |_ ___           |
#   |         | |   / _ \| '_ ` _ \| '_ ` _ \ / _ \ '_ \| __/ __|          |
#   |         | |__| (_) | | | | | | | | | | |  __/ | | | |_\__ \          |
#   |          \____\___/|_| |_| |_|_| |_| |_|\___|_| |_|\__|___/          |
#   |                                                                      |
#   '----------------------------------------------------------------------'

permission_registry.register(PermissionActionAddComment := Permission(
    section=PermissionSectionAction,
    name="addcomment",
    title=_l("Add comments"),
    description=_l("Add comments to hosts or services, and remove comments"),
    defaults=["user", "admin"],
))


@command_registry.register
class CommandAddComment(Command):
    @property
    def ident(self):
        return "add_comment"

    @property
    def title(self):
        return _("Add comment")

    @property
    def permission(self):
        return PermissionActionAddComment

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what):
        html.write_text(_('Comment') + ": ")
        html.text_input("_comment", size=33, submit="_add_comment")
        html.write_text(" &nbsp; ")
        html.button("_add_comment", _("Add comment"))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.var("_add_comment"):
            comment = html.request.get_unicode_input("_comment")
            if not comment:
                raise MKUserError("_comment", _("You need to supply a comment."))
            command = "ADD_" + cmdtag + "_COMMENT;%s;1;%s" % \
                      (spec, config.user.id) + (";%s" % livestatus.lqencode(comment))
            title = _("<b>add a comment to</b>")
            return command, title


#.
#   .--Downtimes-----------------------------------------------------------.
#   |         ____                      _   _                              |
#   |        |  _ \  _____      ___ __ | |_(_)_ __ ___   ___  ___          |
#   |        | | | |/ _ \ \ /\ / / '_ \| __| | '_ ` _ \ / _ \/ __|         |
#   |        | |_| | (_) \ V  V /| | | | |_| | | | | | |  __/\__ \         |
#   |        |____/ \___/ \_/\_/ |_| |_|\__|_|_| |_| |_|\___||___/         |
#   |                                                                      |
#   '----------------------------------------------------------------------'

permission_registry.register(PermissionActionDowntimes := Permission(
    section=PermissionSectionAction,
    name="downtimes",
    title=_l("Set/Remove downtimes"),
    description=_l("Schedule and remove downtimes on hosts and services"),
    defaults=["user", "admin"],
))

permission_registry.register(
    Permission(
        section=PermissionSectionAction,
        name="remove_all_downtimes",
        title=_l("Remove all downtimes"),
        description=_l("Allow the user to use the action \"Remove all\" downtimes"),
        defaults=["user", "admin"],
    ))


@command_group_registry.register
class CommandGroupDowntimes(CommandGroup):
    @property
    def ident(self):
        return "downtimes"

    @property
    def title(self):
        return _("Schedule downtimes")

    @property
    def sort_index(self):
        return 10


@command_registry.register
class CommandScheduleDowntimes(Command):
    @property
    def ident(self):
        return "schedule_downtimes"

    @property
    def title(self):
        return _("Schedule downtimes")

    @property
    def permission(self):
        return PermissionActionDowntimes

    @property
    def group(self):
        return CommandGroupDowntimes

    @property
    def tables(self):
        return ["host", "service", "aggr"]

    def render(self, what):
        html.write_text(_('Downtime Comment') + ": ")
        html.text_input("_down_comment", "", size=60, submit="")
        html.hr()
        html.button("_down_from_now", _("From now for"))
        html.nbsp()
        html.text_input("_down_minutes",
                        default_value="60",
                        size=4,
                        submit="_down_from_now",
                        cssclass="number")
        html.write_text("&nbsp; " + _("minutes"))
        html.hr()
        for time_range in config.user_downtime_timeranges:
            html.button("_downrange__%s" % time_range['end'], _u(time_range['title']))
        if what != "aggr" and config.user.may("action.remove_all_downtimes"):
            html.write_text(" &nbsp; - &nbsp;")
            html.button("_down_remove", _("Remove all"))
        html.hr()
        if config.adhoc_downtime and config.adhoc_downtime.get("duration"):
            adhoc_duration = config.adhoc_downtime.get("duration")
            adhoc_comment = config.adhoc_downtime.get("comment", "")
            html.button("_down_adhoc", _("Adhoc for %d minutes") % adhoc_duration)
            html.nbsp()
            html.write_text(_('with comment') + ": ")
            html.write(adhoc_comment)
            html.hr()

        html.button("_down_custom", _("Custom time range"))
        self._vs_down_from().render_input("_down_from", time.time())
        html.write_text("&nbsp; " + _('to') + " &nbsp;")
        self._vs_down_to().render_input("_down_to", time.time() + 7200)
        html.hr()
        html.checkbox("_down_flexible", False, label="%s " % _('flexible with max. duration'))
        self._vs_duration().render_input("_down_duration", 7200)
        if what == "host":
            html.hr()
            html.checkbox("_include_childs", False, label=_('Also set downtime on child hosts'))
            html.write_text("  ")
            html.checkbox("_include_childs_recurse", False, label=_('Do this recursively'))
        elif what == "service":
            html.hr()
            html.checkbox("_on_hosts",
                          False,
                          label=_('Schedule downtimes on the affected '
                                  '<b>hosts</b> instead of on the individual '
                                  'services'))

        if self._has_recurring_downtimes():
            html.hr()
            html.checkbox("_down_do_recur",
                          False,
                          label=_("Repeat this downtime on a regular basis every"))
            html.write_text(" ")

            from cmk.gui.cee.plugins.wato.cmc import recurring_downtimes_types  # pylint: disable=no-name-in-module,import-outside-toplevel

            recurring_selections: Choices = [
                (str(k), v) for (k, v) in sorted(recurring_downtimes_types().items())
            ]
            html.dropdown("_down_recurring", recurring_selections, deflt="3")
            html.write_text(_("(This only works when using CMC)"))

    def action(self, cmdtag: Any, spec: Any, row: Any, row_index: Any, num_rows: Any) -> Any:
        """Prepares the livestatus command for any received downtime information through WATO"""
        if html.request.var("_down_remove"):
            return self._remove_downtime_details(cmdtag, row)

        recurring_number = self._recurring_number()
        title_prefix = self._title_prefix(recurring_number)

        if html.request.var("_down_from_now"):
            start_time = self._current_local_time()
            duration_minutes = self._from_now_minutes()
            end_time = self._time_after_minutes(start_time, duration_minutes)
            title = self._title_for_next_minutes(duration_minutes, title_prefix)
        elif html.request.var("_down_adhoc"):
            start_time = self._current_local_time()
            duration_minutes = config.adhoc_downtime.get("duration", 0)
            end_time = self._time_after_minutes(start_time, duration_minutes)
            title = self._title_for_next_minutes(duration_minutes, title_prefix)
        elif html.request.var("_down_custom"):
            start_time = self._custom_start_time()
            end_time = self._custom_end_time(start_time)
            title = self._title_range(start_time, end_time)
        else:  # one of the default time buttons
            button_value = self.button_interval_value()
            if button_value is None:
                # the remove button in the Show Downtimes WATO view returns None here
                # TODO: separate the remove mechanism from the create downtime procedure in the views call
                return
            next_time_interval = button_value
            start_time = self._current_local_time()
            end_time = time_interval_end(next_time_interval, start_time)
            if end_time is None:
                end_time = start_time + int(next_time_interval)
            title = time_interval_to_human_readable(next_time_interval, title_prefix)

        comment = self._comment()
        delayed_duration = self._flexible_option()
        mode = determine_downtime_mode(recurring_number, delayed_duration)
        downtime = DowntimeSchedule(start_time, end_time, mode, delayed_duration, comment)
        cmdtag, specs, title = self._downtime_specs(cmdtag, row, spec, title)
        if "aggr_tree" in row:  # BI mode
            node = row["aggr_tree"]
            return bi_commands(downtime, node), title
        return [downtime.livestatus_command(spec_, cmdtag) for spec_ in specs], title

    def _remove_downtime_details(self, cmdtag, row):
        if not config.user.may("action.remove_all_downtimes"):
            return
        if html.request.var("_on_hosts"):
            raise MKUserError(
                "_on_hosts",
                _("The checkbox for setting host downtimes does not work when removing downtimes."))
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
            commands.append("DEL_%s_DOWNTIME;%d\n" % (cmdtag, dtid))
        title = _("<b>remove all scheduled downtimes</b> of ")
        return commands, title

    def _recurring_number(self):
        """Retrieve integer value for repeat downtime option

        Retrieve the integer value which corresponds to the selected option in the "Repeat this downtime"
        dropdown menu. The values are mapped as follows:
            <hour> : 1
            <day> : 2
            <week> : 3
            <second week> : 4
            <fourth week>: 5
            <same nth weekday (from beginning)> : 6
            <same nth weekday (from end)> : 7
            <same day of the month> : 8
        """
        if self._has_recurring_downtimes() and html.get_checkbox("_down_do_recur"):
            recurring_type = html.request.get_integer_input_mandatory("_down_recurring")
        else:
            recurring_type = 0
        return recurring_type

    def _flexible_option(self):
        if html.request.var("_down_flexible"):
            delayed_duration = self._vs_duration().from_html_vars("_down_duration")  # type: Seconds
            self._vs_duration().validate_value(delayed_duration, "_down_duration")
        else:
            delayed_duration = 0
        return delayed_duration

    def _comment(self):
        comment = html.request.get_unicode_input("_down_comment")
        if not comment:
            raise MKUserError("_down_comment", _("You need to supply a comment for your downtime."))
        return comment

    def _current_local_time(self):
        return time.time()

    def _time_after_minutes(self, start_time, minutes):
        return start_time + minutes * 60

    def _from_now_minutes(self):
        try:
            minutes = html.request.get_integer_input_mandatory("_down_minutes", 0)
        except MKUserError:
            minutes = 0

        if minutes <= 0:
            raise MKUserError("_down_minutes", _("Please enter a positive number of minutes."))
        return minutes

    def _custom_start_time(self):
        maybe_down_from = self._vs_down_from().from_html_vars("_down_from")
        if maybe_down_from is None:
            raise Exception("impossible: _down_from is None")
        down_from = int(maybe_down_from)
        self._vs_down_from().validate_value(down_from, "_down_from")
        return maybe_down_from

    def _custom_end_time(self, start_time):
        maybe_down_to = self._vs_down_to().from_html_vars("_down_to")
        if maybe_down_to is None:
            raise Exception("impossible: _down_to is None")
        end_time = maybe_down_to
        self._vs_down_to().validate_value(end_time, "_down_to")

        if end_time < time.time():
            raise MKUserError(
                "_down_to",
                _("You cannot set a downtime that ends in the past. "
                  "This incident will be reported."))

        if end_time < start_time:
            raise MKUserError("_down_to", _("Your end date is before your start date."))

        return end_time

    def _title_prefix(self, recurring_number):
        if recurring_number:
            from cmk.gui.cee.plugins.wato.cmc import \
                recurring_downtimes_types  # pylint: disable=no-name-in-module,import-outside-toplevel
            description = (_("schedule a periodic downtime every %s") %
                           recurring_downtimes_types()[recurring_number])
        else:
            description = _("schedule an immediate downtime")
        return description

    def _title_for_next_minutes(self, minutes, prefix):
        return _("<b>%s for the next %d minutes</b> on") % (prefix, minutes)

    def _title_range(self, start_time, end_time):
        return _("<b>schedule a downtime from %s to %s</b> on ") % (time.asctime(
            time.localtime(start_time)), time.asctime(time.localtime(end_time)))

    def button_interval_value(self):
        rangebtns = (varname for varname, _value in html.request.itervars(prefix="_downrange"))
        try:
            rangebtn: Optional[str] = next(rangebtns)
        except StopIteration:
            rangebtn = None
        if rangebtn is None:
            return None
        _btnname, period = rangebtn.split("__", 1)
        return period

    def _downtime_specs(self, cmdtag, row, spec, title):
        if html.request.var("_include_childs"):  # only for hosts
            specs = [spec] + self._get_child_hosts(
                row["site"], [spec], recurse=bool(html.request.var("_include_childs_recurse")))
        elif html.request.var("_on_hosts"):  # set on hosts instead of services
            specs = [spec.split(";")[0]]
            title += " the hosts of"
            cmdtag = "HOST"
        else:
            specs = [spec]
        return cmdtag, specs, title

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
        for h in hosts:
            query += "Filter: parents >= %s\n" % h
        query += "Or: %d\n" % len(hosts)
        children = sites.live().query_column(query)
        sites.live().set_only_sites(None)

        # Recursion, but try to avoid duplicate work
        new_children = set(children) - hosts
        if new_children and recurse:
            rec_childs = self._get_child_hosts(site, new_children, True)
            new_children.update(rec_childs)
        return list(new_children)

    def _has_recurring_downtimes(self):
        try:
            # The suppression below is OK, we just want to check if the module is there.
            import cmk.gui.cee.plugins.wato.cmc  # noqa: F401 # pylint: disable=unused-variable,unused-import,import-outside-toplevel
            return True
        except ImportError:
            return False


def bi_commands(downtime: DowntimeSchedule, node: Any) -> List[Tuple[Any, Any]]:
    """Generate the list of downtime command strings for the BI module"""
    commands_aggr = []
    for site, host, service in bi.find_all_leaves(node):
        if service:
            spec = "%s;%s" % (host, service)
            cmdtag = "SVC"
        else:
            spec = host
            cmdtag = "HOST"
        commands_aggr.append((site, downtime.livestatus_command(spec, cmdtag)))
    return commands_aggr


def time_interval_end(time_value: Literal["next_day", "next_week", "next_month", "next_year"],
                      start_time: float) -> Optional[float]:
    now = time.localtime(start_time)
    if time_value == "next_day":
        return time.mktime(
            (now.tm_year, now.tm_mon, now.tm_mday, 23, 59, 59, 0, 0, now.tm_isdst)) + 1
    if time_value == "next_week":
        wday = now.tm_wday
        days_plus = 6 - wday
        res = time.mktime(
            (now.tm_year, now.tm_mon, now.tm_mday, 23, 59, 59, 0, 0, now.tm_isdst)) + 1
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
        '<b>schedule an immediate downtime until 24:00:00</b> on'

    Returns:
        string representing the schedule downtime title
    """
    downtime_titles = {
        "next_day": _("<b>%s until 24:00:00</b> on"),
        "next_week": _("<b>%s until sunday night</b> on"),
        "next_month": _("<b>%s until end of month</b> on"),
    }
    try:
        title = downtime_titles[next_time_interval]
    except KeyError:
        duration = int(next_time_interval)
        title = _("<b>%%s of %s length</b> on") % duration_human_readable(duration)
    return title % prefix


def duration_human_readable(secs):
    """Convert duration time into a more convenient readable string

    Args:
        secs:
            The duration time in seconds

    Examples:
        >>> duration_human_readable(1)
        '1 seconds'

    Returns:

    """
    days, rest = divmod(secs, 86400)
    hours, rest = divmod(rest, 3600)
    mins, secs = divmod(rest, 60)

    return ", ".join([
        "%d %s" % (val, label) for val, label in [
            (days, "days"),
            (hours, "hours"),
            (mins, "minutes"),
            (secs, "seconds"),
        ] if val > 0
    ])


@command_registry.register
class CommandRemoveDowntime(Command):
    @property
    def ident(self):
        return "remove_downtimes"

    @property
    def title(self):
        return _("Remove downtimes")

    @property
    def permission(self):
        return PermissionActionDowntimes

    @property
    def tables(self):
        return ["downtime"]

    def render(self, what):
        html.button("_remove_downtimes", _("Remove"))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.has_var("_remove_downtimes"):
            return ("DEL_%s_DOWNTIME;%d" % (cmdtag, spec), _("remove"))


@command_registry.register
class CommandRemoveComments(Command):
    @property
    def ident(self):
        return "remove_comments"

    @property
    def title(self):
        return _("Remove comments")

    @property
    def permission(self):
        return PermissionActionAddComment

    @property
    def tables(self):
        return ["comment"]

    def render(self, what):
        html.button("_remove_comments", _("Remove"))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.has_var("_remove_comments"):
            commands = [("DEL_%s_COMMENT;%d" % (cmdtag, spec))]
            if row.get("comment_entry_type") == 4:
                if row.get("service_description"):
                    commands.append(("REMOVE_%s_ACKNOWLEDGEMENT;%s;%s" %
                                     (cmdtag, row["host_name"], row["service_description"])))
                else:
                    commands.append(("REMOVE_%s_ACKNOWLEDGEMENT;%s" % (cmdtag, row["host_name"])))

            return commands, _("remove")


#.
#   .--Stars * (Favorites)-------------------------------------------------.
#   |                   ____  _                                            |
#   |                  / ___|| |_ __ _ _ __ ___  __/\__                    |
#   |                  \___ \| __/ _` | '__/ __| \    /                    |
#   |                   ___) | || (_| | |  \__ \ /_  _\                    |
#   |                  |____/ \__\__,_|_|  |___/   \/                      |
#   |                                                                      |
#   '----------------------------------------------------------------------'

permission_registry.register(PermissionActionStar := Permission(
    section=PermissionSectionAction,
    name="star",
    title=_l("Use favorites"),
    description=_l("This permission allows a user to make certain host and services "
                   "his personal favorites. Favorites can be used for a having a fast "
                   "access to items that are needed on a regular base."),
    defaults=["user", "admin"],
))


@command_registry.register
class CommandFavorites(Command):
    @property
    def ident(self):
        return "favorites"

    @property
    def title(self):
        return _("Favorites")

    @property
    def permission(self):
        return PermissionActionStar

    @property
    def tables(self):
        return ["host", "service"]

    def render(self, what):
        html.button("_star", _("Add to Favorites"))
        html.button("_unstar", _("Remove from Favorites"))

    def action(self, cmdtag, spec, row, row_index, num_rows):
        if html.request.var("_star") or html.request.var("_unstar"):
            star = 1 if html.request.var("_star") else 0
            if star:
                title = _("<b>add to you favorites</b>")
            else:
                title = _("<b>remove from your favorites</b>")
            return "STAR;%d;%s" % (star, spec), title

    def executor(self, command, site):
        _unused, star, spec = command.split(";", 2)
        stars = config.user.stars
        if star == "0" and spec in stars:
            stars.remove(spec)
        elif star == "1":
            stars.add(spec)
        config.user.save_stars()
