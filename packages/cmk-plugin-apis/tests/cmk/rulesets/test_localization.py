#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

import pytest

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1._localize import _Localizable

_TRANSLATABLE_STRINGS: Final = {
    "The ruleset '%s' has been replaced by '%s'": "%s heißt jetzt %s",
    "Old rule": "Raider",
    "Fancy new rule": "Twix",
    "The host %r does not exist": "%r gibbet nich",
    "horst": "This should not be used.",
    "One sentence. ": "blah",
    "Another sentence.": "blah",
    "is %s": "I am %s",
}


def _localizer(string: str) -> str:
    return _TRANSLATABLE_STRINGS[string]


class TestLocalizable:
    @pytest.mark.parametrize(["localizable"], [(Title,), (Message,), (Label,), (Help,)])
    def test_mod_tuple(self, localizable: type[_Localizable]) -> None:
        assert (
            localizable("The ruleset '%s' has been replaced by '%s'")
            % (
                localizable("Old rule"),
                localizable("Fancy new rule"),
            )
        ).localize(_localizer) == "Raider heißt jetzt Twix"

    @pytest.mark.parametrize(["localizable"], [(Title,), (Message,), (Label,), (Help,)])
    def test_mod_string(self, localizable: type[_Localizable]) -> None:
        assert (localizable("The host %r does not exist") % "horst").localize(
            _localizer
        ) == "'horst' gibbet nich"

    @pytest.mark.parametrize(["localizable"], [(Title,), (Message,), (Label,), (Help,)])
    def test_add(self, localizable: type[_Localizable]) -> None:
        assert (localizable("One sentence. ") + localizable("Another sentence.")).localize(
            _localizer
        ) == "blahblah"

    @pytest.mark.parametrize(
        ["title1", "title2", "expected_equality"],
        [
            pytest.param(Title("same"), Title("same"), True, id="equal"),
            pytest.param(Title("same"), Title("different"), False, id="not equal"),
            pytest.param(
                (Title("is %s") % "same").localize(_localizer),
                (Title("is %s") % "same").localize(_localizer),
                True,
                id="localized equal",
            ),
            pytest.param(
                (Title("is %s") % "same").localize(_localizer),
                (Title("is %s") % "different").localize(_localizer),
                False,
                id="localized unequal",
            ),
        ],
    )
    def test_eq(self, title1: Title, title2: Title, expected_equality: bool) -> None:
        assert (title1 == title2) is expected_equality

    @pytest.mark.parametrize(["localizable"], [(Title,), (Message,), (Label,), (Help,)])
    def test_repr(self, localizable: type[_Localizable]) -> None:
        assert repr(localizable("abc")) == f"{localizable.__name__}('abc')"
