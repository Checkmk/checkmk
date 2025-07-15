#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc.version import Edition
from cmk.plugins.kube.rulesets.special_agent import _migrate_and_transform


def test_migrate_raw() -> None:
    # Assemble
    value = {
        "cluster-name": "asdf",
        "token": ("password", "asdfa"),
        "kubernetes-api-server": {"endpoint_v2": "http://localhost", "verify-cert": False},
        "usage_endpoint": (
            "cluster-collector",
            {"endpoint_v2": "http://localhost", "verify-cert": False},
        ),
        "monitored-objects": ["deployments"],
    }
    # Act
    migrated = _migrate_and_transform(value, Edition.CRE)
    # Assert
    assert migrated == {
        "cluster_name": "asdf",
        "kubernetes_api_server": {"endpoint_v2": "http://localhost", "verify-cert": False},
        "monitored_objects": ["deployments"],
        "token": ("password", "asdfa"),
        "usage_endpoint": (
            "cluster-collector",
            {"endpoint_v2": "http://localhost", "verify-cert": False},
        ),
    }
