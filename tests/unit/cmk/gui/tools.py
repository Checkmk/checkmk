#!/usr/biin/python
# call using
# > py.test -s -k test_html_generator.py

# external imports
import re
import difflib
import warnings
import traceback  # for tracebacks
try:
    import dill.source  # for displaying lambda functional code
except:
    print "Cannot import dill.source" in tests / web / tools.py

import time
from bs4 import BeautifulSoup as bs
from bs4 import NavigableString

# internal imports
from cmk.gui.htmllib import HTML


class bcolors(object):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def timeit(method):
    def timed(*args, **kw):
        ts = time.time()
        result = method(*args, **kw)
        te = time.time()
        print '%r %2.2f sec' % \
              (method.__name__, te-ts)
        return result

    return timed


def prettify(html_text):
    txt = bs("%s" % html_text, 'lxml').prettify()
    return re.sub('\n{2,}', '\n', re.sub('>', '>\n', txt))


class HTMLCode(object):
    def __init__(self, value):
        self.value = value

    def prettify(self):
        return bs(self.value, 'lxml').prettify()


def encode_attribute(value):
    if isinstance(value, list):
        return map(encode_attribute, value)

    return value.replace("&", "&amp;")\
                .replace('"', "&quot;")\
                .replace("<", "&lt;")\
                .replace(">", "&gt;")


def undo_encode_attribute(value):
    if isinstance(value, list):
        return map(undo_encode_attribute, value)

    return value.replace("&quot;", '"')\
                .replace("&lt;", '<')\
                .replace("&gt;", '>')\
                .replace("&amp;", '&')\


def subber(value):
    if isinstance(value, list):
        return map(subber, value)

    return re.sub('>', ' ',\
           re.sub('<', ' ',\
           re.sub('\\\\', '',\
           re.sub("'", '&quot;',\
           re.sub('"', '&quot;',\
           re.sub('\n', '', value))))))


def compare_soup(html1, html2):
    s1 = bs(prettify(html1), 'lxml')
    s2 = bs(prettify(html2), 'lxml')

    children_1 = list(s1.recursiveChildGenerator())
    children_2 = list(s2.recursiveChildGenerator())

    unify_attrs = lambda x: encode_attribute(undo_encode_attribute(subber(x)))

    for d1, d2 in zip(children_1, children_2):

        assert type(d1) == type(d2), "\n%s\n%s" % (type(d1), type(d2))

        if isinstance(d1, NavigableString):
            set1 = set([x for x in subber(d1).split(' ') if x])
            set2 = set([x for x in subber(d2).split(' ') if x])
            assert set1 == set2, "\n%s\n%s\n" % (set1, set2)

        else:
            assert len(list(d1.children)) == len(list(d2.children)), '%s\n%s' % (html1, html2)
            attrs1 = {k: [x for x in (v) if x != ''] for k, v in d1.attrs.iteritems() if len(v) > 0}
            attrs2 = {k: [x for x in (v) if x != ''] for k, v in d2.attrs.iteritems() if len(v) > 0}

            for key in attrs1.keys():
                assert key in attrs2, '%s\n%s\n\n%s' % (key, d1, d2)
                if key.startswith("on") or key == "style":
                    val1 = [
                        x for x in map(lambda x: unify_attrs(x).strip(' '),
                                       attrs1.pop(key, '').split(';')) if x
                    ]
                    val2 = [
                        x for x in map(lambda x: unify_attrs(x).strip(' '),
                                       attrs2.pop(key, '').split(';')) if x
                    ]
                    assert val1 == val2, '\n%s\n%s' % (val1, val2)

            assert attrs1 == attrs2, '\n%s\n%s' % (html1, html2)


def compare_html(html1, html2):
    html1 = "%s" % html1
    html2 = "%s" % html2

    # compare tags
    opening_1 = re.findall(r'<[^<]*>', html1)
    opening_2 = re.findall(r'<[^<]*>', html2)
    closing_1 = re.findall(r'</\s*\w+\s*>', html1)
    closing_2 = re.findall(r'</\s*\w+\s*>', html2)

    map(lambda x: compare_soup(x[0], x[1]), zip(opening_1, opening_2))
    assert closing_1 == closing_2, '\n%s\n%s' % (closing_1, closing_2)

    # compare soup structure
    compare_soup(html1, html2)

    return True


def test_compare_soup():

    html1 = '<tag> <div class=\"test\"> Test <img src = \"Yo!\" /> </div> Hallo Welt! </tag>'
    compare_soup(html1, html1)


def get_attributes(html_object):
    attrs = {var: getattr(html_object, var) for var in dir(html_object)\
                if not callable(getattr(html_object,var)) and not var.startswith("__")}
    attrs = {
        key: val for key, val in attrs.iteritems() if key not in
        ['start_time', 'last_measurement', 'plugged_text', 'indent_level', 'escaper', 'encoder'] and
        not key.startswith("_unescaper")
    }
    return attrs


def compare_attributes(attrs1, attrs2):
    # compare variables
    exclusives_1 = {var for var in attrs1 if var not in attrs2}
    exclusives_2 = {var for var in attrs2 if var not in attrs1}

    # compare variable_content
    for key in attrs1:
        if key in exclusives_1:
            continue

        assert attrs1[key] == attrs2[key],\
            "Values for attribute %s differ: %s VS. %s" % (key, attrs1[key], attrs2[key])

    return True


def compare_attributes_of(old, new):

    vars_old = get_attributes(old)
    vars_new = get_attributes(new)

    compare_attributes(vars_old, vars_new)


# For classes using the drain() functionality
def compare_and_empty(old, new):

    # compare html code
    compare_html(old.drain(), new.drain())

    # compare attribute values
    compare_attributes_of(old, new)


def _html_generator_test(old, new, fun, reinit=True):
    with old.plugged():
        with new.plugged():
            vars_before = get_attributes(old)

            fun(old)
            fun(new)

            vars_after = get_attributes(old)

            # compare html code
            old_html = old.drain()
            new_html = new.drain()
            compare_html(old_html, new_html)

            # compare attribute values
            compare_attributes_of(old, new)

            if reinit:
                old.__init__()
                new.__init__()


# Try to render and write the html using the function fun. (e.g. old.open_head())
# Resets the whole element
def html_generator_test(old, new, fun, attributes=None, reinit=True):

    if attributes and not isinstance(attributes, list):
        attributes = [attributes]

    if reinit:
        try:
            print bcolors.HEADER + "TESTING" + bcolors.ENDC + dill.source.getsource(fun)
        except:
            print "Cannot import dill.source" in tests / web / tools.py

    if attributes:
        attr = attributes.pop(0)

        setattr(old, attr, True)
        setattr(new, attr, True)
        html_generator_test(old, new, fun, attributes=attributes, reinit=False)

        setattr(old, attr, False)
        setattr(new, attr, False)
        html_generator_test(old, new, fun, attributes=attributes, reinit=False)

    else:
        _html_generator_test(old, new, fun, reinit=reinit)


def gentest(old, new, fun, **attrs):
    html_generator_test(old, new, fun, **attrs)


import inspect


def _get_fun_call(fun):
    funcall = re.sub(".*lambda x: x.", "html.", inspect.getsource(fun))
    funcall = re.sub('\n', ' ', funcall)
    funcall = re.sub('[ ]+', ' ', funcall).rstrip(' ')[:-1]
    return funcall


def _get_fun_name(fun):
    return re.search("html.([^(]+)\(", _get_fun_call(fun)).group(1)


def write_unittest_file(old, fun, result, vars_before, vars_after):

    print inspect.getargvalues(fun)

    funcall = _get_fun_call(fun)
    funname = _get_fun_name(fun)
    print funname
    print [var for var in vars_before if var not in vars_after]

    with open("unittest_files/%s.unittest" % funname, "a+") as ufile:
        ufile.write("%s" % funcall)
        ufile.write("\n------------------------------\n")
        ufile.write("%s\n\n" % result)
