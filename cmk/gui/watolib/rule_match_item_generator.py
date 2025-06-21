#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.http import request
from cmk.gui.i18n import _
from cmk.gui.utils.urls import (
    makeuri_contextless,
)

from .rulespecs import get_rulespec_allow_list, Rulespec, RulespecGroupRegistry, RulespecRegistry
from .search import ABCMatchItemGenerator, MatchItem, MatchItems


class MatchItemGeneratorRules(ABCMatchItemGenerator):
    def __init__(
        self,
        name: str,
        rulesepc_group_reg: RulespecGroupRegistry,
        rulespec_reg: RulespecRegistry,
    ) -> None:
        super().__init__(name)
        self._rulespec_group_registry = rulesepc_group_reg
        self._rulespec_registry = rulespec_reg

    def _topic(self, rulespec: Rulespec) -> str:
        if rulespec.is_deprecated:
            return _("Deprecated rulesets")
        return f"{self._rulespec_group_registry[rulespec.main_group_name]().title}"

    def generate_match_items(self) -> MatchItems:
        allow_list = get_rulespec_allow_list()
        for group in self._rulespec_registry.get_all_groups():
            for rulespec in self._rulespec_registry.get_by_group(group):
                if not rulespec.title or not allow_list.is_visible(rulespec.name):
                    continue

                yield MatchItem(
                    title=rulespec.title,
                    topic=self._topic(rulespec),
                    url=makeuri_contextless(
                        request,
                        [("mode", "edit_ruleset"), ("varname", rulespec.name)],
                        filename="wato.py",
                    ),
                    match_texts=[rulespec.title, rulespec.name],
                )

    @staticmethod
    def is_affected_by_change(_change_action_name: str) -> bool:
        return False

    @property
    def is_localization_dependent(self) -> bool:
        return True
