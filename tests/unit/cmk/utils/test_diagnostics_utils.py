#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path

import pytest
from pytest_mock import MockerFixture

from cmk.utils import diagnostics


def test_diagnostics_serialize_wato_parameters_boolean() -> None:
    assert sorted(
        diagnostics.serialize_wato_parameters(
            {  # type: ignore[typeddict-item]
                "opt_info": {
                    diagnostics.OPT_LOCAL_FILES: "ANY",
                    diagnostics.OPT_OMD_CONFIG: "ANY",
                    diagnostics.OPT_CHECKMK_CRASH_REPORTS: "ANY",
                },
            }
        )
    ) == [
        sorted(
            [
                diagnostics.OPT_LOCAL_FILES,
                diagnostics.OPT_OMD_CONFIG,
                diagnostics.OPT_CHECKMK_CRASH_REPORTS,
            ]
        )
    ]


@pytest.mark.parametrize(
    "wato_parameters, expected_parameters",
    [
        (
            {
                "checkmk_server_host": "",
                "opt_info": {},
            },
            [[]],
        ),
        (
            {
                "checkmk_server_host": "",
                "opt_info": {
                    diagnostics.OPT_PERFORMANCE_GRAPHS: "ANY",
                },
            },
            [[diagnostics.OPT_PERFORMANCE_GRAPHS, ""]],
        ),
        (
            {
                "checkmk_server_host": "myhost",
                "opt_info": {
                    diagnostics.OPT_PERFORMANCE_GRAPHS: "ANY",
                },
            },
            [[diagnostics.OPT_PERFORMANCE_GRAPHS, "myhost"]],
        ),
        (
            {
                "checkmk_server_host": "myhost",
                "opt_info": {
                    diagnostics.OPT_PERFORMANCE_GRAPHS: "ANY",
                    diagnostics.OPT_CHECKMK_OVERVIEW: "ANY",
                },
            },
            [
                [diagnostics.OPT_PERFORMANCE_GRAPHS, "myhost"],
                [diagnostics.OPT_CHECKMK_OVERVIEW, "myhost"],
            ],
        ),
    ],
)
def test_diagnostics_serialize_wato_parameters_with_host(
    mocker: MockerFixture,
    wato_parameters: diagnostics.DiagnosticsParameters,
    expected_parameters: list[list[str]],
) -> None:
    assert diagnostics.serialize_wato_parameters(wato_parameters) == expected_parameters


@pytest.mark.parametrize(
    "wato_parameters, expected_parameters",
    [
        (
            {
                "opt_info": {},
                "comp_specific": {},
            },
            [[]],
        ),
        (
            {
                "opt_info": {},
                "comp_specific": {diagnostics.OPT_COMP_NOTIFICATIONS: {}},
            },
            [[]],
        ),
        (
            {
                "opt_info": {
                    diagnostics.OPT_CHECKMK_CONFIG_FILES: ("_ty", ["a", "b"]),
                },
                "comp_specific": {
                    diagnostics.OPT_COMP_NOTIFICATIONS: {
                        "config_files": ("_ty", ["a", "b"]),
                        "log_files": ("_ty", ["a", "b"]),
                    },
                },
            },
            [
                [diagnostics.OPT_CHECKMK_CONFIG_FILES, "a,b"],
                [diagnostics.OPT_CHECKMK_LOG_FILES, "a,b"],
            ],
        ),
        (
            {
                "opt_info": {
                    diagnostics.OPT_CHECKMK_CONFIG_FILES: ("_ty", ["a1", "a2"]),
                },
                "comp_specific": {
                    diagnostics.OPT_COMP_NOTIFICATIONS: {
                        "config_files": ("_ty", ["b1", "b2"]),
                        "log_files": ("_ty", ["c1", "c2"]),
                    },
                },
            },
            [
                [diagnostics.OPT_CHECKMK_CONFIG_FILES, "a1,a2,b1,b2"],
                [diagnostics.OPT_CHECKMK_LOG_FILES, "c1,c2"],
            ],
        ),
        (
            {
                "opt_info": {
                    diagnostics.OPT_CHECKMK_CONFIG_FILES: (
                        "_ty",
                        ["a1", "a2", "a3", "a4", "a5"],
                    ),
                },
                "comp_specific": {
                    diagnostics.OPT_COMP_NOTIFICATIONS: {
                        "config_files": ("_ty", ["b1", "b2"]),
                        "log_files": ("_ty", ["c1", "c2"]),
                    },
                },
            },
            [
                [diagnostics.OPT_CHECKMK_CONFIG_FILES, "a1,a2,a3,a4"],
                [diagnostics.OPT_CHECKMK_CONFIG_FILES, "a5,b1,b2"],
                [diagnostics.OPT_CHECKMK_LOG_FILES, "c1,c2"],
            ],
        ),
    ],
)
def test_diagnostics_serialize_wato_parameters_files(
    mocker: MockerFixture,
    wato_parameters: diagnostics.DiagnosticsParameters,
    expected_parameters: list[list[str]],
) -> None:
    mocker.patch("cmk.utils.diagnostics._get_max_args", return_value=5)
    assert diagnostics.serialize_wato_parameters(wato_parameters) == expected_parameters


@pytest.mark.parametrize(
    "cl_parameters, modes_parameters, expected_parameters",
    [
        ([], {}, {}),
        # boolean
        (
            [
                diagnostics.OPT_LOCAL_FILES,
                diagnostics.OPT_OMD_CONFIG,
                diagnostics.OPT_CHECKMK_CRASH_REPORTS,
            ],
            {
                diagnostics.OPT_LOCAL_FILES: True,
                diagnostics.OPT_OMD_CONFIG: True,
                diagnostics.OPT_CHECKMK_CRASH_REPORTS: True,
            },
            {
                diagnostics.OPT_LOCAL_FILES: True,
                diagnostics.OPT_OMD_CONFIG: True,
                diagnostics.OPT_CHECKMK_CRASH_REPORTS: True,
            },
        ),
        # files
        (
            [
                diagnostics.OPT_CHECKMK_CONFIG_FILES,
                "a,b",
                diagnostics.OPT_CHECKMK_LOG_FILES,
                "a,b",
            ],
            {
                diagnostics.OPT_CHECKMK_CONFIG_FILES: "a,b",
                diagnostics.OPT_CHECKMK_LOG_FILES: "a,b",
            },
            {
                diagnostics.OPT_CHECKMK_CONFIG_FILES: ["a", "b"],
                diagnostics.OPT_CHECKMK_LOG_FILES: ["a", "b"],
            },
        ),
        # with host
        (
            [
                diagnostics.OPT_PERFORMANCE_GRAPHS,
                "myhost",
                diagnostics.OPT_CHECKMK_OVERVIEW,
                "myhost",
            ],
            {
                diagnostics.OPT_PERFORMANCE_GRAPHS: "myhost",
                diagnostics.OPT_CHECKMK_OVERVIEW: "myhost",
            },
            {
                diagnostics.OPT_PERFORMANCE_GRAPHS: "myhost",
                diagnostics.OPT_CHECKMK_OVERVIEW: "myhost",
            },
        ),
    ],
)
def test_diagnostics_deserialize(
    cl_parameters: list[str],
    modes_parameters: dict[str, str],
    expected_parameters: dict[str, list[str]],
) -> None:
    assert diagnostics.deserialize_cl_parameters(cl_parameters) == expected_parameters
    assert diagnostics.deserialize_modes_parameters(modes_parameters) == expected_parameters


# 'sensitivity.value == diagnostics.CheckmkFileSensitivity.unknown' means not found
@pytest.mark.parametrize(
    "component, sensitivity_values",
    [
        (
            diagnostics.OPT_COMP_GLOBAL_SETTINGS,
            [
                diagnostics.CheckmkFileSensitivity.insensitive,
                diagnostics.CheckmkFileSensitivity.sensitive,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
            ],
        ),
        (
            diagnostics.OPT_COMP_HOSTS_AND_FOLDERS,
            [
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.sensitive,
                diagnostics.CheckmkFileSensitivity.sensitive,
                diagnostics.CheckmkFileSensitivity.sensitive,
                diagnostics.CheckmkFileSensitivity.insensitive,
            ],
        ),
        (
            diagnostics.OPT_COMP_NOTIFICATIONS,
            [
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.sensitive,
                diagnostics.CheckmkFileSensitivity.sensitive,
                diagnostics.CheckmkFileSensitivity.sensitive,
                diagnostics.CheckmkFileSensitivity.insensitive,
            ],
        ),
        (
            diagnostics.OPT_COMP_BUSINESS_INTELLIGENCE,
            [
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.unknown,
                diagnostics.CheckmkFileSensitivity.sensitive,
            ],
        ),
    ],
)
def test_diagnostics_get_checkmk_file_info_by_name(
    component: str, sensitivity_values: list[diagnostics.CheckmkFileSensitivity]
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
        assert (
            diagnostics.get_checkmk_file_info(rel_filepath, component).sensitivity.value
            == result.value
        )


@pytest.mark.parametrize(
    "rel_filepath, sensitivity",
    [
        ("apache.conf", diagnostics.CheckmkFileSensitivity.insensitive),
        ("apache.d/wato/global.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("conf.d/microcore.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("conf.d/mkeventd.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("conf.d/pnp4nagios.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("conf.d/wato/.wato", diagnostics.CheckmkFileSensitivity.insensitive),
        (
            "conf.d/wato/alert_handlers.mk",
            diagnostics.CheckmkFileSensitivity.high_sensitive,
        ),
        ("conf.d/wato/contacts.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/global.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/groups.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("conf.d/wato/hosts.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        (
            "conf.d/wato/notifications.mk",
            diagnostics.CheckmkFileSensitivity.sensitive,
        ),
        ("conf.d/wato/rules.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("conf.d/wato/tags.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("dcd.d/wato/global.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("liveproxyd.d/wato/global.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("main.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("mkeventd.d/wato/rules.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        (
            "mkeventd.d/wato/global.mk",
            diagnostics.CheckmkFileSensitivity.sensitive,
        ),
        ("mkeventd.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("mknotifyd.d/wato/global.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("multisite.d/liveproxyd.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("multisite.d/mkeventd.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("multisite.d/sites.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        (
            "multisite.d/wato/global.mk",
            diagnostics.CheckmkFileSensitivity.sensitive,
        ),
        ("multisite.d/wato/groups.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("multisite.d/wato/tags.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        (
            "multisite.d/wato/users.mk",
            diagnostics.CheckmkFileSensitivity.sensitive,
        ),
        ("multisite.mk", diagnostics.CheckmkFileSensitivity.insensitive),
        ("rrdcached.d/wato/global.mk", diagnostics.CheckmkFileSensitivity.sensitive),
        ("alerts.log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("apache/access_log", diagnostics.CheckmkFileSensitivity.high_sensitive),
        ("apache/error_log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("apache/stats", diagnostics.CheckmkFileSensitivity.high_sensitive),
        ("cmc.log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("unknown.log", diagnostics.CheckmkFileSensitivity.unknown),
        ("dcd.log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("diskspace.log", diagnostics.CheckmkFileSensitivity.insensitive),
        ("liveproxyd.log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("liveproxyd.state", diagnostics.CheckmkFileSensitivity.sensitive),
        ("mkeventd.log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("mknotifyd.log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("mknotifyd.state", diagnostics.CheckmkFileSensitivity.sensitive),
        ("notify.log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("rrdcached.log", diagnostics.CheckmkFileSensitivity.sensitive),
        ("web.log", diagnostics.CheckmkFileSensitivity.sensitive),
    ],
)
def test_diagnostics_file_info_of_comp_notifications(
    rel_filepath: str, sensitivity: diagnostics.CheckmkFileSensitivity
) -> None:
    assert (
        diagnostics.get_checkmk_file_info(rel_filepath, None).sensitivity.value == sensitivity.value
    )


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
            diagnostics.redact_passwords_in_content(
                content.replace("TESTPW", password), Path(rel_filepath)
            )
        )
        # Password no longer in content
        assert password not in redacted_content
        # Only ONE substring should be redacted
        assert redacted_content.count(diagnostics.REDACT_STRING) == count
