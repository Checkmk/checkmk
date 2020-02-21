#!/usr/bin/env python
# encoding: utf-8

import pytest  # type: ignore
from cmk.gui.exceptions import MKUserError
from cmk.gui.globals import html


@pytest.mark.parametrize("invalid_url", [
    "http://localhost/",
    "://localhost",
    "localhost:80/bla",
])
def test_get_url_input_invalid_urls(register_builtin_html, invalid_url):
    html.request.set_var("varname", invalid_url)

    with pytest.raises(MKUserError) as e:
        html.get_url_input("varname")
    assert "not a valid URL" in "%s" % e


def test_get_url_input(register_builtin_html):
    html.request.set_var("url", "view.py?bla=blub")
    html.request.set_var("no_url", "2")
    html.request.set_var("invalid_url", "http://bla/")
    html.request.set_var("invalid_char", "viäw.py")
    html.request.set_var("invalid_char2", "vi+w.py")

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
