#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

__all__ = [
    "allow_host_label_conditions",
    "allow_label_conditions",
    "allow_service_label_conditions",
]


def allow_label_conditions(rulespec_name: str) -> bool:
    return allow_host_label_conditions(rulespec_name) and allow_service_label_conditions(
        rulespec_name
    )


def allow_host_label_conditions(rulespec_name: str) -> bool:
    """Rulesets that influence the labels of hosts must not use host label conditions"""
    return rulespec_name not in [
        "host_label_rules",
    ]


def allow_service_label_conditions(rulespec_name: str) -> bool:
    """Rulesets that influence the labels of services must not use service label conditions"""
    return rulespec_name not in [
        "service_label_rules",
    ]
