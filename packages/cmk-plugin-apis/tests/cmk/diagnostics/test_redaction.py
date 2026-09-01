#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest

from cmk.diagnostics.internal import redact_passwords_in_content, REDACT_STRING


@pytest.mark.parametrize(
    "count, rel_filepath, content",
    [
        (
            1,
            "mkeventd.d/wato/global.mk",
            "snmp_credentials = [{'credentials': TESTPW, 'description': ''}]",
        ),
        (
            1,
            "conf.d/wato/tests/hosts.mk",
            "management_ipmi_credentials.update({'myhost': {'username': 'admin', 'password': TESTPW}})",
        ),
        (
            1,
            "conf.d/wato/rules.mk",
            "{'id': '123', 'value': {'auth': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid58b8e40a-dfd0-447e-b06f-f2ba3f469bd9', TESTPW))}}, 'condition': {}, 'options': {}},",
        ),
        (
            1,
            "conf.d/wato/rules.mk",
            "{'id': '123', 'value': {'credentials': ('admin', ('password', TESTPW))}, 'condition': {}, 'options': {}},",
        ),
        (
            1,
            "conf.d/wato/rules.mk",
            "{'id': '123', 'value': {'login': {'auth': ('explicit', ('admin', TESTPW))}}, 'condition': {}, 'options': {}},",
        ),
        (
            2,
            "conf.d/wato/rules.mk",
            "{'id': '123', 'value': ('authPriv', 'md5', 'username', TESTPW, 'AES', TESTPW), 'condition': {}, 'options': {}},",
        ),
        (
            1,
            "conf.d/wato/rules.mk",
            "{'id': '123', 'value': ('authNoPriv', 'md5', 'username', TESTPW), 'condition': {}, 'options': {}},",
        ),
        (
            3,
            "conf.d/wato/hosts.mk",
            """management_snmp_credentials.update({'host1': ('authPriv', 'md5', 'username', TESTPW, 'DES', TESTPW), 'host2': TESTPW})

            """,
        ),
        (1, "mkeventd.d/wato/global.mk", "{'credentials': TESTPW, 'description': ''},"),
        (
            1,
            "mkeventd.d/wato/global.mk",
            "{'credentials': ('authNoPriv', 'md5', 'username', TESTPW),",
        ),
        (
            1,
            "conf.d/wato/rules.mk",
            """snmp_communities = [
{'id': 'e29b75bf-30eb-4e67-baf9-a8a976e11c04', 'value': TESTPW, 'condition': {}, 'options': {'disabled': False}},
] + snmp_communities""",
        ),
        (
            1,
            "network_flow.conf",
            "-F=clickhouse;127.0.0.1@9000,9004;ntopng;network_flow;TESTPW",
        ),
        (
            1,
            "conf.d/wato/rules.mk",
            """{'certificate': '-----BEGIN CERTIFICATE-----\\n'
'TESTPW\\n'
'-----END CERTIFICATE-----\\n'}""",
        ),
        (
            1,
            "conf.d/wato/rules.mk",
            """{'private_key': '-----BEGIN ENCRYPTED PRIVATE KEY-----\\n'
'TESTPW\\n'
'-----END ENCRYPTED PRIVATE KEY-----\\n'}""",
        ),
    ],
)
def test_diagnostics_redact_passwords(count: int, rel_filepath: str, content: str) -> None:
    passwords = [
        "'MySeCr3t_Pa5sWoRd!'",
        '"My\'SeCr3t_Pa5sWoRd!"',
        "'My\"SeCr3t_Pa5sWoRd!'",
        "'My'SeCr3t_Pa5sW\"oRd!'",
    ]
    for password in passwords:
        redacted_content = "".join(
            redact_passwords_in_content(content.replace("TESTPW", password), Path(rel_filepath))
        )
        # Password no longer in content
        assert password not in redacted_content
        # Only ONE substring should be redacted
        assert redacted_content.count(REDACT_STRING) == count
