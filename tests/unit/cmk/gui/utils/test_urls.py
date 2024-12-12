#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest
from werkzeug.test import create_environ

from cmk.gui.http import Request
from cmk.gui.logged_in import user
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.urls import (
    doc_reference_url,
    DocReference,
    makeuri_contextless,
    urlencode,
    urlencode_vars,
)


@pytest.mark.parametrize(
    "inp,out",
    [
        ([], ""),
        ([("c", "d"), ("a", "b")], "a=b&c=d"),
        ([("a", 1), ("c", "d")], "a=1&c=d"),
        ([("a", "ä"), ("c", "d")], "a=%C3%A4&c=d"),
        ([("a", "abcä")], "a=abc%C3%A4"),
        ([("a", "_-.")], "a=_-."),
        ([("a", "#")], "a=%23"),
        ([("a", "+")], "a=%2B"),
        ([("a", " ")], "a=+"),
        ([("a", "/")], "a=%2F"),
        ([("a", None)], "a="),
    ],
)
def test_urlencode_vars(inp: HTTPVariables, out: str) -> None:
    assert urlencode_vars(inp) == out


@pytest.mark.parametrize(
    "inp,out",
    [
        ("välue", "v%C3%A4lue"),
        # TODO: None / int handling inconsistent with urlencode_vars()
        (None, ""),
        ("ä", "%C3%A4"),
        ("_-.", "_-."),
        ("#", "%23"),
        ("+", "%2B"),
        (" ", "+"),
        ("/", "%2F"),
    ],
)
def test_urlencode(inp: str | None, out: str) -> None:
    assert urlencode(inp) == out


def test_empty_doc_reference(request_context: None) -> None:
    doc_reference_url_without_origin = doc_reference_url().replace("?origin=checkmk", "")
    assert doc_reference_url_without_origin == user.get_docs_base_url()


def test_doc_references(request_context: None) -> None:
    assert [doc_reference_url(r) for r in DocReference]


def test_makeuri_contextless() -> None:
    request = Request(create_environ())

    value = makeuri_contextless(request, [("foo", "val"), ("bar", "val")], "wato.py")
    expected = "wato.py?bar=val&foo=val"  # query params are sorted

    assert value == expected


def test_makeuri_contextless_no_variables() -> None:
    request = Request(create_environ())

    value = makeuri_contextless(request, [], "wato.py")
    expected = "wato.py"

    assert value == expected
