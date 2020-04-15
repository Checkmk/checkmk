#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore


checkname = 'graylog_failures'

info = [[
    u'{"failures": [{"timestamp": "2019-09-20T10:52:03.110Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "a", "type": "message", "letter_id": "ae66b494-db94-11e9-9de2-005056981acf"}, {"timestamp": "2019-09-20T10:52:03.110Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "b", "type": "message", "letter_id": "ae66b493-db94-11e9-9de2-005056981acf"}, {"timestamp": "2019-09-20T10:52:02.908Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "b", "type": "message", "letter_id": "ae66b48f-db94-11e9-9de2-005056981acf"}, {"timestamp": "2019-09-20T10:52:02.908Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "a", "type": "message", "letter_id": "ae66b48b-db94-11e9-9de2-005056981acf"}, {"timestamp": "2019-09-20T10:52:02.908Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "graylog_index1", "type": "message", "letter_id": "ae66b487-db94-11e9-9de2-005056981acf"}, {"timestamp": "2019-09-20T10:52:02.908Z", "message": "{\\"type\\":\\"cluster_block_exception\\",\\"reason\\":\\"blocked by: [SERVICE_UNAVAILABLE/2/no master];\\"}", "index": "graylog_index1", "type": "message", "letter_id": "ae66b485-db94-11e9-9de2-005056981acf"}], "total": 198508}'
]]

discovery = {'': [(None, {})]}

checks = {
    '': [(None, {}, [(0, 'Total number of failures: 198508',
                      [('failures', 198508, None, None, None, None)])])]
}
