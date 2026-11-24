#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from urllib.parse import urlencode

from werkzeug.test import create_environ

from cmk.gui.http import Request
from cmk.gui.monitor.legacy_context import encode_unapplied_filters, read_unapplied_filter_titles

_TITLES = {"wato_folder": "Folder", "hostgroup": "Host group"}


def _request(vars_: list[tuple[str, str]]) -> Request:
    return Request(create_environ(query_string=urlencode(vars_)))


def test_a_link_that_took_over_every_filter_names_none() -> None:
    assert encode_unapplied_filters([]) == []


def test_the_page_names_by_their_titles_the_filters_a_link_could_not_take_over() -> None:
    request = _request(encode_unapplied_filters(["wato_folder", "hostgroup"]))

    assert read_unapplied_filter_titles(request, _TITLES.get) == [
        ("wato_folder", "Folder"),
        ("hostgroup", "Host group"),
    ]


def test_the_page_names_no_filter_that_does_not_exist() -> None:
    request = _request([("unapplied", "wato_folder,Click here!")])

    assert read_unapplied_filter_titles(request, _TITLES.get) == [("wato_folder", "Folder")]


def test_the_page_names_a_filter_once() -> None:
    request = _request([("unapplied", "wato_folder,wato_folder")])

    assert read_unapplied_filter_titles(request, _TITLES.get) == [("wato_folder", "Folder")]


def test_a_page_opened_without_the_variable_names_no_filter() -> None:
    assert read_unapplied_filter_titles(_request([]), _TITLES.get) == []
