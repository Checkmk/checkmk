#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Literal

from cmk.ccc.site import SiteId

from cmk.gui import sites
from cmk.gui.i18n import _, _l, ungettext
from cmk.gui.permissions import Permission
from cmk.gui.type_defs import Row, Rows
from cmk.gui.utils.html import HTML
from cmk.gui.utils.speaklater import LazyString

from .group import CommandGroup

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
    def __init__(
        self,
        ident: str,
        title: LazyString,
        permission: Permission,
        tables: Sequence[str],
        render: Callable[[str], None],
        action: Callable[
            ["Command", Literal["HOST", "SVC"], str, Row, int, Rows], CommandActionResult
        ],
        group: type[CommandGroup],
        confirm_button: LazyString | Callable[[], LazyString],
        confirm_title: LazyString | Callable[[], LazyString] | None = None,
        confirm_dialog_additions: Callable[[Literal["HOST", "SVC"], Row, Rows], HTML] | None = None,
        confirm_dialog_icon_class: Callable[[], Literal["question", "warning"]] | None = None,
        cancel_button: LazyString = _l("Cancel"),
        deny_button: LazyString | None = None,
        deny_js_function: str | None = None,
        affected_output_cb: Callable[[int, Literal["HOST", "SVC"]], HTML] | None = None,
        icon_name: str = "commands",
        is_show_more: bool = False,
        is_shortcut: bool = False,
        is_suggested: bool = False,
        only_view: str | None = None,
        show_command_form: bool = True,
        executor: CommandExecutor | None = None,
    ) -> None:
        self.ident = ident
        self.title = title
        self.confirm_button = confirm_button
        self._confirm_title = confirm_title
        self.cancel_button = cancel_button
        self.deny_button = deny_button
        self.deny_js_function = deny_js_function
        self.permission = permission
        self.tables = tables
        self.render = render
        self._action = action
        self.group = group
        self.only_view = only_view
        self.icon_name = icon_name
        self.is_show_more = is_show_more
        self.is_shortcut = is_shortcut
        self.is_suggested = is_suggested
        self.show_command_form = show_command_form
        self._confirm_dialog_additions = confirm_dialog_additions
        self._confirm_dialog_icon_class = confirm_dialog_icon_class
        self._affected_output_cb = affected_output_cb
        self._executor = executor

    @property
    def confirm_title(self) -> str:
        if self._confirm_title:
            return str(
                self._confirm_title() if callable(self._confirm_title) else self._confirm_title
            )
        return ("%s %s?") % (
            self.confirm_button() if callable(self.confirm_button) else self.confirm_button,
            str(self.title).lower(),
        )

    def confirm_dialog_options(
        self, cmdtag: Literal["HOST", "SVC"], row: Row, action_rows: Rows
    ) -> CommandConfirmDialogOptions:
        return CommandConfirmDialogOptions(
            self.confirm_title,
            self.affected(len(action_rows), cmdtag),
            (
                self._confirm_dialog_additions(cmdtag, row, action_rows)
                if self._confirm_dialog_additions
                else HTML.empty()
            ),
            (
                self._confirm_dialog_icon_class()
                if callable(self._confirm_dialog_icon_class)
                else "question"
            ),
            self.confirm_button() if callable(self.confirm_button) else self.confirm_button,
            self.cancel_button,
            self.deny_button,
            self.deny_js_function,
        )

    def affected(self, len_action_rows: int, cmdtag: Literal["HOST", "SVC"]) -> HTML:
        if self._affected_output_cb:
            return self._affected_output_cb(len_action_rows, cmdtag)
        return HTML.with_escaping(
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

    def action(
        self, cmdtag: Literal["HOST", "SVC"], spec: str, row: Row, row_index: int, action_rows: Rows
    ) -> CommandActionResult:
        result = self._action(self, cmdtag, spec, row, row_index, action_rows)
        if result:
            commands, confirm_dialog_options = result
            return commands, confirm_dialog_options
        return None

    def executor(self, command: CommandSpec, site: SiteId | None) -> None:
        """Function that is called to execute this action"""
        # We only get CommandSpecWithoutSite here. Can be cleaned up once we have a dedicated
        # object type for the command
        assert isinstance(command, str)
        if self._executor:
            self._executor(command, site)
            return
        sites.live().command("[%d] %s" % (int(time.time()), command), site)
