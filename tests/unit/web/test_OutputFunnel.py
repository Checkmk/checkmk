#!/usr/bin/python
# call using
# > py.test -s -k test_html_generator.py


import pytest

# Override the global site fixture. Not wanted for git tests!
@pytest.fixture
def site(request):
    pass

# Mark all tests in this file to be executed in the git context
pytestmark = pytest.mark.html_gentest

# external imports
from contextlib import contextmanager


# internal imports
from htmllib import HTML, OutputFunnel
from classes import HTMLOrigTester, Refactored_htmlTester


class OutputFunnelTester(OutputFunnel):

    def __init__(self):
        super(OutputFunnelTester, self).__init__()
        self.written = ""


    def lowlevel_write(self, text):
        self.written += text


#    @ofdecorate
#    def write_test(self, text):
#        self.write("<div>THISISATESTTEXT: %s</div>\n" % text)
#
# decorator for automatical test generation
# def ofdecorate(func):
#    def func_wrapper(html, *args, **kwargs):
#        with html.plugged():
#            func(html, *args, **kwargs)
#            print "_" * 10 + " %s|%s|%s" % (args, kwargs, html.plug_text)
#    return func_wrapper
#
#def test_decorator():
#    print ""
#    html = OutputFunnelTester()
#    html.write_test("HALLO WELT!")
#    print html.written


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
        assert "%s" % e == "Test exception"
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
        html.write("%s\n" % e)
    finally:
        html.write("finally1\n")
    assert html.written == "try1\ntry2\nexcept2\nfinally2\nexcept1\nError\nfinally1\n"


