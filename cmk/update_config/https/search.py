#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
import sys
from collections.abc import Sequence
from contextlib import contextmanager
from typing import Iterator, NamedTuple

import pydantic

from cmk.utils.redis import disable_redis

from cmk.gui.main_modules import load_plugins
from cmk.gui.session import SuperUserContext
from cmk.gui.utils.script_helpers import gui_context
from cmk.gui.watolib.hosts_and_folders import Folder, folder_tree
from cmk.gui.watolib.rulesets import AllRulesets, Rule, Ruleset
from cmk.gui.wsgi.blueprints.global_vars import set_global_vars


class _Error(NamedTuple):
    messages: Sequence[str]


class SearchArgs(pydantic.BaseModel):
    host: str | None
    folder: str | None
    folder_recursive: str | None

    def rule_folder(self) -> tuple[str, bool] | _Error | None:
        if self.folder is not None:
            if (err := _validate_folder(self.folder)) is not None:
                return err
            return (self.folder, False)
        if self.folder_recursive is not None:
            if (err := _validate_folder(self.folder_recursive)) is not None:
                return err
            return (self.folder_recursive, True)
        return None

    def rule_host_list(self) -> None | _Error | str:
        if self.host is None:
            return None
        try:
            re.search(self.host, "", re.I)
        except re.error as e:
            return _Error([f"Invalid host argument, couldn't '{self.host}' regex: {e}"])
        return self.host


def _validate_folder(folder: str) -> None | _Error:
    choices = folder_tree().root_folder().recursive_subfolder_choices(pretty=False)
    if all(folder != arg for arg, _title in choices):
        return _Error(
            [
                "No folder found for the given argument. Available folders:",
                *(f"'{arg}' > {title}" for arg, title in choices),
            ]
        )
    return None


def select(ruleset: Ruleset, search_args: SearchArgs) -> Iterator[tuple[Folder, int, Rule]]:
    search: dict[str, str | tuple[str, bool]] = {}
    match search_args.rule_folder():
        case None:
            pass
        case _Error(errs):
            sys.stdout.write("\n".join(errs) + "\n")
            return
        case tuple(rule_folder):
            search["rule_folder"] = rule_folder
    match search_args.rule_host_list():
        case None:
            pass
        case _Error(errs):
            sys.stdout.write("\n".join(errs) + "\n")
            return
        case str(rule_host_list):
            search["rule_host_list"] = rule_host_list
    if not search:
        yield from ruleset.get_rules()
        return
    for folder, rule_index, rule in ruleset.get_rules():
        if rule.matches_search(search):
            yield folder, rule_index, rule


@contextmanager
def with_allrulesets() -> Iterator[AllRulesets]:
    load_plugins()
    with disable_redis(), gui_context(), SuperUserContext():
        set_global_vars()
        yield AllRulesets.load_all_rulesets()
