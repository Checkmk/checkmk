# -*- encoding: utf-8
# yapf: disable

checkname = 'graylog_sidecars'

freeze_time = '2019-10-10 13:34:30'

info = [
    [
        u'{"sort": "node_name", "pagination": {"count": 1, "per_page": 50, "total": 1, "page": 1}, "sidecars": [{"collectors": null, "node_name": "testserver", "assignments": [], "node_id": "31c3e8f9-a6b2-41d4-be78-f6273c3cb0e5", "node_details": {"metrics": {"disks_75": ["/snap/gnome-calculator/501 (100%)", "/snap/core/7713 (100%)", "/snap/gnome-calculator/406 (100%)", "/snap/gtk-common-themes/1313 (100%)", "/snap/core18/1192 (100%)", "/snap/spotify/35 (100%)", "/snap/gnome-characters/317 (100%)", "/snap/gnome-3-26-1604/90 (100%)", "/snap/gnome-3-28-1804/71 (100%)", "/snap/gnome-3-26-1604/92 (100%)", "/snap/gtk-common-themes/1198 (100%)", "/snap/gnome-logs/73 (100%)", "/snap/gnome-logs/81 (100%)", "/snap/gnome-characters/296 (100%)", "/snap/gnome-3-28-1804/67 (100%)", "/snap/core18/1144 (100%)", "/snap/gnome-system-monitor/100 (100%)", "/snap/gnome-system-monitor/95 (100%)", "/snap/core/7396 (100%)", "/snap/spotify/36 (100%)"], "load_1": 0.49, "cpu_idle": 95.0}, "ip": "10.3.2.62", "operating_system": "Linux", "status": {"status": 1, "message": "Received no ping signal from sidecar", "collectors": []}, "log_file_list": null}, "active": false, "sidecar_version": "1.0.2", "last_seen": "2019-10-10T09:56:29.303Z"}], "filters": null, "only_active": false, "query": "", "total": 1, "order": "asc"}'
    ]
]

discovery = {'': [(u'testserver', {})]}

checks = {
    '': [
        (
            u'testserver', {}, [
                (1, 'Active: no', []),
                (0, 'Last seen: 2019-10-10 11:56:29', []),
                (0, 'Before: 218 m', []),
                (1, u'Collectors: Received no ping signal from sidecar', [])
            ]
        )
    ]
}
