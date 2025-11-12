#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.translations import translate, TranslationOptions


@pytest.mark.parametrize(
    "name, translation, result",
    [
        (
            "host123.foobar.de",
            TranslationOptions(drop_domain=False),
            "host123.foobar.de",
        ),
        (
            "host123.foobar.de",
            TranslationOptions(drop_domain=True),
            "host123",
        ),
        (
            "127.0.0.1",
            TranslationOptions(drop_domain=True),
            "127.0.0.1",
        ),
        # Fixed names
        (
            " Check_MK ",
            TranslationOptions(),
            "Check_MK",
        ),
        (
            " Check_MK Agent ",
            TranslationOptions(),
            "Check_MK Agent",
        ),
        (
            " Check_MK Discovery ",
            TranslationOptions(),
            "Check_MK Discovery",
        ),
        (
            " Check_MK inventory ",
            TranslationOptions(),
            "Check_MK inventory",
        ),
        (
            " Check_MK HW/SW Inventory ",
            TranslationOptions(),
            "Check_MK HW/SW Inventory",
        ),
        # Case
        (
            " Foo Bar ",
            # This can never happen when we are fully typed
            TranslationOptions(case="unknown"),  # type: ignore[typeddict-item]
            "Foo Bar",
        ),
        (
            " foo bar ",
            TranslationOptions(case="upper"),
            "FOO BAR",
        ),
        (
            " FOO BAR ",
            TranslationOptions(case="lower"),
            "foo bar",
        ),
        # Regex
        (
            " Foo Bar ",
            # Legacy format, should be transformed
            TranslationOptions(regex=(" F[o]+", " Föö Bar ")),  # type: ignore[typeddict-item]
            "Foo Bar",
        ),
        (
            " Foo Bar ",
            # Legacy format, should be transformed
            TranslationOptions(regex=(" F[o]+.*", " Föö Bar ")),  # type: ignore[typeddict-item]
            "Föö Bar",
        ),
        (
            " Foo Bar ",
            # Legacy format, should be transformed
            TranslationOptions(regex=(" F([o]+) Bar ", " l\\1l ")),  # type: ignore[typeddict-item]
            "lool",
        ),
        (
            " Foo Bar ",
            TranslationOptions(regex=[(" F[o]+", " Föö Bar ")]),
            "Foo Bar",
        ),
        (
            " Foo Bar ",
            TranslationOptions(regex=[(" F[o]+.*", " Föö Bar ")]),
            "Föö Bar",
        ),
        (
            " Foo Bar ",
            TranslationOptions(regex=[(" F([o]+) Bar ", " l\\1l ")]),
            "lool",
        ),
        (
            " Foo Bar ",
            TranslationOptions(regex=[(" F([o]+) B([a])r ", " l\\2\\1l\\2 ")]),
            "laoola",
        ),
        (
            " Foo Bar ",
            TranslationOptions(
                regex=[
                    (" F[o]+", " FOO Bar "),
                    (" F[o]+.*", " Foo BAR "),
                ]
            ),
            "Foo BAR",
        ),
        # Mapping
        (
            " Foo Bar ",
            TranslationOptions(mapping=[("Foo Bar", " Bar Baz ")]),
            "Foo Bar",
        ),
        (
            " Foo Bar ",
            TranslationOptions(mapping=[(" Foo Bar ", " Bar Baz ")]),
            "Bar Baz",
        ),
        (
            " Foo Bar ",
            TranslationOptions(
                mapping=[
                    (" FOO Bar ", " Foo Bar "),
                    (" Foo Bar ", " Bar Baz "),
                ]
            ),
            "Bar Baz",
        ),
        # Preserve order
        (
            " Foo Bar ",
            TranslationOptions(
                case="upper",
                # Legacy format, should be transformed
                regex=(" FOO.*", " foo bar "),  # type: ignore[typeddict-item]
                mapping=[(" foo bar ", " fOO bAR ")],
            ),
            "fOO bAR",
        ),
    ],
)
def test_translate(name: str, translation: TranslationOptions, result: str) -> None:
    assert translate(translation, name) == result
