# -*- encoding: utf-8
# yapf: disable

checkname = 'emc_isilon_cpu'

info = [['123', '234', '231', '567']]

discovery = {'': [(None, None)]}

checks = {
    '': [(None, None, [(0, 'user: 35.7%, system: 23.1%, total: 115.5%',
                      [('user', 35.7, None, None, None, None),
                       ('system', 23.1, None, None, None, None),
                       ('interrupt', 56.7, None, None, None, None)])])]
}
