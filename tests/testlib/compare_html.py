#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from typing import overload

from bs4 import BeautifulSoup as bs  # type: ignore[import]
from bs4 import NavigableString


def prettify(html_text):
    txt = bs("%s" % html_text, "lxml").prettify()
    return re.sub("\n{2,}", "\n", re.sub(">", ">\n", txt))


@overload
def encode_attribute(value: list) -> list:
    ...


@overload
def encode_attribute(value: str) -> str:
    ...


def encode_attribute(value: list | str) -> list | str:
    if isinstance(value, list):
        return [encode_attribute(v) for v in value]

    return (
        value.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    )


@overload
def undo_encode_attribute(value: list) -> list:
    ...


@overload
def undo_encode_attribute(value: str) -> str:
    ...


def undo_encode_attribute(value: list | str) -> list | str:
    if isinstance(value, list):
        return [undo_encode_attribute(v) for v in value]

    return (
        value.replace("&quot;", '"').replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
    )


@overload
def subber(value: list) -> list:
    ...


@overload
def subber(value: str) -> str:
    ...


def subber(value: list | str) -> list | str:
    if isinstance(value, list):
        return [subber(v) for v in value]

    return re.sub(
        ">",
        " ",
        re.sub(
            "<",
            " ",
            re.sub(
                "\\\\", "", re.sub("'", "&quot;", re.sub('"', "&quot;", re.sub("\n", "", value)))
            ),
        ),
    )


def compare_soup(html1, html2):
    s1 = bs(prettify(html1), "lxml")
    s2 = bs(prettify(html2), "lxml")

    children_1 = list(s1.recursiveChildGenerator())
    children_2 = list(s2.recursiveChildGenerator())

    def unify_attrs(x: str) -> str:
        return encode_attribute(undo_encode_attribute(subber(x)))

    for d1, d2 in zip(children_1, children_2):

        assert isinstance(d1, type(d2)), "\n%s\n%s" % (type(d1), type(d2))

        if isinstance(d1, NavigableString):
            set1 = {x for x in subber(d1).split(" ") if x}
            set2 = {x for x in subber(d2).split(" ") if x}
            assert set1 == set2, "\n%s\n%s\n" % (set1, set2)

        else:
            assert len(list(d1.children)) == len(list(d2.children)), "%s\n%s" % (html1, html2)
            attrs1 = {
                k: [x for x in (v) if x != ""]  #
                for k, v in d1.attrs.items()
                if isinstance(v, list) and len(v) > 0
            }
            attrs2 = {
                k: [x for x in (v) if x != ""]  #
                for k, v in d2.attrs.items()
                if isinstance(v, list) and len(v) > 0
            }

            for key in attrs1.keys():
                assert key in attrs2, "%s\n%s\n\n%s" % (key, d1, d2)
                if key.startswith("on") or key == "style":
                    value1 = attrs1.pop(key, "")
                    assert isinstance(value1, str)
                    value2 = attrs2.pop(key, "")
                    assert isinstance(value2, str)

                    val1 = [unify_attrs(x).strip(" ") for x in value1.split(";") if x]
                    val2 = [unify_attrs(x).strip(" ") for x in value2.split(";") if x]
                    assert val1 == val2, "\n%s\n%s" % (val1, val2)

            assert attrs1 == attrs2, "\n%s\n%s" % (html1, html2)


def compare_html(html1, html2):
    html1 = "%s" % html1
    html2 = "%s" % html2

    # compare tags
    opening_1 = re.findall(r"<[^<]*>", html1)
    opening_2 = re.findall(r"<[^<]*>", html2)
    closing_1 = re.findall(r"</\s*\w+\s*>", html1)
    closing_2 = re.findall(r"</\s*\w+\s*>", html2)

    for x, y in zip(opening_1, opening_2):
        compare_soup(x, y)
    assert closing_1 == closing_2, "\n%s\n%s" % (closing_1, closing_2)

    # compare soup structure
    compare_soup(html1, html2)

    return True
