#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from pathlib import Path

import pytest

from cmk.ccc.site import SiteId
from cmk.diagnostics import (
    CheckmkFileSensitivity,
    deserialize_cl_parameters,
    deserialize_modes_parameters,
    DiagnosticsCLParameters,
    DiagnosticsModesParameters,
    DiagnosticsOptionalParameters,
    DiagnosticsParameters,
    get_checkmk_file_info,
    OPT_CHECKMK_CONFIG_FILES,
    OPT_CHECKMK_CRASH_REPORTS,
    OPT_CHECKMK_LOG_FILES,
    OPT_CHECKMK_OVERVIEW,
    OPT_COMP_BUSINESS_INTELLIGENCE,
    OPT_COMP_GLOBAL_SETTINGS,
    OPT_COMP_HOSTS_AND_FOLDERS,
    OPT_COMP_NOTIFICATIONS,
    OPT_LOCAL_FILES,
    OPT_OMD_CONFIG,
    OPT_PERFORMANCE_GRAPHS,
    redact_passwords_in_content,
    REDACT_STRING,
    serialize_wato_parameters,
)


def test_diagnostics_serialize_wato_parameters_boolean() -> None:
    assert list(
        serialize_wato_parameters(
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={
                    OPT_LOCAL_FILES: "ANY",
                    OPT_OMD_CONFIG: "ANY",
                    OPT_CHECKMK_CRASH_REPORTS: "ANY",
                },
                comp_specific=None,
                checkmk_server_host="hurz",
            ),
            max_args=4096,
        )
    ) == [
        [
            OPT_CHECKMK_CRASH_REPORTS,
            OPT_LOCAL_FILES,
            OPT_OMD_CONFIG,
        ]
    ]


@pytest.mark.parametrize(
    "wato_parameters, expected_parameters",
    [
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={},
                comp_specific=None,
                checkmk_server_host="",
            ),
            [[]],
        ),
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={
                    OPT_PERFORMANCE_GRAPHS: "ANY",
                },
                comp_specific=None,
                checkmk_server_host="",
            ),
            [[OPT_PERFORMANCE_GRAPHS, ""]],
        ),
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={
                    OPT_PERFORMANCE_GRAPHS: "ANY",
                },
                comp_specific=None,
                checkmk_server_host="myhost",
            ),
            [[OPT_PERFORMANCE_GRAPHS, "myhost"]],
        ),
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={
                    OPT_PERFORMANCE_GRAPHS: "ANY",
                    OPT_CHECKMK_OVERVIEW: "ANY",
                },
                comp_specific=None,
                checkmk_server_host="myhost",
            ),
            [
                [OPT_PERFORMANCE_GRAPHS, "myhost"],
                [OPT_CHECKMK_OVERVIEW, "myhost"],
            ],
        ),
    ],
)
def test_diagnostics_serialize_wato_parameters_with_host(
    wato_parameters: DiagnosticsParameters,
    expected_parameters: Sequence[DiagnosticsCLParameters],
) -> None:
    assert serialize_wato_parameters(wato_parameters, max_args=4096) == expected_parameters


@pytest.mark.parametrize(
    "wato_parameters, expected_parameters",
    [
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={},
                comp_specific={},
                checkmk_server_host="hurz",
            ),
            [[]],
        ),
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={},
                comp_specific={OPT_COMP_NOTIFICATIONS: {}},
                checkmk_server_host="hurz",
            ),
            [[]],
        ),
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={
                    OPT_CHECKMK_CONFIG_FILES: ("_ty", ["a", "b"]),
                },
                comp_specific={
                    OPT_COMP_NOTIFICATIONS: {
                        "config_files": ("_ty", ["a", "b"]),
                        "log_files": ("_ty", ["a", "b"]),
                    },
                },
                checkmk_server_host="hurz",
            ),
            [
                [OPT_CHECKMK_CONFIG_FILES, "a,b"],
                [OPT_CHECKMK_LOG_FILES, "a,b"],
            ],
        ),
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={
                    OPT_CHECKMK_CONFIG_FILES: ("_ty", ["a1", "a2"]),
                },
                comp_specific={
                    OPT_COMP_NOTIFICATIONS: {
                        "config_files": ("_ty", ["b1", "b2"]),
                        "log_files": ("_ty", ["c1", "c2"]),
                    },
                },
                checkmk_server_host="hurz",
            ),
            [
                [OPT_CHECKMK_CONFIG_FILES, "a1,a2,b1,b2"],
                [OPT_CHECKMK_LOG_FILES, "c1,c2"],
            ],
        ),
        (
            DiagnosticsParameters(
                site=SiteId("gnlpft"),
                general=True,
                timeout=99,
                opt_info={
                    OPT_CHECKMK_CONFIG_FILES: (
                        "_ty",
                        ["a1", "a2", "a3", "a4", "a5"],
                    ),
                },
                comp_specific={
                    OPT_COMP_NOTIFICATIONS: {
                        "config_files": ("_ty", ["b1", "b2"]),
                        "log_files": ("_ty", ["c1", "c2"]),
                    },
                },
                checkmk_server_host="hurz",
            ),
            [
                [OPT_CHECKMK_CONFIG_FILES, "a1,a2,a3,a4"],
                [OPT_CHECKMK_CONFIG_FILES, "a5,b1,b2"],
                [OPT_CHECKMK_LOG_FILES, "c1,c2"],
            ],
        ),
    ],
)
def test_diagnostics_serialize_wato_parameters_files(
    wato_parameters: DiagnosticsParameters,
    expected_parameters: Sequence[DiagnosticsCLParameters],
) -> None:
    assert serialize_wato_parameters(wato_parameters, max_args=5) == expected_parameters


@pytest.mark.parametrize(
    "cl_parameters, modes_parameters, expected_parameters",
    [
        ([], {}, {}),
        # boolean
        (
            [
                OPT_LOCAL_FILES,
                OPT_OMD_CONFIG,
                OPT_CHECKMK_CRASH_REPORTS,
            ],
            {
                OPT_LOCAL_FILES: True,
                OPT_OMD_CONFIG: True,
                OPT_CHECKMK_CRASH_REPORTS: True,
            },
            {
                OPT_LOCAL_FILES: True,
                OPT_OMD_CONFIG: True,
                OPT_CHECKMK_CRASH_REPORTS: True,
            },
        ),
        # files
        (
            [
                OPT_CHECKMK_CONFIG_FILES,
                "a,b",
                OPT_CHECKMK_LOG_FILES,
                "a,b",
            ],
            {
                OPT_CHECKMK_CONFIG_FILES: "a,b",
                OPT_CHECKMK_LOG_FILES: "a,b",
            },
            {
                OPT_CHECKMK_CONFIG_FILES: ["a", "b"],
                OPT_CHECKMK_LOG_FILES: ["a", "b"],
            },
        ),
        # with host
        (
            [
                OPT_PERFORMANCE_GRAPHS,
                "myhost",
                OPT_CHECKMK_OVERVIEW,
                "myhost",
            ],
            {
                OPT_PERFORMANCE_GRAPHS: "myhost",
                OPT_CHECKMK_OVERVIEW: "myhost",
            },
            {
                OPT_PERFORMANCE_GRAPHS: "myhost",
                OPT_CHECKMK_OVERVIEW: "myhost",
            },
        ),
    ],
)
def test_diagnostics_deserialize(
    cl_parameters: DiagnosticsCLParameters,
    modes_parameters: DiagnosticsModesParameters,
    expected_parameters: DiagnosticsOptionalParameters,
) -> None:
    assert deserialize_cl_parameters(cl_parameters) == expected_parameters
    assert deserialize_modes_parameters(modes_parameters) == expected_parameters


# 'sensitivity.value == CheckmkFileSensitivity.unknown' means not found
@pytest.mark.parametrize(
    "component, sensitivity_values",
    [
        (
            OPT_COMP_GLOBAL_SETTINGS,
            [
                CheckmkFileSensitivity.insensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
            ],
        ),
        (
            OPT_COMP_HOSTS_AND_FOLDERS,
            [
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.insensitive,
            ],
        ),
        (
            OPT_COMP_NOTIFICATIONS,
            [
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.sensitive,
                CheckmkFileSensitivity.insensitive,
            ],
        ),
        (
            OPT_COMP_BUSINESS_INTELLIGENCE,
            [
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.unknown,
                CheckmkFileSensitivity.sensitive,
            ],
        ),
    ],
)
def test_diagnostics_get_checkmk_file_info_by_name(
    component: str, sensitivity_values: Sequence[CheckmkFileSensitivity]
) -> None:
    rel_filepaths = [
        "path/to/sites.mk",
        "path/to/global.mk",
        "path/to/hosts.mk",
        "path/to/rules.mk",
        "path/to/tags.mk",
        "path/to/.wato",
        "multisite.d/wato/bi_config.bi",
    ]
    for rel_filepath, result in zip(rel_filepaths, sensitivity_values):
        assert get_checkmk_file_info(rel_filepath, component).sensitivity.value == result.value


@pytest.mark.parametrize(
    "rel_filepath, sensitivity",
    [
        ("apache.conf", CheckmkFileSensitivity.insensitive),
        ("apache.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("conf.d/microcore.mk", CheckmkFileSensitivity.insensitive),
        ("conf.d/mkeventd.mk", CheckmkFileSensitivity.insensitive),
        ("conf.d/pnp4nagios.mk", CheckmkFileSensitivity.insensitive),
        ("conf.d/wato/.wato", CheckmkFileSensitivity.insensitive),
        (
            "conf.d/wato/alert_handlers.mk",
            CheckmkFileSensitivity.high_sensitive,
        ),
        ("conf.d/wato/contacts.mk", CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/groups.mk", CheckmkFileSensitivity.insensitive),
        ("conf.d/wato/hosts.mk", CheckmkFileSensitivity.sensitive),
        (
            "conf.d/wato/notifications.mk",
            CheckmkFileSensitivity.sensitive,
        ),
        ("conf.d/wato/rules.mk", CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/tags.mk", CheckmkFileSensitivity.sensitive),
        ("dcd.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("liveproxyd.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("main.mk", CheckmkFileSensitivity.insensitive),
        ("mkeventd.d/wato/rules.mk", CheckmkFileSensitivity.sensitive),
        (
            "mkeventd.d/wato/global.mk",
            CheckmkFileSensitivity.sensitive,
        ),
        ("mkeventd.mk", CheckmkFileSensitivity.insensitive),
        ("mknotifyd.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("multisite.d/liveproxyd.mk", CheckmkFileSensitivity.insensitive),
        ("multisite.d/mkeventd.mk", CheckmkFileSensitivity.insensitive),
        ("multisite.d/sites.mk", CheckmkFileSensitivity.sensitive),
        (
            "multisite.d/wato/global.mk",
            CheckmkFileSensitivity.sensitive,
        ),
        ("multisite.d/wato/groups.mk", CheckmkFileSensitivity.insensitive),
        ("multisite.d/wato/tags.mk", CheckmkFileSensitivity.sensitive),
        (
            "multisite.d/wato/users.mk",
            CheckmkFileSensitivity.sensitive,
        ),
        ("multisite.mk", CheckmkFileSensitivity.insensitive),
        ("rrdcached.d/wato/global.mk", CheckmkFileSensitivity.sensitive),
        ("alerts.log", CheckmkFileSensitivity.sensitive),
        ("apache/access_log", CheckmkFileSensitivity.high_sensitive),
        ("apache/error_log", CheckmkFileSensitivity.sensitive),
        ("apache/stats", CheckmkFileSensitivity.high_sensitive),
        ("cmc.log", CheckmkFileSensitivity.sensitive),
        ("unknown.log", CheckmkFileSensitivity.unknown),
        ("dcd.log", CheckmkFileSensitivity.sensitive),
        ("diskspace.log", CheckmkFileSensitivity.insensitive),
        ("liveproxyd.log", CheckmkFileSensitivity.sensitive),
        ("liveproxyd.state", CheckmkFileSensitivity.sensitive),
        ("mkeventd.log", CheckmkFileSensitivity.sensitive),
        ("mknotifyd.log", CheckmkFileSensitivity.sensitive),
        ("mknotifyd.state", CheckmkFileSensitivity.sensitive),
        ("notify.log", CheckmkFileSensitivity.sensitive),
        ("rrdcached.log", CheckmkFileSensitivity.sensitive),
        ("web.log", CheckmkFileSensitivity.sensitive),
    ],
)
def test_diagnostics_file_info_of_comp_notifications(
    rel_filepath: str, sensitivity: CheckmkFileSensitivity
) -> None:
    assert get_checkmk_file_info(rel_filepath, None).sensitivity.value == sensitivity.value


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
