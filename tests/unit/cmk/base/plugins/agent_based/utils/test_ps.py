#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.plugins.agent_based.agent_based_api.v1.type_defs import Parameters
from cmk.base.plugins.agent_based.agent_based_api.v1 import HostLabel
from cmk.base.plugins.agent_based.utils import ps

pytestmark = pytest.mark.checks


def test_host_labels_ps_no_match_attr():
    section = (
        1,
        [
            (
                ps.ps_info(
                    "(root,4056,1512,0.0/52-04:56:05,5689)".split()),  # type: ignore[call-arg]
                ["/usr/lib/ssh/sshd"],
            ),
        ])
    params = [
        Parameters({
            "default_params": {},
            "descr": "SSH",
            "match": "~.*ssh?",
            "user": "flynn",
            "label": {
                'marco': 'polo'
            },
        }),
        Parameters({}),
    ]
    assert list(ps.host_labels_ps(params, section)) == []


def test_host_labels_ps_no_match_pattern():
    section = (
        1,
        [
            (
                ps.ps_info(
                    "(root,4056,1512,0.0/52-04:56:05,5689)".split()),  # type: ignore[call-arg]
                ["/usr/lib/ssh/sshd"],
            ),
        ])
    params = [
        Parameters({
            "default_params": {},
            "descr": "SSH",
            "match": "~wat?",
            "label": {
                'marco': 'polo'
            },
        }),
        Parameters({}),
    ]
    assert list(ps.host_labels_ps(params, section)) == []


def test_host_labels_ps_match():
    section = (
        1,
        [
            (
                ps.ps_info(
                    "(root,4056,1512,0.0/52-04:56:05,5689)".split()),  # type: ignore[call-arg]
                ["/usr/lib/ssh/sshd"],
            ),
        ])
    params = [
        Parameters({
            "default_params": {},
            "descr": "SSH",
            "match": "~.*ssh?",
            "label": {
                'marco': 'polo'
            },
        }),
        Parameters({}),
    ]
    assert list(ps.host_labels_ps(params, section)) == [HostLabel('marco', 'polo')]


@pytest.mark.parametrize("ps_line, ps_pattern, user_pattern, result", [
    (["test", "ps"], "", None, True),
    (["test", "ps"], "ps", None, True),
    (["test", "ps"], "ps", "root", False),
    (["test", "ps"], "ps", "~.*y$", False),
    (["test", "ps"], "ps", "~.*t$", True),
    (["test", "ps"], "sp", "~.*t$", False),
    (["root", "/sbin/init", "splash"], "/sbin/init", None, True),
])
def test_process_matches(ps_line, ps_pattern, user_pattern, result):
    psi = ps.ps_info(ps_line[0])  # type: ignore[call-arg]
    matches_attr = ps.process_attributes_match(psi, user_pattern, (None, False))
    matches_proc = ps.process_matches(ps_line[1:], ps_pattern)

    assert (matches_attr and matches_proc) == result


@pytest.mark.parametrize("ps_line, ps_pattern, user_pattern, match_groups, result", [
    (["test", "ps"], "", None, None, True),
    (["test", "123_foo"], "~.*/(.*)_foo", None, ['123'], False),
    (["test", "/a/b/123_foo"], "~.*/(.*)_foo", None, ['123'], True),
    (["test", "123_foo"], "~.*\\\\(.*)_foo", None, ['123'], False),
    (["test", "c:\\a\\b\\123_foo"], "~.*\\\\(.*)_foo", None, ['123'], True),
])
def test_process_matches_match_groups(ps_line, ps_pattern, user_pattern, match_groups, result):
    psi = ps.ps_info(ps_line[0])  # type: ignore[call-arg]
    matches_attr = ps.process_attributes_match(psi, user_pattern, (None, False))
    matches_proc = ps.process_matches(ps_line[1:], ps_pattern, match_groups)

    assert (matches_attr and matches_proc) == result


@pytest.mark.parametrize("attribute, pattern, result", [
    ("user", "~user", True),
    ("user", "user", True),
    ("user", "~foo", False),
    ("user", "foo", False),
    ("user", "~u.er", True),
    ("user", "u.er", False),
    ("users", "~user", True),
    ("users", "user", False),
])
def test_ps_match_user(attribute, pattern, result):
    assert ps.match_attribute(attribute, pattern) == result


@pytest.mark.parametrize(
    "service_description, matches, result",
    [
        ("PS %2 %1", ["service", "check"], "PS check service"),
        ("PS %2 %1", ["service", "check", "sm"], "PS check service"),
        ("PS %s %s", ["service", "rename"], "PS service rename"),
        ("My Foo Service", ("Moo", "Cow"), "My Foo Service"),
        ("My %sService", ("", "Cow"), "My Service"),
        ("My %sService", (None, "Cow"), "My Service"),
        ("My %s Service", ("Moo", "Cow"), "My Moo Service"),
        ("My %2 Service sais '%1!'", ("Moo", "Cow"), "My Cow Service sais 'Moo!'"),
        # the following is not very sensible, and not allowed by WATO configuration since 1.7.0i1.
        # Make sure we know what's happening, though
        ("PS %2 %s", ["service", "rename"], "PS rename rename"),
        ("%s %2 %s %1", ("one", "two", "three", "four"), "three two four one")
    ])
def test_replace_service_description(service_description, matches, result):
    assert ps.replace_service_description(service_description, matches, "") == result


def test_replace_service_description_exception():
    with pytest.raises(ValueError, match="1 replaceable elements"):
        ps.replace_service_description("%s", [], "")


PROCESSES = [[
    ("name", ("/bin/sh", "")),
    ("user", ("root", "")),
    ("virtual size", (1234, "kB")),
    ("arguments", ("--feen-gibt-es-nicht quark --invert", "")),
]]


@pytest.mark.parametrize("processes, formatted_list, html_flag", [
    (PROCESSES, ("name /bin/sh, user root, virtual size 1234kB,"
                 " arguments --feen-gibt-es-nicht quark --invert\r\n"), False),
    (PROCESSES, ("<table><tr><th>name</th><th>user</th><th>virtual size</th><th>arguments</th></tr>"
                 "<tr><td>/bin/sh</td><td>root</td><td>1234kB</td>"
                 "<td>--feen-gibt-es-nicht quark --invert</td></tr></table>"), True),
])
def test_format_process_list(processes, formatted_list, html_flag):
    assert ps.format_process_list(processes, html_flag) == formatted_list


def test_unused_value_remover():

    value_store_test = {
        "test": {
            "unused": (23., 23.),
            "updated": (42., 42.),
        },
    }

    with ps.unused_value_remover(value_store_test, "test") as value_store:
        value_store["updated"] = (3.14, 3.14)
        value_store["new"] = (2.7, 2.7)

    assert value_store_test == {
        "test": {
            "updated": (3.14, 3.14),
            "new": (2.7, 2.7),
        },
    }
