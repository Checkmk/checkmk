#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import re
from typing import Any

from cmk.ccc.plugin_registry import Registry

from cmk.gui.permissions import permission_registry

from .base import Command
from .group import command_group_registry


class CommandRegistry(Registry[Command]):
    def plugin_name(self, instance: Command) -> str:
        return instance.ident


command_registry = CommandRegistry()


# TODO: Kept for pre 1.6 compatibility
def register_legacy_command(spec: dict[str, Any]) -> None:
    command_registry.register(
        Command(
            ident=re.sub("[^a-zA-Z]", "", spec["title"]).lower(),
            title=spec["title"],
            confirm_button=spec.get("confirm_button", "Submit"),
            permission=permission_registry[spec["permission"]],
            tables=spec["tables"],
            render=spec["render"],
            action=lambda command, cmdtag, cmd_spec, row, row_index, action_rows: spec["action"](
                cmdtag, cmd_spec, row
            ),
            group=command_group_registry[spec.get("group", "various")],
            only_view=spec.get("only_view"),
        )
    )
