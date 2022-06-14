#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# yapf: disable
# type: ignore

checkname = 'mysql_slave'

info = [['***************************', '1.', 'row', '***************************'],
        ['Slave_IO_State:', 'Waiting', 'for', 'master', 'to', 'send', 'event'],
        ['Master_Host:', '10.1.27.6'], ['Master_User:', 'repl'], ['Master_Port:', '3306'],
        ['Connect_Retry:', '60'], ['Master_Log_File:', 'repl-log-bin.002158'],
        ['Read_Master_Log_Pos:', '142181744'], ['Relay_Log_File:', 'repl-relay-bin.003953'],
        ['Relay_Log_Pos:', '8161786'], ['Relay_Master_Log_File:', 'repl-log-bin.002158'],
        ['Slave_IO_Running:', 'Yes'], ['Slave_SQL_Running:', 'Yes'], ['Replicate_Do_DB:'],
        ['Replicate_Ignore_DB:'], ['Replicate_Do_Table:'], ['Replicate_Ignore_Table:'],
        ['Replicate_Wild_Do_Table:'], ['Replicate_Wild_Ignore_Table:'], ['Last_Errno:', '0'],
        ['Last_Error:'], ['Skip_Counter:', '0'], ['Exec_Master_Log_Pos:', '142181744'],
        ['Relay_Log_Space:', '93709799'], ['Until_Condition:', 'None'], ['Until_Log_File:'],
        ['Until_Log_Pos:', '0'], ['Master_SSL_Allowed:', 'No'], ['Master_SSL_CA_File:'],
        ['Master_SSL_CA_Path:'], ['Master_SSL_Cert:'], ['Master_SSL_Cipher:'], ['Master_SSL_Key:'],
        ['Seconds_Behind_Master:', '0'], ['Master_SSL_Verify_Server_Cert:', 'No'],
        ['Last_IO_Errno:', '0'], ['Last_IO_Error:'], ['Last_SQL_Errno:', '0'], ['Last_SQL_Error:'],
        ['Replicate_Ignore_Server_Ids:'], ['Master_Server_Id:', '12']]

discovery = {'': [('mysql', {})]}

checks = {
    '': [('mysql', {}, [
        (0,
         'Slave-IO: running, Relay Log: 89.37 MB, Slave-SQL: running, Time behind Master: 0 seconds',
         [('relay_log_space', 93709799, None, None, None, None),
          ('sync_latency', 0, None, None, None, None)])
    ])]
}
