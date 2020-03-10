#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for check devolpment

These are meant to be exposed in the API
"""
import re
import itertools
from cmk.base.api.agent_based.section_types import SNMPDetectSpec

#     ____       _            _
#    |  _ \  ___| |_ ___  ___| |_   ___ _ __   ___  ___
#    | | | |/ _ \ __/ _ \/ __| __| / __| '_ \ / _ \/ __|
#    | |_| |  __/ ||  __/ (__| |_  \__ \ |_) |  __/ (__
#    |____/ \___|\__\___|\___|\__| |___/ .__/ \___|\___|
#                                      |_|


def all_of(spec_0, spec_1, *specs):
    # type: (SNMPDetectSpec, SNMPDetectSpec, SNMPDetectSpec) -> SNMPDetectSpec
    reduced = [l0 + l1 for l0, l1 in itertools.product(spec_0, spec_1)]
    if not specs:
        return reduced
    return all_of(reduced, *specs)


def any_of(*specs):
    # type: (SNMPDetectSpec) -> SNMPDetectSpec
    return sum(specs, [])


def _negate(spec):
    # type: (SNMPDetectSpec) -> SNMPDetectSpec
    assert len(spec) == 1
    assert len(spec[0]) == 1
    return [[(spec[0][0][0], spec[0][0][1], not spec[0][0][2])]]


def contains(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, '.*%s.*' % re.escape(value), True)]]


def startswith(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, '^%s.*' % re.escape(value), True)]]


def endswith(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, '.*%s$' % re.escape(value), True)]]


def equals(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return [[(oidstr, '^%s$' % re.escape(value), True)]]


def exists(oidstr):
    # type: (str) -> SNMPDetectSpec
    return [[(oidstr, '.*', True)]]


def not_contains(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(contains(oidstr, value))


def not_startswith(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(startswith(oidstr, value))


def not_endswith(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(endswith(oidstr, value))


def not_equals(oidstr, value):
    # type: (str, str) -> SNMPDetectSpec
    return _negate(equals(oidstr, value))


def not_exists(oidstr):
    # type: (str) -> SNMPDetectSpec
    return _negate(exists(oidstr))
