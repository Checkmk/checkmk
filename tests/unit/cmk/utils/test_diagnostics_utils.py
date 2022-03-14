#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore[typeddict-item]

import pytest

import cmk.utils.diagnostics as diagnostics


def test_diagnostics_serialize_wato_parameters_boolean():
    assert sorted(
        diagnostics.serialize_wato_parameters(
            {
                "opt_info": {
                    diagnostics.OPT_LOCAL_FILES: "ANY",
                    diagnostics.OPT_OMD_CONFIG: "ANY",
                    diagnostics.OPT_PERFORMANCE_GRAPHS: "ANY",
                    diagnostics.OPT_CHECKMK_OVERVIEW: "ANY",
                },
            }
        )
    ) == [
        sorted(
            [
                diagnostics.OPT_LOCAL_FILES,
                diagnostics.OPT_OMD_CONFIG,
                diagnostics.OPT_PERFORMANCE_GRAPHS,
                diagnostics.OPT_CHECKMK_OVERVIEW,
            ]
        )
    ]


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
                    diagnostics.OPT_CHECKMK_CONFIG_FILES: ("_ty", ["a1", "a2", "a3", "a4", "a5"]),
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
def test_diagnostics_serialize_wato_parameters_files(mocker, wato_parameters, expected_parameters):
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
                diagnostics.OPT_PERFORMANCE_GRAPHS,
                diagnostics.OPT_CHECKMK_OVERVIEW,
            ],
            {
                diagnostics.OPT_LOCAL_FILES: True,
                diagnostics.OPT_OMD_CONFIG: True,
                diagnostics.OPT_PERFORMANCE_GRAPHS: True,
                diagnostics.OPT_CHECKMK_OVERVIEW: True,
            },
            {
                diagnostics.OPT_LOCAL_FILES: True,
                diagnostics.OPT_OMD_CONFIG: True,
                diagnostics.OPT_PERFORMANCE_GRAPHS: True,
                diagnostics.OPT_CHECKMK_OVERVIEW: True,
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
    ],
)
def test_diagnostics_deserialize(cl_parameters, modes_parameters, expected_parameters):
    assert diagnostics.deserialize_cl_parameters(cl_parameters) == expected_parameters
    assert diagnostics.deserialize_modes_parameters(modes_parameters) == expected_parameters


# 'sensitivity_value == 3' means not found
@pytest.mark.parametrize(
    "component, sensitivity_values",
    [
        (diagnostics.OPT_COMP_GLOBAL_SETTINGS, [0, 1, 3, 3, 3, 3]),
        (diagnostics.OPT_COMP_HOSTS_AND_FOLDERS, [3, 3, 2, 2, 1, 0]),
        (diagnostics.OPT_COMP_NOTIFICATIONS, [3, 3, 2, 2, 1, 0]),
        (diagnostics.OPT_COMP_BUSINESS_INTELLIGENCE, [3, 3, 3, 3, 3, 3, 1]),
    ],
)
def test_diagnostics_get_checkmk_file_info_by_name(component, sensitivity_values):
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
            diagnostics.get_checkmk_file_info(rel_filepath, component).sensitivity.value == result
        )


# This list of files comes from an empty Checkmk site setup
# and may be incomplete.
# 'sensitivity_value == 3' means not found
@pytest.mark.parametrize(
    "rel_filepath, sensitivity_value",
    [
        ("apache.conf", 3),
        ("apache.d/wato/global.mk", 3),
        ("conf.d/microcore.mk", 3),
        ("conf.d/mkeventd.mk", 3),
        ("conf.d/pnp4nagios.mk", 3),
        ("conf.d/wato/.wato", 0),
        ("conf.d/wato/alert_handlers.mk", 2),
        ("conf.d/wato/contacts.mk", 2),
        ("conf.d/wato/global.mk", 1),
        ("conf.d/wato/groups.mk", 0),
        ("conf.d/wato/hosts.mk", 2),
        ("conf.d/wato/notifications.mk", 2),
        ("conf.d/wato/rules.mk", 2),
        ("conf.d/wato/tags.mk", 1),
        ("dcd.d/wato/global.mk", 3),
        ("liveproxyd.d/wato/global.mk", 3),
        ("main.mk", 0),
        ("mkeventd.d/wato/rules.mk", 2),
        ("mkeventd.d/wato/global.mk", 3),
        ("mkeventd.mk", 3),
        ("mknotifyd.d/wato/global.mk", 1),
        ("multisite.d/liveproxyd.mk", 3),
        ("multisite.d/mkeventd.mk", 3),
        ("multisite.d/sites.mk", 3),
        ("multisite.d/wato/global.mk", 1),
        ("multisite.d/wato/groups.mk", 0),
        ("multisite.d/wato/tags.mk", 1),
        ("multisite.d/wato/users.mk", 2),
        ("multisite.mk", 3),
        ("rrdcached.d/wato/global.mk", 3),
        ("alerts.log", 3),
        ("apache/access_log", 3),
        ("apache/error_log", 3),
        ("apache/stats", 3),
        ("cmc.log", 1),
        ("dcd.log", 3),
        ("diskspace.log", 3),
        ("liveproxyd.log", 3),
        ("liveproxyd.state", 3),
        ("mkeventd.log", 3),
        ("mknotifyd.log", 1),
        ("mknotifyd.state", 1),
        ("notify.log", 1),
        ("rrdcached.log", 3),
        ("web.log", 1),
    ],
)
def test_diagnostics_file_info_of_comp_notifications(rel_filepath, sensitivity_value):
    assert (
        diagnostics.get_checkmk_file_info(
            rel_filepath, diagnostics.OPT_COMP_NOTIFICATIONS
        ).sensitivity.value
        == sensitivity_value
    )
