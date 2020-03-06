# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore


checkname = 'aws_elb_limits'

info = [['[["load_balancers",', '"TITLE",', '10,', '1]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'load_balancer_registered_instances': (None, 80.0, 90.0),
                'load_balancer_listeners': (None, 80.0, 90.0),
                'load_balancers': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (u'aws_elb_load_balancers', 1, None, None, None, None)
                    ]
                ), (0, u'\nTITLE: 1 (of max. 10)', [])
            ]
        )
    ]
}
