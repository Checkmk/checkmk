#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.gui.availability as availability


@pytest.mark.parametrize("av_rawdata, annotations, result", [({
    ('heute', 'heute'): {
        'CPU load': [{
            'site': 'heute',
            'host_name': 'heute',
            'service_description': 'CPU load',
            'duration': 31282,
            'from': 1590530400,
            'until': 1590561682,
            'state': -1,
            'host_down': 0,
            'in_downtime': 0,
            'in_host_downtime': 0,
            'in_notification_period': 1,
            'in_service_period': 1,
            'is_flapping': 0,
            'log_output': 'OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)'
        }, {
            'site': 'heute',
            'host_name': 'heute',
            'service_description': 'CPU load',
            'duration': 3285,
            'from': 1590561682,
            'until': 1590564967,
            'state': 0,
            'host_down': 0,
            'in_downtime': 0,
            'in_host_downtime': 0,
            'in_notification_period': 1,
            'in_service_period': 1,
            'is_flapping': 0,
            'log_output': 'OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)'
        }]
    }
}, {
    ('heute', 'heute', None): [],
    ('heute', 'heute', 'CPU load'): [{
        'service': 'CPU load',
        'service_state': 2,
        'from': 1590471893.0,
        'until': 1590496168.0,
        'downtime': True,
        'text': 'sdfg\n',
        'hide_from_report': False,
        'date': 1590496182.311858,
        'author': 'cmkadmin'
    }, {
        'service': 'CPU load',
        'service_state': 0,
        'from': 1590496168.0,
        'until': 1590498082.0,
        'downtime': None,
        'text': 'adgf\n',
        'hide_from_report': False,
        'date': 1590498137.9092221,
        'author': 'cmkadmin'
    }, {
        'service': 'CPU load',
        'from': 1590561682.0,
        'until': 1590563170.0,
        'downtime': True,
        'text': 'Annotation with added Downtime\n',
        'hide_from_report': False,
        'date': 1590563194.9577022,
        'author': 'cmkadmin'
    }, {
        'service': 'CPU load',
        'from': 1590563170.0,
        'until': 1590563208.0,
        'downtime': None,
        'text': 'Annotation without Downtime\n',
        'hide_from_report': False,
        'date': 1590563221.8145533,
        'author': 'cmkadmin'
    }, {
        'service': 'CPU load',
        'from': 1590563170.0,
        'until': 1590563194.0,
        'downtime': False,
        'text': 'Annottion with removed downtime\n',
        'hide_from_report': False,
        'date': 1590563227.5949395,
        'author': 'cmkadmin'
    }],
    ('heute', 'heute', 'Filesystem /snap/core18/1705'): [{
        'service': 'Filesystem /snap/core18/1705',
        'from': 1590515368.0,
        'until': 1590515472.0,
        'downtime': True,
        'text': 'sadf\n',
        'hide_from_report': False,
        'date': 1590521475.382475,
        'author': 'cmkadmin'
    }]
}, {
    ('heute', 'heute'): {
        'CPU load': [{
            'site': 'heute',
            'host_name': 'heute',
            'service_description': 'CPU load',
            'duration': 31282,
            'from': 1590530400,
            'until': 1590561682,
            'state': -1,
            'host_down': 0,
            'in_downtime': 0,
            'in_host_downtime': 0,
            'in_notification_period': 1,
            'in_service_period': 1,
            'is_flapping': 0,
            'log_output': 'OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)'
        }, {
            'site': 'heute',
            'host_name': 'heute',
            'service_description': 'CPU load',
            'duration': 1488.0,
            'from': 1590561682,
            'until': 1590563170.0,
            'state': 0,
            'host_down': 0,
            'in_downtime': 1,
            'in_host_downtime': 0,
            'in_notification_period': 1,
            'in_service_period': 1,
            'is_flapping': 0,
            'log_output': 'OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)'
        }, {
            'site': 'heute',
            'host_name': 'heute',
            'service_description': 'CPU load',
            'duration': 24.0,
            'from': 1590563170.0,
            'until': 1590563194.0,
            'state': 0,
            'host_down': 0,
            'in_downtime': 0,
            'in_host_downtime': 0,
            'in_notification_period': 1,
            'in_service_period': 1,
            'is_flapping': 0,
            'log_output': 'OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)'
        }, {
            'site': 'heute',
            'host_name': 'heute',
            'service_description': 'CPU load',
            'duration': 1773.0,
            'from': 1590563194.0,
            'until': 1590564967,
            'state': 0,
            'host_down': 0,
            'in_downtime': 0,
            'in_host_downtime': 0,
            'in_notification_period': 1,
            'in_service_period': 1,
            'is_flapping': 0,
            'log_output': 'OK - 15 min load: 1.78 at 8 Cores (0.22 per Core)'
        }]
    }
})])
def test_reclassify_by_annotations(monkeypatch, av_rawdata, annotations, result):
    monkeypatch.setattr(availability, "load_annotations", lambda: annotations)
    assert availability.reclassify_by_annotations("service", av_rawdata) == result
