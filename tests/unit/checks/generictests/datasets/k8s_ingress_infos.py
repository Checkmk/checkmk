#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# type: ignore


checkname = "k8s_ingress_infos"

parsed = {
    "cafe-ingress": {
        "load_balancers": [{"ip": "10.0.2.15", "hostname": ""}],
        "backends": [
            ["cafe.example.com/tea", "tea-svc", 80],
            ["cafe.example.com/coffee", "coffee-svc", 80],
        ],
        "hosts": {"cafe-secret": ["cafe.example.com"]},
    }
}

discovery = {"": [("cafe.example.com/coffee", None), ("cafe.example.com/tea", None)]}

checks = {
    "": [
        (
            "cafe.example.com/coffee",
            {},
            [(0, "Ports: 80, 443", []), (0, "Service: coffee-svc:80", [])],
        ),
        ("cafe.example.com/tea", {}, [(0, "Ports: 80, 443", []), (0, "Service: tea-svc:80", [])]),
    ]
}
