#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Final

from cmk.graphing.v1 import Title

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


class TestTitle:
    def test_mod_tuple(self) -> None:
        assert (
            Title("The ruleset '%s' has been replaced by '%s'")
            % (
                Title("Old rule"),
                Title("Fancy new rule"),
            )
        ).localize(_localizer) == "Raider heißt jetzt Twix"

    def test_mod_string(self) -> None:
        assert (Title("The host %r does not exist") % "horst").localize(
            _localizer
        ) == "'horst' gibbet nich"

    def test_add(self) -> None:
        assert (Title("One sentence. ") + Title("Another sentence.")).localize(
            _localizer
        ) == "blahblah"
