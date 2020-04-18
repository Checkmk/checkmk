#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name

import pytest  # type: ignore[import]

from cmk.gui.htmllib import OutputFunnel
from cmk.gui.http import Response


class OutputFunnelTester(OutputFunnel):
    def __init__(self, response):
        super(OutputFunnelTester, self).__init__(response)
        self.written = ""

    def _lowlevel_write(self, text):
        self.written += text


@pytest.fixture()
def html():
    response = Response()
    return OutputFunnelTester(response)


def test_output_funnel_not_plugged(html):
    html.write("A")
    assert html.written == "A"


def test_output_funnel_plugged(html):
    with html.plugged():
        html.write("B")
        assert html.plug_text == [["B"]]


def test_output_funnel_2nd_plug(html):
    with html.plugged():
        html.write("B")
        assert html.plug_text == [["B"]]
        with html.plugged():
            html.write("C")
            assert html.plug_text == [["B"], ["C"]]
        assert html.plug_text == [["B", "C"]]
    assert html.written == "BC"


def test_output_funnel_drain(html):
    with html.plugged():
        html.write("A")
        text = html.drain()
        assert text == "A"

        html.write("B")
        assert html.plug_text == [["B"]]
    assert html.written == "B"


def test_output_funnel_context_nesting(html):
    html.write("A")
    assert html.written == "A"
    with html.plugged():
        html.write("B")
        assert html.plug_text == [["B"]]
        with html.plugged():
            html.write("C")
            assert html.plug_text == [["B"], ["C"]]
        assert html.plug_text == [["B", "C"]]
    assert html.written == "ABC"


def test_output_funnel_context_drain(html):
    html.write("A")
    assert html.written == "A"
    with html.plugged():
        html.write("B")
        assert html.plug_text == [['B']]
        code = html.drain()
        assert html.plug_text == [[]]
    assert code == 'B'
    assert html.written == "A"


def test_output_funnel_context_raise(html):
    try:
        html.write("A")
        assert html.written == "A"
        with html.plugged():
            html.write("B")
            assert html.plug_text == [['B']]
            raise Exception("Test exception")
    except Exception as e:
        assert "%s" % e == "Test exception"
    finally:
        assert html.plug_text == []


def test_output_funnel_try_finally(html):
    try:
        html.write("try1\n")
        try:
            html.write("try2\n")
            raise Exception("Error")
        except Exception as e:
            html.write("except2\n")
            raise
        finally:
            html.write("finally2\n")
    except Exception as e:
        html.write("except1\n")
        html.write("%s\n" % e)
    finally:
        html.write("finally1\n")
    assert html.written == "try1\ntry2\nexcept2\nfinally2\nexcept1\nError\nfinally1\n"
