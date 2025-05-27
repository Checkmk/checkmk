#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Sequence
from os import devnull
from pathlib import Path
from typing import override, TypedDict
from unittest.mock import MagicMock

import pytest

from cmk.gui.valuespec import Dictionary, DictionaryEntry, TextInput
from cmk.gui.wato.pages._simple_modes import SimpleEditMode, SimpleModeType
from cmk.gui.watolib.config_domain_name import ABCConfigDomain
from cmk.gui.watolib.simple_config_file import WatoSimpleConfigFile


class SomeSpec(TypedDict):
    title: str
    comment: str
    docu_url: str
    disabled: bool
    site: Sequence[str]
    foo: str


class SomeModeType(SimpleModeType[SomeSpec]):
    def affected_config_domains(self) -> list[ABCConfigDomain]:
        return []

    def can_be_disabled(self) -> bool:
        return False

    def is_site_specific(self) -> bool:
        return False

    def name_singular(self) -> str:
        return "some-mode-type"

    def type_name(self) -> str:
        return "some-mode-type"


class SomeStore(WatoSimpleConfigFile[SomeSpec]):
    def __init__(self, value: SomeSpec):
        super().__init__(config_file_path=Path(devnull), config_variable="foo", spec_class=SomeSpec)
        self._value = value

    @override
    def _load_file(self, *, lock: bool) -> dict[str, SomeSpec]:
        return {self._config_variable: self._value}

    # def validate(self, raw: object) -> SomeSpec:
    #     return SomeSpec(**vars(raw))

    @override
    def save(self, cfg: dict[str, SomeSpec], pprint_value: bool) -> None:
        self._value = cfg[self._config_variable]


class SomeEditMode(SimpleEditMode[SomeSpec]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mock = MagicMock(spec=Dictionary)

    def valuespec(self) -> Dictionary:
        return self.mock

    @classmethod
    def name(cls) -> str:
        return "some-edit-mode"

    @staticmethod
    def static_permissions() -> Sequence[str]:
        return ["some-edit-mode"]

    def _vs_individual_elements(self) -> list[DictionaryEntry]:
        return [("foo", TextInput(title="Foo"))]


@pytest.mark.parametrize(
    ["new", "clone", "expected_form"],
    [
        pytest.param(True, None, False, id="New"),
        pytest.param(False, None, True, id="Edit"),
        pytest.param(True, "clone", True, id="Clone"),
    ],
)
@pytest.mark.usefixtures("request_context")
def test_page_form_render_entry_valuespec(
    new: bool, clone: str | None, expected_form: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    mode_type = SomeModeType()
    store = SomeStore(
        SomeSpec(
            title="Foo",
            comment="comment",
            docu_url="docu-url",
            disabled=False,
            site=[],
            foo="bar",
        )
    )

    mode = SomeEditMode(mode_type, store)
    mode._entry = store._value
    mode._new = new
    mode._clone = clone
    mode._page_form_render_entry_valuespec()

    vs_mock = mode.valuespec()
    assert vs_mock.render_input.call_count == 1  # type: ignore[attr-defined]
    assert vs_mock.render_input.call_args[0][1] == (store._value if expected_form else {})  # type: ignore[attr-defined,typeddict-item]
