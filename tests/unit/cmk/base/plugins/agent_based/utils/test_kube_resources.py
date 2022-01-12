#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.base.plugins.agent_based.utils.kube_resources import iterate_resources, Resources


def test_correct_order_resources() -> None:
    """
    Requests and limits should always be displayed in the order: Request, Limit. This is because
    requests are smaller than limits and Kubernetes follows this convention for the most part.
    """
    order = ("request", "limit")
    assert tuple(Resources.__fields__) == order
    assert (
        tuple(
            requirement[0] for requirement in iterate_resources(Resources(limit=0.0, request=0.0))
        )
        == order
    )
