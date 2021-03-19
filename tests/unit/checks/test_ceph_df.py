#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from testlib import Check  # type: ignore[import]
import pytest


def test_sanitize_line():
    input_ = [
        u'cephfs_data', u'1', u'N/A', u'N/A', u'1.6', u'GiB', u'1.97', u'77', u'GiB', u'809',
        u'809', u'33', u'B', u'177', u'KiB', u'4.7', u'GiB'
    ]
    expected = [
        u'cephfs_data', u'1', u'N/A', u'N/A', u'1.6GiB', u'1.97', u'77GiB', u'809', u'809', u'33B',
        u'177KiB', u'4.7GiB'
    ]
    check = Check('ceph_df')
    sanitize_line = check.context['_sanitize_line']
    assert expected == sanitize_line(input_)
