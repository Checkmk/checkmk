#!/usr/biin/python
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
import re
import json
import itertools
import copy
from itertools import izip
import difflib
import warnings
import traceback  # for tracebacks
try:
    import dill.source # for displaying lambda functional code
except:
    print "Cannot import dill.source" in tests/web/tools.py

import time
from bs4 import BeautifulSoup as bs
from bs4 import NavigableString

# internal imports
import tools
from tools import get_attributes
import htmllib
from htmllib import HTML
from classes import HTMLOrigTester, HTMLCheck_MKTester

from html_tests import HtmlTest, build_html_test, save_html_test, load_html_test

from html_tests import get_cartesian_product, build_orig_test
from html_tests import get_tests_args_state, get_tests_args


def test_cartesian_product():

    args = {"arg1": ["val11", "val12"],
            "arg2": ["val21", "val22"], }
    product = get_cartesian_product(args)
    assert len(product) == 4
    assert {"arg1": "val11", "arg2": "val21"} in product
    assert {"arg1": "val11", "arg2": "val22"} in product
    assert {"arg1": "val12", "arg2": "val21"} in product
    assert {"arg1": "val12", "arg2": "val21"} in product

    states = {"attr1": ["val11", "val12"],
              "attr2": ["val21", "val22"] }
    product = get_cartesian_product(states)
    assert len(product) == 4
    assert {"attr1": "val11", "attr2": "val21"} in product
    assert {"attr1": "val11", "attr2": "val22"} in product
    assert {"attr1": "val12", "attr2": "val21"} in product
    assert {"attr1": "val12", "attr2": "val21"} in product


def test_single():
    test_name = "test_1"
    function_name = "empty_icon"
    test = HtmlTest().create(function_name, '''<img src="images/trans.png" class="icon" align=absmiddle />''')
    assert save_html_test(test_name, test)
    test = load_html_test(test_name)[0]
    assert test is not None
    test.run()

    test_name = "test_2"
    function_name = "empty_icon"
    test = build_orig_test(function_name, {}, {})
    assert save_html_test(test_name, test)
    test = load_html_test(test_name)[0]
    assert test is not None
    test.run()


def test_list():
    test_name = "test_3"
    function_name = "unittesting_tester"
    arguments = {"arg1": ["eins", "zwei"], \
                 "arg2": ["drei", "vier"], \
                 "args": [{"sonstige": True}, {"sonstige": False}]}
    state_in  = {"header_sent": [True, False],\
                 "body_classes": ["test"]}
    state_out = {"header_sent": [True, True],\
                 "html_is_open": [True, True]}
    tests = []
    for s_in in get_cartesian_product(state_in):
        for args in get_cartesian_product(arguments):
            tests.append(build_orig_test(function_name, args, state_in={}))

    for test in tests:
        assert test.validate()

    assert save_html_test(test_name, tests)
    tests = load_html_test(test_name)
    assert tests is not None
    for test in tests:
        assert test.run(), "%s" % test

