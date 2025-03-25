#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Literal

from livestatus import SiteId

from cmk.gui.config import active_config
from cmk.gui.data_source import ABCDataSource
from cmk.gui.display_options import display_options
from cmk.gui.exceptions import MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import InfoName, Row, Rows, ViewSpec
from cmk.gui.utils.confirm_with_preview import command_confirm_dialog
from cmk.gui.utils.selection_id import SelectionId

from .base import Command, CommandConfirmDialogOptions, CommandExecutor, CommandSpec
from .group import CommandGroup
from .registry import command_registry


def core_command(
    what: str, row: Row, row_nr: int, action_rows: Rows
) -> tuple[
    Sequence[CommandSpec], list[tuple[str, str]], CommandConfirmDialogOptions, CommandExecutor
]:
    """Examine the current HTML variables in order determine, which command the user has selected.
    The fetch ids from a data row (host name, service name, downtime/commands id) and
    construct one or several core command lines and a descriptive confirm dialog."""
    host = row.get("host_name")
    descr = row.get("service_description")

    if what == "host":
        assert isinstance(host, str)
        spec: str = host
        cmdtag: Literal["HOST", "SVC"] = "HOST"

    elif what == "service":
        assert isinstance(host, str)
        assert isinstance(descr, str)
        spec = f"{host};{descr}"
        cmdtag = "SVC"

    else:
        # e.g. downtime_id for downtimes may be int, same for acknowledgements
        spec = str(row[what + "_id"])
        cmdtag = "SVC" if descr else "HOST"

    commands: Sequence[CommandSpec] | None = None
    # Call all command actions. The first one that detects
    # itself to be executed (by examining the HTML variables)
    # will return a command to execute and confirm dialog options for the
    # confirmation dialog.
    for cmd in command_registry.values():
        if user.may(cmd.permission.name):
            result = cmd.action(cmdtag, spec, row, row_nr, action_rows)
            confirm_options = cmd.user_confirm_options(len(action_rows), cmdtag)
            if result:
                executor = cmd.executor
                commands, confirm_dialog_options = result
                break

    if commands is None:
        raise MKUserError(None, _("Sorry. This command is not implemented."))

    # Some commands return lists of commands, others
    # just return one basic command. Convert those
    if isinstance(commands, str):
        commands = [commands]

    return commands, confirm_options, confirm_dialog_options, executor


def should_show_command_form(
    datasource: ABCDataSource, ignore_display_option: bool = False
) -> bool:
    """Whether or not this view handles commands for the current user

    When it does not handle commands the command tab, command form, row
    selection and processing commands is disabled.
    """
    if not ignore_display_option and display_options.disabled(display_options.C):
        return False
    if not user.may("general.act"):
        return False

    # What commands are available depends on the Livestatus table we
    # deal with. If a data source provides information about more
    # than one table, (like services datasource also provide host
    # information) then the first info is the primary table. So 'what'
    # will be one of "host", "service", "command" or "downtime".
    what = datasource.infos[0]
    for command in command_registry.values():
        if what in command.tables and user.may(command.permission.name):
            return True

    return False


def get_command_groups(info_name: InfoName) -> dict[type[CommandGroup], list[Command]]:
    by_group: dict[type[CommandGroup], list[Command]] = {}

    for command in command_registry.values():
        if info_name in command.tables and user.may(command.permission.name):
            # Some special commands can be shown on special views using this option.  It is
            # currently only used by custom commands, not shipped with Checkmk.
            if command.only_view and request.var("view_name") != command.only_view:
                continue
            by_group.setdefault(command.group, []).append(command)

    return by_group


# Returns:
# True -> Actions have been done
# False -> No actions done because now rows selected
def do_actions(
    view: ViewSpec,
    what: InfoName,
    action_rows: Rows,
    backurl: str,
) -> bool:
    if not user.may("general.act"):
        html.show_error(
            _(
                "You are not allowed to perform actions. "
                "If you think this is an error, please ask "
                "your administrator grant you the permission to do so."
            )
        )
        return False  # no actions done

    # User canceled the first confirm dialog
    if request.get_str_input("_cancel") is not None:
        return False

    if not action_rows:
        message_no_rows = _("No rows selected to perform actions for.")
        message_no_rows += '<br><a href="{}">{}</a>'.format(backurl, _("Back to view"))
        html.show_error(message_no_rows)
        return False  # no actions done

    command = None
    _commands, confirm_options, confirm_dialog_options, executor = core_command(
        what, action_rows[0], 0, action_rows
    )

    if not command_confirm_dialog(
        confirm_options,
        confirm_dialog_options.confirm_title,
        (
            confirm_dialog_options.affected + confirm_dialog_options.additions
            if confirm_dialog_options.additions
            else confirm_dialog_options.affected
        ),
        confirm_dialog_options.icon_class,
        confirm_dialog_options.confirm_button,
        confirm_dialog_options.cancel_button,
        confirm_dialog_options.deny_button,
        confirm_dialog_options.deny_js_function,
    ):
        return False

    if request.has_var("_do_confirm_host_downtime"):
        request.set_var("_on_hosts", "on")

    count = 0
    already_executed = set()
    for nr, row in enumerate(action_rows):
        core_commands, _confirm_options, _confirm_dialog_options, executor = core_command(
            what,
            row,
            nr,
            action_rows,
        )
        for command_entry in core_commands:
            site: str | None = row.get(
                "site"
            )  # site is missing for BI rows (aggregations can spawn several sites)
            if (site, command_entry) not in already_executed:
                # Some command functions return the information about the site per-command (e.g. for BI)
                if isinstance(command_entry, tuple):
                    site, command = command_entry
                else:
                    command = command_entry

                executor(command, SiteId(site) if site else None)
                already_executed.add((site, command_entry))
                count += 1

    message = None
    if command:
        message = _("Successfully sent %d commands.") % count
        if active_config.debug:
            message += _("The last one was: <pre>%s</pre>") % command
    elif count == 0:
        message = _("No matching data row. No command sent.")

    if message:
        backurl += "&filled_in=filter&_show_filter_form=0"
        message += '<br><a href="{}">{}</a>'.format(backurl, _("Back to view"))
        if request.var("show_checkboxes") == "1":
            request.del_var("selection")
            backurl += "&selection=" + SelectionId.from_request(request)
            message += '<br><a href="{}">{}</a>'.format(
                backurl,
                _("Back to view with checkboxes reset"),
            )
        if request.var("_show_result") == "0":
            html.immediate_browser_redirect(0.5, backurl)
        html.show_message(message)

    return True
