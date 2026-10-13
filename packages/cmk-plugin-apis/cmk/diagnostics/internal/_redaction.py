#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""General purpose redaction of passwords and other secrets in collected content"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, kw_only=True)
class RedactPattern:
    affected_files: Sequence[str]
    outer_regex: re.Pattern[str] | None
    replace_regex: re.Pattern[str]
    replacement: str


REDACT_STRING = "REDACTED"
REDACT_PATTERNS: list[RedactPattern] = [
    # Examples of strings to be redacted:
    #   mkeventd.d/wato/global.mk:snmp_credentials = [{'credentials': 'secret_PW_123!', 'description': ''}]
    #   conf.d/wato/tests/hosts.mk:management_ipmi_credentials.update({'myhost': {'username': 'admin', 'password': 'secret_PW_123!'}})
    RedactPattern(
        affected_files=[],
        outer_regex=None,
        replace_regex=re.compile(
            r"('(?:access_key_id|api_key|api_token|app_key|automation_secret|client_secret|community|credentials|ilert_api_key|management_snmp_community|passwd|password|proxy_password|recipient_key|routing_key|secret|secret_access_key|snmp_community|token)': [\"']).*?((?:\"|')[,\}])",
        ),
        replacement=r"\1%s\2" % REDACT_STRING,
    ),
    # This one is because the password is stored in clear text even thoough an internal pw store
    # entry is being created. Can be removed, once, this is fixed.
    # Examples of strings to be redacted:
    #   conf.d/wato/rules.mk:{'id': '123', 'value': {'auth': {'username': 'admin', 'password': ('cmk_postprocessed', 'explicit_password', ('uuid58b8e40a-dfd0-447e-b06f-f2ba3f469bd9', 'secret_PW_123!'))}}, 'condition': {}, 'options': {}},
    RedactPattern(
        affected_files=[
            "rules.mk",
            "multisite.d/wato/user_connections.mk",
            "conf.d/wato/notification_parameter.mk",
            "conf.d/wato/contacts.mk",
            "conf.d/wato/influxdb_connections.mk",
        ],
        outer_regex=None,
        replace_regex=re.compile(
            r"(\('[^']*', 'explicit_password', \('[^']*', [\"']).*?([\"']\)\))"
        ),
        replacement=r"\1%s\2" % REDACT_STRING,
    ),
    # Examples of strings to be redacted:
    #   conf.d/wato/rules.mk:{'id': '123', 'value': {'credentials': ('admin', ('password', 'secret_PW_123!'))}, 'condition': {}, 'options': {}},
    RedactPattern(
        affected_files=[],
        outer_regex=None,
        replace_regex=re.compile(r"(\('(?:password|webhook_url)', [\"']).*?([\"']\))"),
        replacement=r"\1%s\2" % REDACT_STRING,
    ),
    # This one is only for the Agent rules for mk_ms_sql, mk_mysql and mk_oracle:
    # Examples of strings to be redacted:
    #   conf.d/wato/rules.mk:{'id': '123', 'value': {'login': {'auth': ('explicit', ('admin', 'secret_PW_123!'))}}, 'condition': {}, 'options': {}},
    RedactPattern(
        affected_files=[
            "rules.mk",
        ],
        outer_regex=None,
        replace_regex=re.compile(
            r"('auth': \('[^']*', \('[^']*', [\"']|'credentials': \('[^']+', [\"']).*?([\"']\)\)|'\))"
        ),
        replacement=r"\1%s\2" % REDACT_STRING,
    ),
    # This one is for the fact that the SNMP community is always stored as cleartext
    # Can be removed, once the password store can be used, here
    # Examples of strings to be redacted:
    #   conf.d/wato/rules.mk:{'id': '123', 'value': ('authPriv', 'md5', 'username', 'secret_PW_123!', 'AES', 'secret_PW_456!'), 'condition': {}, 'options': {}},
    RedactPattern(
        affected_files=[
            "hosts.mk",
            "rules.mk",
        ],
        outer_regex=None,
        replace_regex=re.compile(
            r"(\('authPriv', '[^']+', '[^']+', [\"']).*?([\"'], '[^']+', [\"']).*?([\"']\))"
        ),
        replacement=rf"\1{REDACT_STRING}\2{REDACT_STRING}\3",
    ),
    # This one is for the fact that the SNMP community is always stored as cleartext
    # Can be removed, once the password store can be used, here
    # Examples of strings to be redacted:
    #   conf.d/wato/rules.mk:{'id': '123', 'value': ('authNoPriv', 'md5', 'username', 'secret_PW_123!'), 'condition': {}, 'options': {}},
    RedactPattern(
        affected_files=[
            "rules.mk",
            "hosts.mk",
        ],
        outer_regex=None,
        replace_regex=re.compile(
            r"(\('(?:authNoPriv|noAuthPriv)', (?:'[^']+',){1,2} [\"']).*?([\"']\))"
        ),
        replacement=r"\1%s\2" % REDACT_STRING,
    ),
    # This one is for the fact that the SNMP community is always stored as cleartext
    # Can be removed, once the password store can be used, here
    # Examples of strings to be redacted, tricky, because we have to consider the surrounding lines:
    #   conf.d/wato/rules.mk:snmp_communities = [
    #   conf.d/wato/rules.mk:{'id': 'e29b75bf-30eb-4e67-baf9-a8a976e11c04', 'value': 'secret_PW_123!', 'condition': {}, 'options': {'disabled': False}},
    #   conf.d/wato/rules.mk:] + snmp_communities
    RedactPattern(
        affected_files=[
            "rules.mk",
        ],
        outer_regex=re.compile(
            r"(snmp_communities\s*=\s*\[)(.*?)(\]\s*\+\s*snmp_communities)",
            flags=re.DOTALL | re.MULTILINE,
        ),
        replace_regex=re.compile(r"('value': [\"']).*?([\"'][,\}}])"),
        replacement=r"\1%s\2" % REDACT_STRING,
    ),
    # This one is for the fact that the SNMP community is always stored as cleartext
    # Can be removed, once the password store can be used, here
    # Examples of strings to be redacted:
    #   conf.d/wato/hosts.mk:management_snmp_credentials.update({'host1': ('authPriv', 'md5', 'username', 'REDACTED', 'DES', 'REDACTED'), 'host2': 'secret_PW_123!'})
    RedactPattern(
        affected_files=[
            "hosts.mk",
        ],
        outer_regex=re.compile(
            r"(management_snmp_credentials.update\(|explicit_snmp_communities.update\()(.*?)(\n\n)",
            flags=re.DOTALL | re.MULTILINE,
        ),
        replace_regex=re.compile(r"('[^']+': [\"']).*?([\"'][,\}])"),
        replacement=r"\1%s\2" % REDACT_STRING,
    ),
    # This one is for the fact that the SNMP community is always stored as cleartext
    # Can be removed, once the password store can be used, here
    # Examples of strings to be redacted:
    #   mkeventd.d/wato/global.mk: {'credentials': 'secret_PW_123!', 'description': ''},
    #   mkeventd.d/wato/global.mk: {'credentials': ('authNoPriv', 'md5', 'username', 'secret_PW_123!'),
    RedactPattern(
        affected_files=[
            "mkeventd.d/wato/global.mk",
        ],
        outer_regex=None,
        replace_regex=re.compile(r"('credentials': )(?:[\{\(][^)}]*[\}\)]|'.*?'|\".*?\")([,\}])"),
        replacement=r"\1'%s'\2" % REDACT_STRING,
    ),
    # The flow aggregator's ClickHouse export target carries its password as the last
    # field of the -F= line. Example of a string to be redacted:
    #   network_flow.conf:-F=clickhouse;127.0.0.1@9000,9004;ntopng;network_flow;secret_PW_123!
    RedactPattern(
        affected_files=[
            "network_flow.conf",
        ],
        outer_regex=None,
        replace_regex=re.compile(r"(^-F=clickhouse(?:;[^;\n]*){3};).*$", flags=re.MULTILINE),
        replacement=r"\1%s" % REDACT_STRING,
    ),
    # There are keys and certificates stored in different places.
    # Examples of strings to be redacted:
    #   $ cat multisite.d/wato/agent_signature_keys.mk
    #   # Written by Checkmk store
    #
    #   agent_signature_keys.update({1: {'alias': 'cmk12345',
    #
    #        'certificate': '-----BEGIN CERTIFICATE-----\n'
    #                       'MIIC3DCCAcQCAQEwDQYJKoZIhvcNAQEFBQAwMzEeMBwGA1UECgwVQ2hlY2tfTUsg\n'
    #                       '...\n'
    #                       'tBffpLmvRGzO2Jr+jAmHfQ==\n'
    #                       '-----END CERTIFICATE-----\n',
    #        'date': 1612247808.417043,
    #        'owner': 'cmkadmin',
    #        'private_key': '-----BEGIN ENCRYPTED PRIVATE KEY-----\n'
    #                       'MIIFLTBXBgkqhkiG9w0BBQ0wSjApBgkqhkiG9w0BBQwwHAQIfOHW49AopeICAggA\n'
    #                       '...\n'
    #                       '2sbZtJKXqX1hnmhYwOSeG1fA2smedEAOhZQYCdnbN+zN\n'
    #                       '-----END ENCRYPTED PRIVATE KEY-----\n'}})
    RedactPattern(
        affected_files=[],
        outer_regex=None,
        replace_regex=re.compile(
            r"(-----BEGIN .*?-----).*?(-----END)", flags=re.DOTALL | re.MULTILINE
        ),
        replacement=r"\1 %s \2" % REDACT_STRING,
    ),
]


def redact_passwords_in_content(content: str, rel_filepath: Path) -> str:
    for rp in REDACT_PATTERNS:
        if not rp.affected_files or any(a in str(rel_filepath) for a in rp.affected_files):
            content = _apply_redact_pattern(rp, content)

    return content


def _apply_redact_pattern(rp: RedactPattern, content: str) -> str:
    if rp.outer_regex is None:
        return rp.replace_regex.sub(rp.replacement, content)

    def _inner_regex_processor(match: re.Match[str]) -> str:
        p, c, s = match.groups()
        return p + rp.replace_regex.sub(rp.replacement, c) + s

    return rp.outer_regex.sub(_inner_regex_processor, content)


def redact_passwords_in_file(filepath: Path, rel_filepath: Path) -> int:
    try:
        with open(filepath) as f:
            content = f.read()

    except UnicodeDecodeError:
        # We won't redact non-ASCII files
        return 0

    content = redact_passwords_in_content(content, rel_filepath)

    with open(filepath, "w") as f:
        f.write(content)

    return content.count(REDACT_STRING)
