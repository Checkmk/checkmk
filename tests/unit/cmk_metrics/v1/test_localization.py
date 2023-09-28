#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk_metrics.v1._localize import Localizable

_TRANSLATABLE_STRINGS: Final = {
    "The ruleset '%s' has been replaced by '%s'": "%s heißt jetzt %s",
    "Old rule": "Raider",
    "Fancy new rule": "Twix",
    "The host %r does not exist": "%r gibbet nich",
    "horst": "This should not be used.",
    "One sentence. ": "blah",
    "Another sentence.": "blah",
}


def _localizer(string: str) -> str:
    return _TRANSLATABLE_STRINGS[string]


class TestLocalizable:
    def test_mod_tuple(self) -> None:
        assert (
            Localizable("The ruleset '%s' has been replaced by '%s'")
            % (
                Localizable("Old rule"),
                Localizable("Fancy new rule"),
            )
        ).localize(_localizer) == "Raider heißt jetzt Twix"

    def test_mod_string(self) -> None:
        assert (Localizable("The host %r does not exist") % "horst").localize(
            _localizer
        ) == "'horst' gibbet nich"

    def test_add(self) -> None:
        assert (Localizable("One sentence. ") + Localizable("Another sentence.")).localize(
            _localizer
        ) == "blahblah"
