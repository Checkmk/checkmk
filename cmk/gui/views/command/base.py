#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from livestatus import SiteId

from cmk.gui import sites
from cmk.gui.i18n import _, _l, ungettext
from cmk.gui.permissions import Permission
from cmk.gui.type_defs import Row, Rows
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString
from cmk.gui.utils.time import timezone_utc_offset_str

from .group import command_group_registry, CommandGroup

CommandSpecWithoutSite = str
CommandSpecWithSite = tuple[SiteId | None, CommandSpecWithoutSite]
CommandSpec = CommandSpecWithoutSite | CommandSpecWithSite


@dataclass
class CommandConfirmDialogOptions:
    confirm_title: str
    affected: HTML
    additions: HTML
    icon_class: Literal["question", "warning"]
    confirm_button: LazyString
    cancel_button: LazyString
    deny_button: LazyString | None = None
    deny_js_function: str | None = None


CommandActionResult = (
    tuple[CommandSpecWithoutSite | Sequence[CommandSpec], CommandConfirmDialogOptions] | None
)
CommandExecutor = Callable[[CommandSpec, SiteId | None], None]


class Command(abc.ABC):
    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a command. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        raise NotImplementedError()

    @property
    def confirm_title(self) -> str:
        return ("%s %s?") % (self.confirm_button, self.title.lower())

    @property
    @abc.abstractmethod
    def confirm_button(self) -> LazyString:
        raise NotImplementedError()

    @property
    def cancel_button(self) -> LazyString:
        return _l("Cancel")

    @property
    def deny_button(self) -> LazyString | None:
        return None

    @property
    def deny_js_function(self) -> str | None:
        return None

    @property
    @abc.abstractmethod
    def permission(self) -> Permission:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def tables(self) -> list[str]:
        """List of livestatus table identities the action may be used with"""
        raise NotImplementedError()

    def confirm_dialog_additions(
        self,
        cmdtag: Literal["HOST", "SVC"],
        row: Row,
        len_action_rows: int,
    ) -> HTML:
        return HTML("")

    def confirm_dialog_icon_class(self) -> Literal["question", "warning"]:
        return "question"

    def confirm_dialog_options(
        self, cmdtag: Literal["HOST", "SVC"], row: Row, len_action_rows: int
    ) -> CommandConfirmDialogOptions:
        return CommandConfirmDialogOptions(
            self.confirm_title,
            self.affected(len_action_rows, cmdtag),
            self.confirm_dialog_additions(cmdtag, row, len_action_rows),
            self.confirm_dialog_icon_class(),
            self.confirm_button,
            self.cancel_button,
            self.deny_button,
            self.deny_js_function,
        )

    def confirm_dialog_date_and_time_format(
        self, timestamp: float, show_timezone: bool = True
    ) -> str:
        """Return date, time and if show_timezone is True the local timezone in the format of e.g.
        'Mon, 01. January 2042 at 01:23 [UTC+01:00]'"""
        local_time = time.localtime(timestamp)
        return (
            time.strftime(_("%a, %d. %B %Y at %H:%M"), local_time)
            + (" " + timezone_utc_offset_str(timestamp))
            if show_timezone
            else ""
        )

    def affected(self, len_action_rows: int, cmdtag: Literal["HOST", "SVC"]) -> HTML:
        return HTML(
            _("Affected %s: %s")
            % (
                (
                    ungettext(
                        "host",
                        "hosts",
                        len_action_rows,
                    )
                    if cmdtag == "HOST"
                    else ungettext(
                        "service",
                        "services",
                        len_action_rows,
                    )
                ),
                len_action_rows,
            )
        )

    def user_confirm_options(
        self, len_rows: int, cmdtag: Literal["HOST", "SVC"]
    ) -> list[tuple[str, str]]:
        return [(_("Confirm"), "_do_confirm")]

    def render(self, what: str) -> None:
        raise NotImplementedError()

    def action(
        self, cmdtag: Literal["HOST", "SVC"], spec: str, row: Row, row_index: int, action_rows: Rows
    ) -> CommandActionResult:
        result = self._action(cmdtag, spec, row, row_index, action_rows)
        if result:
            commands, confirm_dialog_options = result
            return commands, confirm_dialog_options
        return None

    @abc.abstractmethod
    def _action(
        self, cmdtag: Literal["HOST", "SVC"], spec: str, row: Row, row_index: int, action_rows: Rows
    ) -> CommandActionResult:
        raise NotImplementedError()

    @property
    def group(self) -> type[CommandGroup]:
        """The command group the commmand belongs to"""
        return command_group_registry["various"]

    @property
    def only_view(self) -> str | None:
        """View name to show a view exclusive command for"""
        return None

    @property
    def icon_name(self) -> str:
        return "commands"

    @property
    def is_show_more(self) -> bool:
        return False

    @property
    def is_shortcut(self) -> bool:
        return False

    @property
    def is_suggested(self) -> bool:
        return False

    @property
    def show_command_form(self) -> bool:
        return True

    def executor(self, command: CommandSpec, site: SiteId | None) -> None:
        """Function that is called to execute this action"""
        # We only get CommandSpecWithoutSite here. Can be cleaned up once we have a dedicated
        # object type for the command
        assert isinstance(command, str)
        sites.live().command("[%d] %s" % (int(time.time()), command), site)
