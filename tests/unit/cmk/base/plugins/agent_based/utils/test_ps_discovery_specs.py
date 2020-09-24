#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from cmk.base.discovered_labels import DiscoveredHostLabels

from cmk.base.plugins.agent_based.agent_based_api.v1 import HostLabel, type_defs
from cmk.base.plugins.agent_based.utils import ps

pytestmark = pytest.mark.checks


def test_get_discovery_specs():
    assert ps.get_discovery_specs([
        type_defs.Parameters(par) for par in [
            {
                "default_params": {},
                "descr": "smss",
                "match": "~smss.exe"
            },
            {
                "default_params": {
                    "cpulevels": (90.0, 98.0),
                    "handle_count": (1000, 2000),
                    "levels": (1, 1, 99999, 99999),
                    "max_age": (3600, 7200),
                    "resident_levels": (104857600, 209715200),
                    "resident_levels_perc": (25.0, 50.0),
                    "single_cpulevels": (90.0, 98.0),
                    "virtual_levels": (1073741824000, 2147483648000),
                },
                "descr": "svchost",
                "match": "svchost.exe"
            },
            {
                "default_params": {
                    "process_info": "text"
                },
                "match": "~.*(fire)fox",
                "descr": "firefox is on %s",
                "user": None,
            },
            {
                "default_params": {
                    "process_info": "text"
                },
                "match": "~.*(fire)fox",
                "descr": "firefox is on %s",
                "user": None,
                "label": DiscoveredHostLabels(HostLabel(u'marco', u'polo'),
                                              HostLabel(u'peter', u'pan')),
            },
            {
                "default_params": {
                    "cpu_rescale_max": True,
                    "cpu_average": 15,
                    "process_info": "html",
                    "resident_levels_perc": (25.0, 50.0),
                    "virtual_levels": (1024**3, 2 * 1024**3),
                    "resident_levels": (1024**3, 2 * 1024**3),
                    "icon": "emacs.png",
                },
                "descr": "emacs %u",
                "match": "emacs",
                "user": False
            },
            {
                "default_params": {
                    "max_age": (3600, 7200),
                    "resident_levels_perc": (25.0, 50.0),
                    "single_cpulevels": (90.0, 98.0),
                    "resident_levels": (104857600, 209715200),
                },
                "match": "~.*cron",
                "descr": "cron",
                "user": "root"
            },
            {
                "default_params": {},
                "descr": "sshd",
                "match": "~.*sshd"
            },
            {
                'default_params': {},
                'descr': 'PS counter',
                'user': 'zombie',
            },
            {
                "default_params": {
                    "process_info": "text"
                },
                "match": r"~/omd/sites/(\w+)/lib/cmc/checkhelper",
                "descr": "Checkhelpers %s",
                "user": None,
            },
            {
                "default_params": {
                    "process_info": "text"
                },
                "match": r"~/omd/sites/\w+/lib/cmc/checkhelper",
                "descr": "Checkhelpers Overall",
                "user": None,
            },
            # Legacy-style rule without default_params. This is from v1.5 or before, since the key
            # default_params was made non-optional in v1.6.
            {
                'perfdata': True,
                'levels': (1, 1, 20, 20),
                'descr': 'cron',
                'match': '/usr/sbin/cron',
                'user': None,
            },
            {},
        ]
    ]) == [
        ("smss", "~smss.exe", None, (None, False), DiscoveredHostLabels(), {
            'cpu_rescale_max': None
        }),
        ("svchost", "svchost.exe", None, (None, False), {}, {
            "cpulevels": (90.0, 98.0),
            'cpu_rescale_max': None,
            "handle_count": (1000, 2000),
            "levels": (1, 1, 99999, 99999),
            "max_age": (3600, 7200),
            "resident_levels": (104857600, 209715200),
            "resident_levels_perc": (25.0, 50.0),
            "single_cpulevels": (90.0, 98.0),
            "virtual_levels": (1073741824000, 2147483648000),
        }),
        ("firefox is on %s", "~.*(fire)fox", None, (None, False), {}, {
            "process_info": "text",
            'cpu_rescale_max': None,
        }),
        ("firefox is on %s", "~.*(fire)fox", None, (None, False),
         DiscoveredHostLabels(HostLabel(u'marco', u'polo'), HostLabel(u'peter', u'pan')), {
             "process_info": "text",
             'cpu_rescale_max': None,
         }),
        ("emacs %u", "emacs", False, (None, False), {}, {
            "cpu_average": 15,
            'cpu_rescale_max': True,
            "process_info": "html",
            "resident_levels_perc": (25.0, 50.0),
            "virtual_levels": (1024**3, 2 * 1024**3),
            "resident_levels": (1024**3, 2 * 1024**3),
            "icon": "emacs.png",
        }),
        ("cron", "~.*cron", "root", (None, False), {}, {
            "max_age": (3600, 7200),
            'cpu_rescale_max': None,
            "resident_levels_perc": (25.0, 50.0),
            "single_cpulevels": (90.0, 98.0),
            "resident_levels": (104857600, 209715200)
        }),
        ("sshd", "~.*sshd", None, (None, False), {}, {
            'cpu_rescale_max': None
        }),
        ('PS counter', None, 'zombie', (None, False), {}, {
            'cpu_rescale_max': None
        }),
        ("Checkhelpers %s", r"~/omd/sites/(\w+)/lib/cmc/checkhelper", None, (None, False), {}, {
            "process_info": "text",
            'cpu_rescale_max': None,
        }),
        ("Checkhelpers Overall", r"~/omd/sites/\w+/lib/cmc/checkhelper", None, (None, False), {}, {
            "process_info": "text",
            'cpu_rescale_max': None,
        }),
        ('cron', '/usr/sbin/cron', None, (None, False), {}, {
            'cpu_rescale_max': None,
            'descr': 'cron',
            'levels': (1, 1, 20, 20),
            'match': '/usr/sbin/cron',
            'perfdata': True,
            'user': None
        }),
    ]
