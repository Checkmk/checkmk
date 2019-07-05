#!/usr/bin/env python
# -*- coding: utf-8 -*-

import re
from bs4 import BeautifulSoup as bs  # type: ignore
from bs4 import NavigableString


def prettify(html_text):
    txt = bs("%s" % html_text, 'lxml').prettify()
    return re.sub('\n{2,}', '\n', re.sub('>', '>\n', txt))


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
            set1 = {x for x in subber(d1).split(' ') if x}
            set2 = {x for x in subber(d2).split(' ') if x}
            assert set1 == set2, "\n%s\n%s\n" % (set1, set2)

        else:
            assert len(list(d1.children)) == len(list(d2.children)), '%s\n%s' % (html1, html2)
            attrs1 = {k: [x for x in (v) if x != ''] for k, v in d1.attrs.iteritems() if len(v) > 0}
            attrs2 = {k: [x for x in (v) if x != ''] for k, v in d2.attrs.iteritems() if len(v) > 0}

            for key in attrs1.keys():
                assert key in attrs2, '%s\n%s\n\n%s' % (key, d1, d2)
                if key.startswith("on") or key == "style":
                    val1 = [
                        x for x in
                        [unify_attrs(x).strip(' ') for x in attrs1.pop(key, '').split(';') if x]
                    ]
                    val2 = [
                        x for x in
                        [unify_attrs(x).strip(' ') for x in attrs2.pop(key, '').split(';') if x]
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

    for x, y in zip(opening_1, opening_2):
        compare_soup(x, y)
    assert closing_1 == closing_2, '\n%s\n%s' % (closing_1, closing_2)

    # compare soup structure
    compare_soup(html1, html2)

    return True
