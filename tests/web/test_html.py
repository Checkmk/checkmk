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

    assert HTML() == HTML('')
    assert HTML().join([A, B]) == A + B
    assert HTML().join([a, b]) == a + b
    assert ''.join(map(str, [A, B])) == A + B

    assert isinstance(A + B, HTML), type(A + B)
    assert isinstance(HTML('').join([A, B]), HTML)
    assert isinstance(HTML().join([A, B]), HTML)
    assert isinstance(HTML('').join([a, b]), HTML)
    assert isinstance("TEST" + HTML(), HTML)
    assert isinstance(HTML() + "TEST", HTML)
    assert isinstance("TEST" + HTML() + "TEST" , HTML)


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

    assert isinstance(A + "TEST" , HTML)

    assert isinstance("TEST%s" % A, str)

    assert "test" + C == "test" + c

    assert D == d
    assert "%s" % D == "%s" % d
    assert isinstance(D.value, unicode)

    assert repr(D) == "HTML(%s)" % repr(d)

