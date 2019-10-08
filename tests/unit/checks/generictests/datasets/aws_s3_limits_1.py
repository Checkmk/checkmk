# -*- encoding: utf-8
# yapf: disable

checkname = 'aws_s3_limits'

info = [['[["buckets",', '"TITLE",', '10,', '1]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'buckets': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (u'aws_s3_buckets', 1, None, None, None, None)
                    ]
                ), (0, u'\nTITLE: 1 (of max. 10)', [])
            ]
        )
    ]
}
