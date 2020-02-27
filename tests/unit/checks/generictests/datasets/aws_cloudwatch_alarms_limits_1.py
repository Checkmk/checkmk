# -*- encoding: utf-8 -*-

# yapf: disable
# type: ignore


checkname = 'aws_cloudwatch_alarms_limits'

info = [['[["cloudwatch_alarms",', '"TITEL",', '10,', '1]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'cloudwatch_alarms': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (
                            u'aws_cloudwatch_alarms_cloudwatch_alarms', 1,
                            None, None, None, None
                        )
                    ]
                ), (0, u'\nTITEL: 1 (of max. 10)', [])
            ]
        )
    ]
}
