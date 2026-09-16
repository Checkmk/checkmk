#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterator

import pytest

from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.global_settings.search import MatchItemGeneratorSettings
from cmk.gui.i18n import _l
from cmk.gui.search.matchers import MatchItem
from cmk.gui.utils.roles import UserPermissions
from cmk.gui.watolib.config_domain_name import ConfigVariableGroup
from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import Integer
from tests.testlib.gui.global_settings import patch_factory_defaults, registered

TEST_VAR = "ident"


def _match_items() -> list[MatchItem]:
    generator = MatchItemGeneratorSettings(
        "settings",
        "Settings",
        filename="global_settings.py",
        shows=lambda _config_variable: True,
    )
    return list(generator.generate_match_items(UserPermissions({}, {}, {}, [])))


@pytest.fixture(name="test_variable")
def fixture_test_variable(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    patch_factory_defaults(monkeypatch, {TEST_VAR: 1})
    with registered(ConfigVariableGroup(title=_l("Test group"), sort_index=1), TEST_VAR):
        yield


@pytest.fixture(name="transformed_variable")
def fixture_transformed_variable(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    patch_factory_defaults(monkeypatch, {TEST_VAR: 1})
    with registered(
        ConfigVariableGroup(title=_l("Test group"), sort_index=1),
        TEST_VAR,
        form_spec=lambda _context: TransformDataForLegacyFormatOrRecomposeFunction(
            wrapped_form_spec=Integer(title=Title("Wrapped title")),
            from_disk=lambda value: value,
            to_disk=lambda value: value,
        ),
    ):
        yield


@pytest.mark.usefixtures("request_context", "test_variable")
def test_a_registered_variable_links_to_the_settings_page() -> None:
    assert _match_items() == [
        MatchItem(
            title="Test",
            topic="Settings",
            url=f"global_settings.py?varname={TEST_VAR}",
            match_texts=["Test", TEST_VAR],
        )
    ]


@pytest.mark.usefixtures("request_context", "transformed_variable")
def test_the_title_comes_from_the_form_spec_a_transform_wraps() -> None:
    assert [match_item.title for match_item in _match_items()] == ["Wrapped title"]
