#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.utils.translations import (
    translate_hostname,
    translate_service_description,
    TranslationOptions,
)


# translate_service_description covers all options thus we need to test
# translate_hostname only with option "drop_domain"
@pytest.mark.parametrize(
    "hostname, translation, result",
    [
        (
            "host123.foobar.de",
            TranslationOptions(case=None, drop_domain=False, mapping=[], regex=[]),
            "host123.foobar.de",
        ),
        (
            "host123.foobar.de",
            TranslationOptions(case=None, drop_domain=True, mapping=[], regex=[]),
            "host123",
        ),
        (
            "127.0.0.1",
            TranslationOptions(case=None, drop_domain=True, mapping=[], regex=[]),
            "127.0.0.1",
        ),
    ],
)
def test_translate_hostname(hostname: str, translation: TranslationOptions, result: str) -> None:
    assert translate_hostname(translation, hostname) == result


@pytest.mark.parametrize(
    "service_description, translation, result",
    [
        # Fixed names
        (
            " Check_MK ",
            TranslationOptions(case=None, drop_domain=False, mapping=[], regex=[]),
            "Check_MK",
        ),
        (
            " Check_MK Agent ",
            TranslationOptions(case=None, drop_domain=False, mapping=[], regex=[]),
            "Check_MK Agent",
        ),
        (
            " Check_MK Discovery ",
            TranslationOptions(case=None, drop_domain=False, mapping=[], regex=[]),
            "Check_MK Discovery",
        ),
        (
            " Check_MK inventory ",
            TranslationOptions(case=None, drop_domain=False, mapping=[], regex=[]),
            "Check_MK inventory",
        ),
        (
            " Check_MK HW/SW Inventory ",
            TranslationOptions(case=None, drop_domain=False, mapping=[], regex=[]),
            "Check_MK HW/SW Inventory",
        ),
        (
            " Check_MK ",
            # Legacy format, should be transformed
            TranslationOptions(regex=(" Ch[e]ck_MK .*", " Chäck_MK ")),  # type: ignore[typeddict-item]
            "Check_MK",
        ),
        (
            " Check_MK Agent ",
            # Legacy format, should be transformed
            TranslationOptions(regex=(" Ch[e]ck_MK .*", " Chäck_MK ")),  # type: ignore[typeddict-item]
            "Check_MK Agent",
        ),
        (
            " Check_MK Discovery ",
            # Legacy format, should be transformed
            TranslationOptions(regex=(" Ch[e]ck_MK .*", " Chäck_MK ")),  # type: ignore[typeddict-item]
            "Check_MK Discovery",
        ),
        (
            " Check_MK inventory ",
            # Legacy format, should be transformed
            TranslationOptions(regex=(" Ch[e]ck_MK .*", " Chäck_MK ")),  # type: ignore[typeddict-item]
            "Check_MK inventory",
        ),
        (
            " Check_MK HW/SW Inventory ",
            # Legacy format, should be transformed
            TranslationOptions(regex=(" Ch[e]ck_MK .*", " Chäck_MK ")),  # type: ignore[typeddict-item]
            "Check_MK HW/SW Inventory",
        ),
        (
            " Check_MK ",
            TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[(" Check_MK ", "Foo Bar")],
                regex=[],
            ),
            "Check_MK",
        ),
        (
            " Check_MK Agent ",
            TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[(" Check_MK Agent ", "Foo Bar")],
                regex=[],
            ),
            "Check_MK Agent",
        ),
        (
            " Check_MK Discovery ",
            TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[(" Check_MK Discovery ", "Foo Bar")],
                regex=[],
            ),
            "Check_MK Discovery",
        ),
        (
            " Check_MK inventory ",
            TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[(" Check_MK inventory ", "Foo Bar")],
                regex=[],
            ),
            "Check_MK inventory",
        ),
        (
            " Check_MK HW/SW Inventory ",
            TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[(" Check_MK HW/SW Inventory ", "Foo Bar")],
                regex=[],
            ),
            "Check_MK HW/SW Inventory",
        ),
        # Case
        (
            " foo bar ",
            TranslationOptions(case="upper", drop_domain=False, mapping=[], regex=[]),
            "FOO BAR",
        ),
        (
            " FOO BAR ",
            TranslationOptions(case="lower", drop_domain=False, mapping=[], regex=[]),
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
            TranslationOptions(
                case=None, drop_domain=False, mapping=[], regex=[(" F[o]+", " Föö Bar ")]
            ),
            "Foo Bar",
        ),
        (
            " Foo Bar ",
            TranslationOptions(
                case=None, drop_domain=False, mapping=[], regex=[(" F[o]+.*", " Föö Bar ")]
            ),
            "Föö Bar",
        ),
        (
            " Foo Bar ",
            TranslationOptions(
                case=None, drop_domain=False, mapping=[], regex=[(" F([o]+) Bar ", " l\\1l ")]
            ),
            "lool",
        ),
        (
            " Foo Bar ",
            TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[],
                regex=[(" F([o]+) B([a])r ", " l\\2\\1l\\2 ")],
            ),
            "laoola",
        ),
        (
            " Foo Bar ",
            TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[],
                regex=[
                    (" F[o]+", " FOO Bar "),
                    (" F[o]+.*", " Foo BAR "),
                ],
            ),
            "Foo BAR",
        ),
        # Mapping
        (
            " Foo Bar ",
            TranslationOptions(
                case=None, drop_domain=False, mapping=[("Foo Bar", " Bar Baz ")], regex=[]
            ),
            "Foo Bar",
        ),
        (
            " Foo Bar ",
            TranslationOptions(
                case=None, drop_domain=False, mapping=[(" Foo Bar ", " Bar Baz ")], regex=[]
            ),
            "Bar Baz",
        ),
        (
            " Foo Bar ",
            TranslationOptions(
                case=None,
                drop_domain=False,
                mapping=[
                    (" FOO Bar ", " Foo Bar "),
                    (" Foo Bar ", " Bar Baz "),
                ],
                regex=[],
            ),
            "Bar Baz",
        ),
        # Preserve order
        (
            " Foo Bar ",
            TranslationOptions(
                case="upper",
                drop_domain=False,
                mapping=[(" foo bar ", " fOO bAR ")],
                # Legacy format, should be transformed
                regex=(" FOO.*", " foo bar "),  # type: ignore[typeddict-item]
            ),
            "fOO bAR",
        ),
    ],
)
def test_translate_service_description(
    service_description: str, translation: TranslationOptions, result: str
) -> None:
    assert translate_service_description(translation, service_description) == result
