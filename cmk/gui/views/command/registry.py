#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=protected-access

import re
from typing import Any, Literal

from cmk.ccc.plugin_registry import Registry

from cmk.gui.permissions import Permission, permission_registry
from cmk.gui.type_defs import Row, Rows
from cmk.gui.utils.speaklater import LazyString

from .base import Command, CommandActionResult
from .group import command_group_registry, CommandGroup


class CommandRegistry(Registry[Command]):
    def plugin_name(self, instance: Command) -> str:
        return instance.ident


command_registry = CommandRegistry()


# TODO: Kept for pre 1.6 compatibility
def register_legacy_command(spec: dict[str, Any]) -> None:
    class LegacyCommand(Command):
        def __init__(self, ident: str, spec: dict[str, Any]):
            self._ident = ident
            self._spec = spec

        @property
        def ident(self) -> str:
            return self._ident

        @property
        def title(self) -> str:
            return self._spec["title"]

        @property
        def confirm_button(self) -> LazyString:
            return self._spec.get("confirm_button", "Submit")

        @property
        def permission(self) -> Permission:
            return permission_registry[self._spec["permission"]]

        @property
        def tables(self) -> list[str]:
            return self._spec["tables"]

        def render(self, what: str) -> None:
            self._spec["render"]()

        def action(
            self,
            cmdtag: Literal["HOST", "SVC"],
            spec: str,
            row: Row,
            row_index: int,
            action_rows: Rows,
        ) -> CommandActionResult:
            return self._spec["action"](cmdtag, spec, row)

        def _action(
            self,
            cmdtag: Literal["HOST", "SVC"],
            spec: str,
            row: Row,
            row_index: int,
            action_rows: Rows,
        ) -> CommandActionResult:
            return self._spec["_action"](cmdtag, spec, row)

        @property
        def group(self) -> type[CommandGroup]:
            return command_group_registry[self._spec.get("group", "various")]

        @property
        def only_view(self) -> str | None:
            return self._spec.get("only_view")

    command_registry.register(
        LegacyCommand(
            ident=re.sub("[^a-zA-Z]", "", spec["title"]).lower(),
            spec=spec,
        )
    )
