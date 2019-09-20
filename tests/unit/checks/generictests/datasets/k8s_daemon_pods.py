# -*- encoding: utf-8
# yapf: disable

checkname = 'k8s_daemon_pods'

parsed = {
    u'collision_count': None,
    u'conditions': None,
    u'current_number_scheduled': 1,
    u'desired_number_scheduled': 1,
    u'number_available': 1,
    u'number_misscheduled': 0,
    u'number_ready': 1,
    u'number_unavailable': None,
    u'observed_generation': 1,
    u'updated_number_scheduled': 1
}

discovery = {'': [(None, {})]}

checks = {
    '': [(
        None,
        {},
        [(0, 'Ready: 1', [('k8s_daemon_pods_ready', 1, None, None, None, None)]),
         (0, 'Scheduled: 1/1', [('k8s_daemon_pods_scheduled_desired', 1, None, None, None, None),
                                ('k8s_daemon_pods_scheduled_current', 1, None, None, None, None)]),
         (0, 'Up to date: 1', [('k8s_daemon_pods_scheduled_updated', 1, None, None, None, None)]),
         (0, 'Available: 1/1', [('k8s_daemon_pods_available', 1, None, None, None, None),
                                ('k8s_daemon_pods_unavailable', 0, None, None, None, None)])],
    )],
}
