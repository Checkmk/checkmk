#!/usr/bin/env python

import pytest  # type: ignore

from cmk.gui.htmllib import OutputFunnel


class OutputFunnelTester(OutputFunnel):
    def __init__(self):
        super(OutputFunnelTester, self).__init__()
        self.written = ""


    def _lowlevel_write(self, text):
        self.written += text


@pytest.fixture()
def html():
    return OutputFunnelTester()


def test_output_funnel_not_plugged(html):
    html.write("A")
    assert html.written == "A"


def test_output_funnel_plugged(html):
    html.plug()
    html.write("B")
    assert html.plug_text == [["B"]]


def test_output_funnel_2nd_plug(html):
    html.plug()
    html.write("B")
    assert html.plug_text == [["B"]]

    html.plug()
    html.write("C")
    assert html.plug_text == [["B"], ["C"]]

    html.unplug()
    assert html.plug_text == [["B", "C"]]

    html.unplug()
    assert html.written == "BC"


def test_output_funnel_drain(html):
    html.plug()
    html.write("A")
    text = html.drain()
    assert text == "A"

    html.write("B")
    assert html.plug_text == [["B"]]
    html.unplug()
    assert html.written == "B"


def test_output_funnel_flush(html):
    html.plug()
    html.write("A")
    assert html.plug_text == [["A"]]
    html.flush()
    assert html.written == "A"
    assert html.plug_text == [[]]
    html.unplug()
    assert html.written == "A"


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
        assert not html.is_plugged()


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
