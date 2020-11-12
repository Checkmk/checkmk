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
        diagnostics.serialize_wato_parameters({
            "opt_info": {
                diagnostics.OPT_LOCAL_FILES: "ANY",
                diagnostics.OPT_OMD_CONFIG: "ANY",
                diagnostics.OPT_PERFORMANCE_GRAPHS: "ANY",
                diagnostics.OPT_CHECKMK_OVERVIEW: "ANY",
            },
        })) == sorted([
            diagnostics.OPT_LOCAL_FILES,
            diagnostics.OPT_OMD_CONFIG,
            diagnostics.OPT_PERFORMANCE_GRAPHS,
            diagnostics.OPT_CHECKMK_OVERVIEW,
        ])


@pytest.mark.parametrize("wato_parameters, expected_parameters", [
    ({
        "opt_info": {},
        "comp_specific": {},
    }, []),
    ({
        "opt_info": {},
        "comp_specific": {
            diagnostics.OPT_COMP_NOTIFICATIONS: {},
        },
    }, []),
    ({
        "opt_info": {
            diagnostics.OPT_CHECKMK_CONFIG_FILES: ("_ty", ["a", "b"]),
        },
        "comp_specific": {
            diagnostics.OPT_COMP_NOTIFICATIONS: {
                "config_files": ("_ty", ["a", "b"]),
                "log_files": ("_ty", ["a", "b"]),
            },
        },
    }, [
        diagnostics.OPT_CHECKMK_CONFIG_FILES,
        "a,b",
        diagnostics.OPT_CHECKMK_LOG_FILES,
        "a,b",
    ]),
    ({
        "opt_info": {
            diagnostics.OPT_CHECKMK_CONFIG_FILES: ("_ty", ["a1", "a2"]),
        },
        "comp_specific": {
            diagnostics.OPT_COMP_NOTIFICATIONS: {
                "config_files": ("_ty", ["b1", "b2"]),
                "log_files": ("_ty", ["c1", "c2"]),
            },
        },
    }, [
        diagnostics.OPT_CHECKMK_CONFIG_FILES,
        "a1,a2,b1,b2",
        diagnostics.OPT_CHECKMK_LOG_FILES,
        "c1,c2",
    ]),
])
def test_diagnostics_serialize_wato_parameters_files(wato_parameters, expected_parameters):
    assert diagnostics.serialize_wato_parameters(wato_parameters) == expected_parameters


@pytest.mark.parametrize(
    "cl_parameters, modes_parameters, expected_parameters",
    [
        ([], {}, {}),
        # boolean
        ([
            diagnostics.OPT_LOCAL_FILES,
            diagnostics.OPT_OMD_CONFIG,
            diagnostics.OPT_PERFORMANCE_GRAPHS,
            diagnostics.OPT_CHECKMK_OVERVIEW,
        ], {
            diagnostics.OPT_LOCAL_FILES: True,
            diagnostics.OPT_OMD_CONFIG: True,
            diagnostics.OPT_PERFORMANCE_GRAPHS: True,
            diagnostics.OPT_CHECKMK_OVERVIEW: True,
        }, {
            diagnostics.OPT_LOCAL_FILES: True,
            diagnostics.OPT_OMD_CONFIG: True,
            diagnostics.OPT_PERFORMANCE_GRAPHS: True,
            diagnostics.OPT_CHECKMK_OVERVIEW: True,
        }),
        # files
        ([
            diagnostics.OPT_CHECKMK_CONFIG_FILES,
            "a,b",
            diagnostics.OPT_CHECKMK_LOG_FILES,
            "a,b",
        ], {
            diagnostics.OPT_CHECKMK_CONFIG_FILES: "a,b",
            diagnostics.OPT_CHECKMK_LOG_FILES: "a,b",
        }, {
            diagnostics.OPT_CHECKMK_CONFIG_FILES: ["a", "b"],
            diagnostics.OPT_CHECKMK_LOG_FILES: ["a", "b"],
        }),
    ])
def test_diagnostics_deserialize(cl_parameters, modes_parameters, expected_parameters):
    assert diagnostics.deserialize_cl_parameters(cl_parameters) == expected_parameters
    assert diagnostics.deserialize_modes_parameters(modes_parameters) == expected_parameters
