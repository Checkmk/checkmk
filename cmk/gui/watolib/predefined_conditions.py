#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import TypedDict

from cmk.utils.rulesets.ruleset_matcher import RuleConditionsSpec

from cmk.gui import userdb
from cmk.gui.logged_in import user
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile
from cmk.gui.watolib.utils import wato_root_dir


class PredefinedConditionSpec(TypedDict):
    title: str
    comment: str
    docu_url: str
    conditions: RuleConditionsSpec
    shared_with: Sequence[str]
    owned_by: str | None


class PredefinedConditionStore(WatoSimpleConfigFile[PredefinedConditionSpec]):
    def __init__(self) -> None:
        super().__init__(
            config_file_path=wato_root_dir() / "predefined_conditions.mk",
            config_variable="predefined_conditions",
            spec_class=PredefinedConditionSpec,
        )

    def filter_usable_entries(
        self, entries: dict[str, PredefinedConditionSpec]
    ) -> dict[str, PredefinedConditionSpec]:
        if user.may("wato.edit_all_predefined_conditions"):
            return entries

        assert user.id is not None
        user_groups = userdb.contactgroups_of_user(user.id)

        entries = self.filter_editable_entries(entries)
        entries.update({k: v for k, v in entries.items() if v["shared_with"] in user_groups})
        return entries

    def filter_editable_entries(
        self, entries: dict[str, PredefinedConditionSpec]
    ) -> dict[str, PredefinedConditionSpec]:
        if user.may("wato.edit_all_predefined_conditions"):
            return entries

        assert user.id is not None
        user_groups = userdb.contactgroups_of_user(user.id)
        return {k: v for k, v in entries.items() if v["owned_by"] in user_groups}

    def filter_by_path(self, path: str) -> dict[str, PredefinedConditionSpec]:
        result = {}
        for ident, condition in self.load_for_reading().items():
            if condition["conditions"]["host_folder"] == path:
                result[ident] = condition

        return result

    def choices(self) -> list[tuple[str, str]]:
        return [
            (ident, entry["title"])
            for ident, entry in self.filter_usable_entries(self.load_for_reading()).items()
        ]
