#!/usr/bin/env python

import pytest

from htmllib import OutputFunnel


class OutputFunnelTester(OutputFunnel):
    def __init__(self):
        super(OutputFunnelTester, self).__init__()
        self.written = ""


    def _lowlevel_write(self, text):
        self.written += text


def test_plug():
    html = OutputFunnelTester()

    html.write("A")
    assert html.written == "A"
    html.plug()
    html.write("B")
    assert html.plug_text == [["B"]]
    html.plug()
    html.write("C")
    assert html.plug_text == [["B"], ["C"]]
    html.unplug()
    assert html.plug_text == [["B", "C"]]
    html.unplug()
    assert html.written == "ABC"


def test_drain():
    html = OutputFunnelTester()

    html.plug()
    html.write("A")
    text = html.drain()
    assert text == "A"
    html.write("B")
    assert html.plug_text == [["B"]]
    html.unplug()
    assert html.written == "B"


def test_flush():
    html = OutputFunnelTester()

    html.plug()
    html.write("A")
    html.plug_text == ["A"]
    html.flush()
    assert html.written == "A"
    assert html.plug_text == [[]]
    html.unplug()
    assert html.written == "A"


def test_context_nesting():
    html = OutputFunnelTester()

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


def test_context_drain():
    html = OutputFunnelTester()

    html.write("A")
    assert html.written == "A"
    with html.plugged():
        html.write("B")
        assert html.plug_text == [['B']]
        code = html.drain()
        assert html.plug_text == [[]]
    assert code == 'B'
    assert html.written == "A"


def test_context_raise():
    html = OutputFunnelTester()

    try:
        html.write("A")
        assert html.written == "A"
        with html.plugged():
            html.write("B")
            assert html.plug_text == [['B']]
            raise Exception("Test exception")
    except Exception, e:
        assert e.message == "Test exception"
    finally:
        assert not html.is_plugged()


def test_try_finally():
    html = OutputFunnelTester()
    try:
        html.write("try1\n")
        try:
            html.write("try2\n")
            raise Exception("Error")
        except Exception, e:
            html.write("except2\n")
            raise
        finally:
            html.write("finally2\n")
    except Exception, e:
        html.write("except1\n")
        html.write("%s\n" % e.message)
    finally:
        html.write("finally1\n")
    assert html.written == "try1\ntry2\nexcept2\nfinally2\nexcept1\nError\nfinally1\n"


