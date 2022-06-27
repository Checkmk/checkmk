#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.translations as translations


# translate_service_description covers all options thus we need to test
# translate_hostname only with option "drop_domain"
@pytest.mark.parametrize(
    "hostname, translation, result",
    [
        (
            "host123.foobar.de",
            {
                "drop_domain": False,
            },
            "host123.foobar.de",
        ),
        (
            "host123.foobar.de",
            {
                "drop_domain": True,
            },
            "host123",
        ),
        (
            "127.0.0.1",
            {
                "drop_domain": True,
            },
            "127.0.0.1",
        ),
    ],
)
def test_translate_hostname(hostname, translation, result) -> None:
    assert translations.translate_hostname(translation, hostname) == result


@pytest.mark.parametrize(
    "service_description, translation, result",
    [
        # Fixed names
        (" Check_MK ", {}, "Check_MK"),
        (" Check_MK Agent ", {}, "Check_MK Agent"),
        (" Check_MK Discovery ", {}, "Check_MK Discovery"),
        (" Check_MK inventory ", {}, "Check_MK inventory"),
        (" Check_MK HW/SW Inventory ", {}, "Check_MK HW/SW Inventory"),
        (
            " Check_MK ",
            {
                "case": "upper",
            },
            "Check_MK",
        ),
        (
            " Check_MK Agent ",
            {
                "case": "upper",
            },
            "Check_MK Agent",
        ),
        (
            " Check_MK Discovery ",
            {
                "case": "upper",
            },
            "Check_MK Discovery",
        ),
        (
            " Check_MK inventory ",
            {
                "case": "upper",
            },
            "Check_MK inventory",
        ),
        (
            " Check_MK HW/SW Inventory ",
            {
                "case": "upper",
            },
            "Check_MK HW/SW Inventory",
        ),
        (" Check_MK ", {"regex": (" Ch[e]ck_MK .*", " Chäck_MK ")}, "Check_MK"),
        (" Check_MK Agent ", {"regex": (" Ch[e]ck_MK .*", " Chäck_MK ")}, "Check_MK Agent"),
        (" Check_MK Discovery ", {"regex": (" Ch[e]ck_MK .*", " Chäck_MK ")}, "Check_MK Discovery"),
        (" Check_MK inventory ", {"regex": (" Ch[e]ck_MK .*", " Chäck_MK ")}, "Check_MK inventory"),
        (
            " Check_MK HW/SW Inventory ",
            {"regex": (" Ch[e]ck_MK .*", " Chäck_MK ")},
            "Check_MK HW/SW Inventory",
        ),
        (
            " Check_MK ",
            {
                "mapping": [(" Check_MK ", "Foo Bar")],
            },
            "Check_MK",
        ),
        (
            " Check_MK Agent ",
            {
                "mapping": [(" Check_MK Agent ", "Foo Bar")],
            },
            "Check_MK Agent",
        ),
        (
            " Check_MK Discovery ",
            {
                "mapping": [(" Check_MK Discovery ", "Foo Bar")],
            },
            "Check_MK Discovery",
        ),
        (
            " Check_MK inventory ",
            {
                "mapping": [(" Check_MK inventory ", "Foo Bar")],
            },
            "Check_MK inventory",
        ),
        (
            " Check_MK HW/SW Inventory ",
            {
                "mapping": [(" Check_MK HW/SW Inventory ", "Foo Bar")],
            },
            "Check_MK HW/SW Inventory",
        ),
        # Case
        (
            " Foo Bar ",
            {
                "case": "unknown",
            },
            "Foo Bar",
        ),
        (
            " foo bar ",
            {
                "case": "upper",
            },
            "FOO BAR",
        ),
        (
            " FOO BAR ",
            {
                "case": "lower",
            },
            "foo bar",
        ),
        # Regex
        (
            " Foo Bar ",
            {
                "regex": (" F[o]+", " Föö Bar "),
            },
            "Foo Bar",
        ),
        (
            " Foo Bar ",
            {
                "regex": (" F[o]+.*", " Föö Bar "),
            },
            "Föö Bar",
        ),
        (
            " Foo Bar ",
            {
                "regex": (" F([o]+) Bar ", " l\\1l "),
            },
            "lool",
        ),
        (
            " Foo Bar ",
            {
                "regex": [(" F[o]+", " Föö Bar ")],
            },
            "Foo Bar",
        ),
        (
            " Foo Bar ",
            {
                "regex": [(" F[o]+.*", " Föö Bar ")],
            },
            "Föö Bar",
        ),
        (
            " Foo Bar ",
            {
                "regex": [(" F([o]+) Bar ", " l\\1l ")],
            },
            "lool",
        ),
        (
            " Foo Bar ",
            {
                "regex": [(" F([o]+) B([a])r ", " l\\2\\1l\\2 ")],
            },
            "laoola",
        ),
        (
            " Foo Bar ",
            {
                "regex": [(" F[o]+", " FOO Bar "), (" F[o]+.*", " Foo BAR ")],
            },
            "Foo BAR",
        ),
        # Mapping
        (" Foo Bar ", {"mapping": [("Foo Bar", " Bar Baz ")]}, "Foo Bar"),
        (" Foo Bar ", {"mapping": [(" Foo Bar ", " Bar Baz ")]}, "Bar Baz"),
        (
            " Foo Bar ",
            {"mapping": [(" FOO Bar ", " Foo Bar "), (" Foo Bar ", " Bar Baz ")]},
            "Bar Baz",
        ),
        # Preserve order
        (
            " Foo Bar ",
            {
                "case": "upper",
                "regex": (" FOO.*", " foo bar "),
                "mapping": [(" foo bar ", " fOO bAR ")],
            },
            "fOO bAR",
        ),
    ],
)
def test_translate_service_description(service_description, translation, result) -> None:
    assert translations.translate_service_description(translation, service_description) == result
