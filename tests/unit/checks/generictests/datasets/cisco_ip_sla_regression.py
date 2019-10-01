# -*- encoding: utf-8
# yapf: disable
checkname = 'cisco_ip_sla'

info = [
    [
        [[10, 96, 66, 4], [10, 96, 27, 69], u'1'],
    ],
    [
        [u'', u'', u'9', u'5000'],
    ],
    [
        [u'6', u'', u'2', u'2', u'2'],
    ],
    [
        [u'25', u'1'],
    ],
]

discovery = {'': [('0', {})]}

checks = {
    '': [('0', {
             'completion_time_over_treshold_occured': 'no',
             'connection_lost_occured': 'no',
             'latest_rtt_completion_time': (250, 500),
             'latest_rtt_state': 'ok',
             'state': 'active',
             'timeout_occured': 'no'
         }, [(0, 'Target address: 10.96.66.4', []), (0, 'Source address: 10.96.27.69', []),
             (0, 'RTT type: jitter', []), (0, 'Threshold: 5000 ms', []), (0, 'State: active', []),
             (0, 'Connection lost occured: no', []), (0, 'Timeout occured: no', []),
             (0, 'Completion time over treshold occured: no', []),
             (0, 'Latest RTT completion time: 25 ms', [('rtt', 0.025, 0.25, 0.5, None, None)]),
             (0, 'Latest RTT state: ok', [])])]
}
