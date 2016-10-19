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

    A = HTML(a)
    B = HTML(b)
    C = HTML(c)

    assert (A + B) == (a + b)
    print A

    A += B
    a += b

    assert isinstance(A, HTML), A

    assert A == A
    assert A != B

    assert A == a, A
    assert ("%s" % A) == a, A

    assert B + C != C + B
    assert "test" + C == "test" + c
    assert "test" + C + "test" == "test" + c + "test"

    assert HTML(A) == A, "%s %s" % (HTML(A), A)
    assert HTML(a) == A, "%s %s" % (HTML(a), A)

    assert HTML("A") == "A"
    assert HTML("A") <= "B"
    assert HTML("B") >= "A"
    assert (A < B) == (a < b), "%s %s" % (A < B, a < b)
    assert (A > B) == (a > b)

    assert isinstance(HTML(HTML(A)), HTML)
    assert isinstance(HTML(HTML(A)).value, str)

    assert isinstance(A, HTML)
    A += (" JO PICASSO! ")
    assert isinstance(A, HTML)

    assert isinstance(A + "TEST" , str)
    assert isinstance("TEST%s" % A, str)

    assert c in C
    assert C.index(c) == 0
    assert C.index(c) == 0
    assert C.count(c) == 1

    assert A[0] == a[0]


