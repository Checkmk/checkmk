# -*- encoding: utf-8
# yapf: disable

checkname = 'kernel'

freeze_time = '1970-01-01 00:00:02'

info = [[u'11238'], [u'nr_free_pages', u'198749'], [u'pgpgin', u'169984814'],
        [u'pgpgout', u'97137765'], [u'pswpin', u'250829'], [u'pswpout', u'751706'],
        [u'pgmajfault', u'1795031'],
        [
            u'cpu', u'13008772', u'12250', u'5234590', u'181918601', u'73242', u'0', u'524563',
            u'0', u'0', u'0'
        ],
        [
            u'cpu0', u'1602366', u'1467', u'675813', u'22730303', u'9216', u'0', u'265437', u'0',
            u'0', u'0'
        ],
        [
            u'cpu1', u'1463624', u'1624', u'576516', u'22975174', u'8376', u'0', u'116908', u'0',
            u'0', u'0'
        ], [u'ctxt', u'539210403'], [u'processes', u'4700038']]

discovery = {'': [], 'performance': [(None, {})], 'util': [(None, {})]}

checks = {
    'performance': [(None, {}, [
        (0, 'Process Creations: 418.23/s', [('process_creations', 418.2272646378359, None, None, None, None)]),
        (0, 'Context Switches: 47980.99/s', [('context_switches', 47980.99332621463, None, None, None, None)]),
        (0, 'Major Page Faults: 159.73/s', [('major_page_faults', 159.72868837871508, None, None, None, None)]),
        (0, 'Page Swap in: 22.32/s', [('page_swap_in', 22.319718811176365, None, None, None, None)]),
        (0, 'Page Swap Out: 66.89/s', [('page_swap_out', 66.8896600818651, None, None, None, None)]),
                ]),
                (
                    None,
                    {
                        'ctxt': (30000.0, 45000.0),
                        'processes': (400.0, 500.0),
                        'page_swap_in_levels': (10.0, 50.0),
                        'page_swap_out_levels_lower': (500.0, 100.0),
                    },
                    [
                        (1, 'Process Creations: 418.23/s (warn/crit at 400.00/s/500.00/s)',
                         [('process_creations', 418.2272646378359, 400.0, 500.0)]),
                        (2, 'Context Switches: 47980.99/s (warn/crit at 30000.00/s/45000.00/s)',
                         [('context_switches', 47980.99332621463, 30000.0, 45000.0)]),
                        (0, 'Major Page Faults: 159.73/s',
                         [('major_page_faults', 159.72868837871508, None, None, None, None)]),
                        (1, 'Page Swap in: 22.32/s (warn/crit at 10.00/s/50.00/s)',
                         [('page_swap_in', 22.319718811176365, 10.0, 50.0, None, None)]),
                        (2, 'Page Swap Out: 66.89/s (warn/crit below 500.00/s/100.00/s)',
                         [('page_swap_out', 66.8896600818651, None, None, None, None)]),
                    ],
                )],
    'util': [(None, {}, [
        (0, 'User: 6.49%', [('user', 6.48547647710549, None, None, None, None)]),
        (0, 'System: 2.87%', [('system', 2.868503817100648, None, None, None, None)]),
        (0, 'Wait: 0.04%', [('wait', 0.03648018320959447, None, None, None, None)]),
        (0, 'Total CPU: 9.39%', [('util', 9.390460477415733, None, None, 0, None)]),
    ])]
}

mock_item_state = {'performance': (0, 0)}
