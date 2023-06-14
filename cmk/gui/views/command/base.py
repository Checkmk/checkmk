#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import time
from collections.abc import Callable, Sequence
from typing import Literal, Union

from livestatus import SiteId

from cmk.gui import sites
from cmk.gui.i18n import _, ungettext
from cmk.gui.permissions import Permission
from cmk.gui.type_defs import Row, Rows

from .group import command_group_registry, CommandGroup

CommandSpecWithoutSite = str
CommandSpecWithSite = tuple[str | None, CommandSpecWithoutSite]
CommandSpec = CommandSpecWithoutSite | CommandSpecWithSite
CommandActionResult = Union[tuple[CommandSpecWithoutSite | Sequence[CommandSpec], str] | None]
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
    @abc.abstractmethod
    def permission(self) -> Permission:
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def tables(self) -> list[str]:
        """List of livestatus table identities the action may be used with"""
        raise NotImplementedError()

    def user_dialog_suffix(
        self, title: str, len_action_rows: int, cmdtag: Literal["HOST", "SVC"]
    ) -> str:
        return title + " the following %(count)d %(what)s?" % {
            "count": len_action_rows,
            "what": ungettext(
                "host",
                "hosts",
                len_action_rows,
            )
            if cmdtag == "HOST"
            else ungettext(
                "service",
                "services",
                len_action_rows,
            ),
        }

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
            commands, title = result
            return commands, self.user_dialog_suffix(title, len(action_rows), cmdtag)
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

    def executor(self, command: CommandSpec, site: SiteId | None) -> None:
        """Function that is called to execute this action"""
        # We only get CommandSpecWithoutSite here. Can be cleaned up once we have a dedicated
        # object type for the command
        assert isinstance(command, str)
        sites.live().command("[%d] %s" % (int(time.time()), command), site)
