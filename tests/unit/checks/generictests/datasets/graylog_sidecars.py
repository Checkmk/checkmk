# -*- encoding: utf-8
# yapf: disable
checkname = 'graylog_sidecars'

freeze_time = '2019-10-18 14:42:00'

info = [
    [
        u'{"sort": "node_name", "pagination": {"count": 1, "per_page": 50, "total": 1, "page": 1}, "sidecars": [{"collectors": null, "node_name": "testserver", "assignments": [{"collector_id": "5da58757e2847e0602771e78", "configuration_id": "5da8af643a058606098b970c"}, {"collector_id": "5da58757e2847e0602771e75", "configuration_id": "5da6d6da96c943060a7e1fed"}], "node_id": "31c3e8f9-a6b2-41d4-be78-f6273c3cb0e5", "node_details": {"metrics": {"disks_75": ["/snap/spotify/35 (100%)", "/snap/gnome-logs/81 (100%)", "/snap/core18/1223 (100%)", "/snap/core18/1192 (100%)", "/snap/gnome-3-26-1604/92 (100%)", "/snap/gnome-system-monitor/100 (100%)", "/snap/gnome-characters/296 (100%)", "/snap/gnome-3-28-1804/67 (100%)", "/snap/gnome-calculator/501 (100%)", "/snap/core/7917 (100%)", "/snap/spotify/36 (100%)", "/snap/gnome-calculator/406 (100%)", "/snap/gnome-characters/317 (100%)", "/snap/gnome-3-26-1604/90 (100%)", "/snap/gnome-logs/73 (100%)", "/snap/core/7713 (100%)", "/snap/gtk-common-themes/1313 (100%)", "/snap/gnome-system-monitor/95 (100%)", "/snap/gtk-common-themes/1353 (100%)", "/snap/gnome-3-28-1804/71 (100%)"], "load_1": 1.12, "cpu_idle": 80.97}, "ip": "192.168.11.221", "operating_system": "Linux", "status": {"status": 2, "message": "0 running / 1 stopped / 1 failing", "collectors": [{"status": 3, "verbose_message": "", "message": "Stopped", "collector_id": "5da58757e2847e0602771e75"}, {"status": 2, "verbose_message": "", "message": "Couldn\'t start validation command: fork/exec /usr/bin/nxlog: no such file or directory", "collector_id": "5da58757e2847e0602771e78"}]}, "log_file_list": null}, "active": false, "sidecar_version": "1.0.2", "last_seen": "2019-10-17T19:16:41.265Z"}], "filters": null, "only_active": false, "query": "", "total": 1, "order": "asc"}'
    ]
]

discovery = {'': [(u'testserver', {})]}

checks = {
    '': [
        (
            u'testserver', {
                'failing_upper': (1, 1),
                'stopped_upper': (1, 1),
                'running_lower': (1, 0)
            }, [
                (2, 'Active: no', []),
                (0, 'Last seen: 2019-10-17 21:16:41', []),
                (0, 'Before: 19 h', []),
                (
                    1, u'Collectors running: 0 (warn/crit below 1/0)', [
                        (u'collectors_running', 0, None, None, None, None)
                    ]
                ),
                (
                    2, u'Collectors stopped: 1 (warn/crit at 1/1)', [
                        (u'collectors_stopped', 1, 1.0, 1.0, None, None)
                    ]
                ),
                (
                    2, u'Collectors failing: 1 (warn/crit at 1/1)', [
                        (u'collectors_failing', 1, 1.0, 1.0, None, None)
                    ]
                ), (2, 'see long output for more details', []),
                (2, u'\nID: 5da58757e2847e0602771e75, Message: Stopped', []),
                (
                    2,
                    u"\nID: 5da58757e2847e0602771e78, Message: Couldn't start validation command: fork/exec /usr/bin/nxlog: no such file or directory",
                    []
                )
            ]
        )
    ]
}
