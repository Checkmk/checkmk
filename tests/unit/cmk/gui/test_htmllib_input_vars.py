#!/usr/bin/env python
# encoding: utf-8

import pytest

from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html


def test_get_ascii_input(monkeypatch, register_builtin_html):
    monkeypatch.setattr(html.request, "vars", {
        "xyz": "x",
        "abc": "äbc",
    })

    assert html.get_ascii_input("xyz") == "x"
    assert isinstance(html.get_ascii_input("xyz"), str)

    with pytest.raises(MKUserError) as e:
        html.get_ascii_input("abc")
    assert "must only contain ASCII" in "%s" % e

    assert html.get_ascii_input("get_default", "xyz") == "xyz"
    assert html.get_ascii_input("zzz") is None


def test_get_integer_input(monkeypatch, register_builtin_html):
    monkeypatch.setattr(html.request, "vars", {
        "number": "2",
        "float": "2.2",
        "not_a_number": "a",
    })

    with pytest.raises(MKUserError) as e:
        html.get_integer_input("not_existing")
    assert "is missing" in "%s" % e

    assert html.get_integer_input("get_default", 1) == 1

    assert html.get_integer_input("number") == 2

    with pytest.raises(MKUserError) as e:
        html.get_integer_input("bla")
    assert "is missing" in "%s" % e

    with pytest.raises(MKUserError) as e:
        html.get_integer_input("float")
    assert "is not an integer" in "%s" % e

    with pytest.raises(MKUserError) as e:
        html.get_integer_input("not_a_number")
    assert "is not an integer" in "%s" % e


@pytest.mark.parametrize("invalid_url", [
    "http://localhost/",
    "://localhost",
    "localhost:80/bla",
])
def test_get_url_input_invalid_urls(monkeypatch, register_builtin_html, invalid_url):
    monkeypatch.setattr(html.request, "vars", {
        "varname": invalid_url,
    })

    with pytest.raises(MKUserError) as e:
        html.get_url_input("varname")
    assert "not a valid URL" in "%s" % e


def test_get_url_input(monkeypatch, register_builtin_html):
    monkeypatch.setattr(html.request, "vars", {
        "url": "view.py?bla=blub",
        "no_url": "2",
        "invalid_url": "http://bla/",
        "invalid_char": "viäw.py",
        "invalid_char2": "vi+w.py",
    })

    with pytest.raises(MKUserError) as e:
        html.get_url_input("not_existing")
    assert "is missing" in "%s" % e

    assert html.get_url_input("get_default", "my_url.py") == "my_url.py"
    assert html.get_url_input("get_default", "http://bla/") == "http://bla/"
    assert html.get_url_input("url") == "view.py?bla=blub"
    assert html.get_url_input("no_url") == "2"

    with pytest.raises(MKUserError) as e:
        html.get_url_input("invalid_url")
    assert "not a valid" in "%s" % e

    with pytest.raises(MKUserError) as e:
        html.get_url_input("invalid_char")
    assert "not a valid" in "%s" % e

    with pytest.raises(MKUserError) as e:
        html.get_url_input("invalid_char2")
    assert "not a valid" in "%s" % e

    assert html.get_url_input("no_url") == "2"
