# -*- encoding: utf-8
# yapf: disable

checkname = 'aws_glacier_limits'

info = [['[["number_of_vaults",', '"TITLE",', '10,', '1,', '"REGION"]]']]

discovery = {'': [(None, {})]}

checks = {
    '': [
        (
            None, {
                'number_of_vaults': (None, 80.0, 90.0)
            }, [
                (
                    0, 'No levels reached', [
                        (
                            u'aws_glacier_number_of_vaults', 1, None, None,
                            None, None
                        )
                    ]
                ), (0, u'\nTITLE: 1 (of max. 10) (Region REGION)', [])
            ]
        )
    ]
}
