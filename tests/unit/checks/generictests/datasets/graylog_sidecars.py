#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'graylog_sidecars'

freeze_time = '2019-10-24 10:48:00'

info = [
    [
        u'{"collectors": null, "node_name": "debian", "assignments": [], "node_id": "0ec4c2eb-6240-4f34-a0b2-00d075a50bb3", "node_details": {"metrics": {"disks_75": ["/ (76%)"], "load_1": 0.0, "cpu_idle": 99.3}, "ip": "192.168.11.187", "operating_system": "Linux", "status": {"status": 1, "message": "Received no ping signal from sidecar", "collectors": []}, "log_file_list": null}, "active": false, "sidecar_version": "1.0.2", "last_seen": "2019-10-23T11:36:26.402Z"}'
    ],
    [
        u'{"collectors": null, "node_name": "testserver", "assignments": [{"collector_id": "5da58757e2847e0602771e75", "configuration_id": "5da6d6da96c943060a7e1fed"}], "node_id": "31c3e8f9-a6b2-41d4-be78-f6273c3cb0e5", "node_details": {"metrics": {"disks_75": ["/snap/gnome-3-28-1804/67 (100%)", "/snap/gnome-3-28-1804/71 (100%)", "/snap/core18/1223 (100%)", "/snap/gnome-characters/317 (100%)", "/snap/core/7713 (100%)", "/snap/core18/1192 (100%)", "/snap/gnome-characters/296 (100%)", "/snap/spotify/36 (100%)", "/snap/gnome-3-26-1604/92 (100%)", "/snap/core/7917 (100%)", "/snap/gnome-calculator/406 (100%)", "/snap/spotify/35 (100%)", "/snap/gnome-logs/73 (100%)", "/snap/gtk-common-themes/1353 (100%)", "/snap/gnome-system-monitor/95 (100%)", "/snap/gnome-system-monitor/100 (100%)", "/snap/gnome-calculator/501 (100%)", "/snap/gnome-logs/81 (100%)", "/snap/gnome-3-26-1604/90 (100%)", "/snap/gtk-common-themes/1313 (100%)"], "load_1": 0.91, "cpu_idle": 87.59}, "ip": "192.168.11.221", "operating_system": "Linux", "status": {"status": 1, "message": "Received no ping signal from sidecar", "collectors": [{"status": 1, "verbose_message": "", "message": "Received no ping signal from sidecar", "collector_id": "5da58757e2847e0602771e75"}]}, "log_file_list": null}, "active": false, "sidecar_version": "1.0.2", "last_seen": "2019-10-21T08:01:08.579Z"}'
    ]
]

discovery = {'': [(u'debian', {}), (u'testserver', {})]}

checks = {
    '': [
        (
            u'debian', {
                'failing_upper': (1, 1),
                'stopped_upper': (1, 1),
                'running_lower': (1, 0)
            }, [
                (2, 'Active: no', []),
                (0, 'Last seen: 2019-10-23 13:36:26', []),
                (0, 'Before: 23 hours 11 minutes', []),
                (2, u'Collectors: Received no ping signal from sidecar', [])
            ]
        ),
        (
            u'testserver', {
                'failing_upper': (1, 1),
                'stopped_upper': (1, 1),
                'running_lower': (1, 0)
            }, [
                (2, 'Active: no', []),
                (0, 'Last seen: 2019-10-21 10:01:08', []),
                (0, 'Before: 3 days 2 hours', []),
                (2, u'Collectors: Received no ping signal from sidecar', []),
                (2, 'see long output for more details', []),
                (
                    2,
                    u'\nID: 5da58757e2847e0602771e75, Message: Received no ping signal from sidecar',
                    []
                )
            ]
        )
    ]
}
