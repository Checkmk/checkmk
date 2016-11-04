#!/usr/bin/python
# call using
# > py.test -s -k test_HTML_generator.py

# enable imports from web directory
from testlib import cmk_path
import sys
sys.path.insert(0, "%s/web/htdocs" % cmk_path())

# external imports
import re

# internal imports
from htmllib import HTML




def test_class_HTML():

    a = "One"
    b = "two"
    c = "Three"
    d = unicode('u')

    A = HTML(a)
    B = HTML(b)
    C = HTML(c)
    D = HTML(d)

    assert (A + B) == (a + b)
    print A

    A += B
    assert isinstance(A, HTML), A

    a += b
    assert A == a, A

    assert A == a

    assert ("%s" % A) == a

    assert B + C != C + B

    assert HTML(A) == A, "%s %s" % (HTML(A), A)
    assert HTML(a) == A, "%s %s" % (HTML(a), A)

    assert  (A < B) == (a < b), "%s %s" % (A < B, a < b)

    assert (A > B) == (a > b)

    assert A != B

    assert isinstance(HTML(HTML(A)), HTML)
    assert isinstance(HTML(HTML(A)).value, str)

    assert isinstance(A, HTML)
    A += (" JO PICASSO! ")
    assert isinstance(A, HTML)

    assert isinstance(A + "TEST" , str)

    assert isinstance("TEST%s" % A, str)

    assert "test" + C == "test" + c

    assert D == d
    assert "%s" % D == "%s" % d
    assert isinstance(D.value, unicode)

    assert repr(D) == "HTML(%s)" % repr(d)
