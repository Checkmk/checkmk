#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable

from pytest import MonkeyPatch

from cmk.gui.valuespec import TextInput, ValueSpec
from cmk.gui.wato.pages.global_settings import DefaultModeEditGlobals, MatchItemGeneratorSettings
from cmk.gui.watolib.config_domain_name import ABCConfigDomain, ConfigVariable, ConfigVariableGroup
from cmk.gui.watolib.search import MatchItem


def test_match_item_generator_settings(
    monkeypatch: MonkeyPatch,
    request_context: None,
) -> None:
    class SomeConfigVariable(ConfigVariable):
        def group(self) -> type[ConfigVariableGroup]:
            raise NotImplementedError()  # Hmmm...

        def ident(self) -> str:
            return "ident"

        def valuespec(self) -> ValueSpec:
            return TextInput(title="title")

    class SomeSettingsMode(DefaultModeEditGlobals):
        def iter_all_configuration_variables(
            self,
        ) -> Iterable[tuple[ConfigVariableGroup, Iterable[ConfigVariable]]]:
            return [
                (
                    ConfigVariableGroup(),
                    [SomeConfigVariable()],
                )
            ]

    monkeypatch.setattr(ABCConfigDomain, "get_all_default_globals", lambda: {})

    assert list(
        MatchItemGeneratorSettings(
            "settings",
            "Settings",
            SomeSettingsMode,
        ).generate_match_items()
    ) == [
        MatchItem(
            title="title",
            topic="Settings",
            url="wato.py?mode=edit_configvar&varname=ident",
            match_texts=["title", "ident"],
        ),
    ]
