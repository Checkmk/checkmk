# -*- encoding: utf-8
# yapf: disable

checkname = 'aws_ebs_limits'

info = [['[["block_store_snapshots",', '"TITLE",', '10,', '1]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'block_store_space_gp2': (None, 80.0, 90.0),
                'block_store_space_sc1': (None, 80.0, 90.0),
                'block_store_space_st1': (None, 80.0, 90.0),
                'block_store_snapshots': (None, 80.0, 90.0),
                'block_store_iops_io1': (None, 80.0, 90.0),
                'block_store_space_standard': (None, 80.0, 90.0),
                'block_store_space_io1': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (
                            u'aws_ebs_block_store_snapshots', 1, None, None,
                            None, None
                        )
                    ]
                ), (0, u'\nTITLE: 1 (of max. 10)', [])
            ]
        )
    ]
}
