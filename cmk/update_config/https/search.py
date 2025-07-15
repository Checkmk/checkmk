#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from typing import NamedTuple

from cmk.utils.redis import disable_redis

from cmk.gui.main_modules import load_plugins
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars

from cmk.update_config.https.arguments import SearchArgs


class _Error(NamedTuple):
    messages: Sequence[str]


def _validate_folder(folder: str) -> None | _Error:
    choices = folder_tree().root_folder().recursive_subfolder_choices(pretty=False)
    if all(folder != arg for arg, _title in choices):
        return _Error(
            [
                "No folder found for the given argument. Use the ‘script_folder_key’ for the desired folder. Available folders:",
                *(f"{title} > '{arg}'" for arg, title in choices),
            ]
        )
    return None


def _validate_host(host: str) -> None | _Error:
    try:
        re.search(host, "", re.I)
    except re.error as e:
        return _Error([f"Invalid host argument, couldn't '{host}' regex: {e}"])
    return None


def select(ruleset: Ruleset, search_args: SearchArgs) -> Iterator[tuple[Folder, int, Rule]]:
    search: dict[str, str | tuple[str, bool]] = {}
    if (rule_folder := search_args.rule_folder()) is not None:
        if (err := _validate_folder(rule_folder[0])) is not None:
            sys.stdout.write("\n".join(err.messages) + "\n")
            return
        search["rule_folder"] = rule_folder
    if (rule_host_list := search_args.host) is not None:
        if (err := _validate_host(rule_host_list)) is not None:
            sys.stdout.write("\n".join(err.messages) + "\n")
            return
        search["rule_host_list"] = rule_host_list
    if not search:
        yield from ruleset.get_rules()
        return
    for folder, rule_index, rule in ruleset.get_rules():
        if rule.matches_search(search, {}):
            yield folder, rule_index, rule


@contextmanager
def with_allrulesets() -> Iterator[AllRulesets]:
    sys.stdout.write("Loading plugins...\n")
    load_plugins()
    sys.stdout.write("Loading rule sets...\n")
    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        yield AllRulesets.load_all_rulesets()
