#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore



checkname = u'megaraid_ldisks'


parsed = {'0/0': {}, '0/1': {}}


discovery = {'': [('0/0', None), ('0/1', None)]}


checks = {'': [('0/0', {}, []), ('0/1', {}, [])]}
