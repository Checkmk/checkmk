#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'genua_carp'

info = [[[u'carp0', u'2', u'2'], [u'carp1', u'2', u'2'], [u'carp2', u'1', u'0']], []]

discovery = {'': [(u'carp0', None), (u'carp1', None), (u'carp2', None)]}

checks = {
    '': [(u'carp0', {}, [(0, 'Node test: node in carp state master with IfLinkState up', [])]),
         (u'carp1', {}, [(0, 'Node test: node in carp state master with IfLinkState up', [])]),
         (u'carp2', {}, [(1, 'Node test: node in carp state init with IfLinkState down', [])])]
}
