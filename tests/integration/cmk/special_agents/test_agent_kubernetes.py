#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest  # type: ignore[import]

from kubernetes.client.models import V1ClusterRole


def test_v1_clusterrole_without_rules():
    try:
        role = V1ClusterRole(rules=None)
    except ValueError:
        pytest.fail(
            "It must be possible to instantiate a V1ClusterRole without explicit roles. "
            "This is assured by patch 0020-kubernetes-allow-empty-rules-in-clusterrole.dif.")

    assert role.rules == []
