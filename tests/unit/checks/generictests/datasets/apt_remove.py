#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'apt'

info = [[u'Remv default-java-plugin [2:1.8-58]'], [u'Remv icedtea-8-plugin [1.6.2-3.1]'],
        [u'Inst default-jre [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64]) []'],
        [u'Inst default-jre-headless [2:1.8-58] (2:1.8-58+deb9u1 Debian:9.11/oldstable [amd64])'],
        [u'Inst icedtea-netx [1.6.2-3.1] (1.6.2-3.1+deb9u1 Debian:9.11/oldstable [amd64])']]

discovery = {'': [(None, {})]}

checks = {
    '': [(None, {'normal': 1, 'removals': 1, 'security': 2},
          [(1, '3 normal updates', [('normal_updates', 3, None, None, None, None)]),
           (1, u'2 auto removals (default-java-plugin, icedtea-8-plugin)',
            [('removals', 2, None, None, None, None)]),
           (0, '0 security updates', [('security_updates', 0, None, None, None, None)])])]
}
