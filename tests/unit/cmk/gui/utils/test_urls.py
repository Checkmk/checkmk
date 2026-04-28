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
    add_kiosk_to_url,
    doc_reference_url,
    DocReference,
    DocReferenceUtm,
    get_docs_base_url,
    is_kiosk_request,
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
    utm = DocReferenceUtm(campaign="help_menu", content="test")
    url = doc_reference_url(user.language, utm)
    assert url.startswith(f"{get_docs_base_url(user.language)}?")


def test_doc_references(request_context: None) -> None:
    utm = DocReferenceUtm(campaign="help_menu", content="test")
    assert [doc_reference_url(user.language, utm, r) for r in DocReference]


def test_doc_reference_url_encodes_special_characters_in_content(
    request_context: None,
) -> None:
    """A content value with `&` or non-ASCII must not corrupt the query string."""
    utm = DocReferenceUtm(campaign="help_menu", content="hosts & services")
    url = doc_reference_url(user.language, utm)
    # The raw '&' must not leak through, otherwise it would be parsed as a
    # new query parameter by consumers.
    assert "utm_content=hosts+%26+services" in url
    assert "content=hosts & services" not in url


def test_doc_reference_url_term_includes_patch_level(request_context: None) -> None:
    """utm_term must include the patch level (e.g. 2.3.0p1_pro), not just 2.3.0_pro."""
    from cmk.ccc.version import __version__, Version

    utm = DocReferenceUtm(campaign="help_menu", content="test")
    url = doc_reference_url(user.language, utm)
    version_without_rc = Version.from_str(__version__).version_without_rc or "master"
    assert f"utm_term={version_without_rc}_" in url


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


@pytest.mark.parametrize(
    "query_string,expected",
    [
        pytest.param("", False, id="empty query"),
        pytest.param("name=foo", False, id="no kiosk var"),
        pytest.param("kiosk=true", True, id="kiosk true"),
        pytest.param("kiosk=TRUE", True, id="kiosk true uppercase"),
        pytest.param("kiosk=1", True, id="kiosk 1"),
        pytest.param("kiosk=yes", True, id="kiosk yes"),
        pytest.param("kiosk=on", True, id="kiosk on"),
        pytest.param("kiosk=t", True, id="kiosk t"),
        pytest.param("kiosk=y", True, id="kiosk y"),
        pytest.param("kiosk=%20true%20", True, id="kiosk true whitespace padded"),
        pytest.param("kiosk=false", False, id="kiosk false is not truthy"),
        pytest.param("kiosk=0", False, id="kiosk 0 is not truthy"),
        pytest.param("kiosk=no", False, id="kiosk no is not truthy"),
        pytest.param("kiosk=off", False, id="kiosk off is not truthy"),
        pytest.param("kiosk=", False, id="kiosk empty value not truthy"),
        pytest.param("kiosk", False, id="kiosk bare flag not truthy"),
        pytest.param("name=foo&kiosk=true", True, id="kiosk alongside other vars"),
    ],
)
def test_is_kiosk_request(query_string: str, expected: bool) -> None:
    assert is_kiosk_request(Request(create_environ(query_string=query_string))) is expected


@pytest.mark.parametrize(
    "url,expected",
    [
        pytest.param("dashboard.py", "dashboard.py?kiosk=true", id="plain path kiosk appended"),
        pytest.param(
            "dashboard.py?name=foo",
            "dashboard.py?name=foo&kiosk=true",
            id="existing query kiosk appended at end",
        ),
        pytest.param(
            "dashboard.py?b=2&a=1",
            "dashboard.py?b=2&a=1&kiosk=true",
            id="existing query order preserved",
        ),
        pytest.param(
            "dashboard.py?kiosk=true",
            "dashboard.py?kiosk=true",
            id="already kiosk deduped",
        ),
        pytest.param(
            "dashboard.py?kiosk=true&name=foo",
            "dashboard.py?kiosk=true&name=foo",
            id="already kiosk position preserved",
        ),
        pytest.param(
            "dashboard.py?kiosk=false",
            "dashboard.py?kiosk=true",
            id="kiosk value overwritten to true",
        ),
        pytest.param(
            "dashboard.py#anchor",
            "dashboard.py?kiosk=true#anchor",
            id="fragment preserved kiosk before",
        ),
        pytest.param(
            "dashboard.py?name=foo#anchor",
            "dashboard.py?name=foo&kiosk=true#anchor",
            id="fragment preserved with existing query",
        ),
    ],
)
def test_add_kiosk_to_url(url: str, expected: str) -> None:
    assert add_kiosk_to_url(url) == expected
