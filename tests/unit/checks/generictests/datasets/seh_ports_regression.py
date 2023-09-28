#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# fmt: off
# mypy: disable-error-code=var-annotated


checkname = "seh_ports"

info = [
    [
        ["2.0", "20848_Ent_GNSMART2", "010.099.005.209", "15"],
        ["3.0", "20673_GNSMART1_Daten", "010.028.103.077", "4"],
        ["4.0", "20557_Ent_SSR-Post", "010.028.103.076", "5"],
        ["5.0", "20676_Postprocessing", "010.028.103.075", "6"],
        ["6.0", "20675_Postprocessing", "SAPOS-Admin (010.099.005.208)", "7"],
        ["7.0", "20785_Ent_GNSMART2", "010.099.005.111", "8"],
        ["8.0", "20786_Ent_GNSMART2", "010.099.005.202", "12"],
        ["9.0", "20737_GNSMART1_Vernetzung_NI", "010.028.103.078", "10"],
        ["10.0", "20119_Postprocessing", "ent.westphal (010.028.130.016)", "20"],
        ["12.0", "20672_GNSMART1_Vernetzung_NI", "SAPOS-Admin (010.099.005.205)", "3"],
        ["13.0", "20674_GNSMART1_alles", "010.099.005.102", "14"],
        ["14.0", "20414_SSR-Post", "010.099.005.112", "19"],
        ["15.0", "20833_GNSMART1_Vernetzung_DE", "010.099.005.207", "16"],
        ["16.0", "20606_GNSMART1_PE-Client", "SAPOS-Admin (010.099.005.204)", "17"],
        ["17.0", "20387_GNSMART1_Daten", "SAPOS-Admin (010.099.005.206)", "18"],
        ["18.0", "20600_GNSMART1_RxTools", "-", "0"],
        ["19.0", "20837_Ent_GNSMART2", "Available", "2"],
        ["20.0", "Test", "SAPOS-Admin (010.099.005.203)", "9"],
        ["21.0", "", "010.099.005.114", "13"],
    ]
]

discovery = {
    "": [
        ("10", {"status_at_discovery": "010.028.103.078"}),
        ("12", {"status_at_discovery": "010.099.005.202"}),
        ("13", {"status_at_discovery": "010.099.005.114"}),
        ("14", {"status_at_discovery": "010.099.005.102"}),
        ("15", {"status_at_discovery": "010.099.005.209"}),
        ("16", {"status_at_discovery": "010.099.005.207"}),
        ("17", {"status_at_discovery": "SAPOS-Admin (010.099.005.204)"}),
        ("18", {"status_at_discovery": "SAPOS-Admin (010.099.005.206)"}),
        ("19", {"status_at_discovery": "010.099.005.112"}),
        ("2", {"status_at_discovery": "Available"}),
        ("20", {"status_at_discovery": "ent.westphal (010.028.130.016)"}),
        ("3", {"status_at_discovery": "SAPOS-Admin (010.099.005.205)"}),
        ("4", {"status_at_discovery": "010.028.103.077"}),
        ("5", {"status_at_discovery": "010.028.103.076"}),
        ("6", {"status_at_discovery": "010.028.103.075"}),
        ("7", {"status_at_discovery": "SAPOS-Admin (010.099.005.208)"}),
        ("8", {"status_at_discovery": "010.099.005.111"}),
        ("9", {"status_at_discovery": "SAPOS-Admin (010.099.005.203)"}),
    ]
}

checks = {
    "": [
        (
            "8",
            {"status_at_discovery": "010.099.005.111"},
            [
                (0, "Tag: 20786_Ent_GNSMART2", []),
                (0, "Status: 010.099.005.111", []),
            ],
        ),
        (
            "9",
            {"status_at_discovery": "Available"},
            [
                (0, "Tag: 20737_GNSMART1_Vernetzung_NI", []),
                (0, "Status: SAPOS-Admin (010.099.005.203)", []),
                (1, "Status during discovery: Available", []),
            ],
        ),
        (
            "9",
            {"status_at_discovery": None},
            [
                (0, "Tag: 20737_GNSMART1_Vernetzung_NI", []),
                (0, "Status: SAPOS-Admin (010.099.005.203)", []),
                (1, "Status during discovery: unknown", []),
            ],
        ),
    ]
}
