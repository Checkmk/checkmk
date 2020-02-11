# -*- encoding: utf-8
# yapf: disable
checkname = 'graylog_streams'

info = [[u'{"total": 5, "streams": []}']]

discovery = {'': [(None, {})]}

checks = {
    '': [(None, {
        'stream_disabled': 1
    }, [(1, 'Number of streams: 0', [])])]
}
