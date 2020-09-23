#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.inv_oracle_tablespaces import inventory_oracle_tablespaces
from cmk.base.plugins.agent_based.utils.oracle import OraErrors, SectionTableSpaces
from cmk.base.plugins.agent_based.agent_based_api.v1 import TableRow

Section: SectionTableSpaces = {
    'error_sids': {
        "ORA-bar": OraErrors(["ORA-bar", "some", "data"])
    },
    'tablespaces': {
        ('CLUSTER', 'FOO'): {
            'amount_missing_filenames': 0,
            'autoextensible': True,
            'datafiles': [{
                'autoextensible': True,
                'block_size': 8192,
                'file_online_status': 'TEMP',
                'free_space': 7738490880,
                'increment_size': 209715200,
                'max_size': 20971520000,
                'name': '/oracle/PRD/sapdata/sapdata3/temp_3/temp.data3',
                'size': 18874368000,
                'status': 'ONLINE',
                'ts_status': 'ONLINE',
                'ts_type': 'TEMPORARY',
                'used_size': 18873319424
            }, {
                'autoextensible': True,
                'block_size': 8192,
                'file_online_status': 'TEMP',
                'free_space': 7738490880,
                'increment_size': 209715200,
                'max_size': 20971520000,
                'name': '/oracle/PRD/sapdata/sapdata3/temp_4/temp.data5',
                'size': 18874368000,
                'status': 'ONLINE',
                'ts_status': 'ONLINE',
                'ts_type': 'TEMPORARY',
                'used_size': 18873319424
            }],
            'db_version': 0,
            'status': 'ONLINE',
            'type': 'TEMPORARY'
        },
    }
}


def test_inventory():

    yielded_inventory = list(inventory_oracle_tablespaces(Section))
    assert yielded_inventory == [
        TableRow(path=['software', 'applications', 'oracle', 'tablespaces'],
                 key_columns={
                     'sid': 'CLUSTER',
                     'name': 'FOO'
                 },
                 inventory_columns={
                     'version': '',
                     'type': 'TEMPORARY',
                     'autoextensible': 'YES'
                 },
                 status_columns={
                     'current_size': 37748736000,
                     'max_size': 41943040000,
                     'used_size': 22271754240,
                     'num_increments': 20,
                     'increment_size': 4194304000,
                     'free_space': 21768437760
                 })
    ]
