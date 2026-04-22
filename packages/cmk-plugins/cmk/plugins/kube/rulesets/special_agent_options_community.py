#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Iterable, Mapping

from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoiceElement,
    Dictionary,
)


class OpenshiftElement:
    def __call__(
        self,
        tcp_timeouts: Dictionary,
    ) -> Iterable[CascadingSingleChoiceElement[Mapping[str, object]]]:
        return ()


class TransformOpenshiftEndpoint:
    def __call__(self, p: dict[str, object]) -> dict[str, object]:
        return {
            k: v
            for k, v in p.items()
            if k != "usage_endpoint"
            or (isinstance(v, tuple) and v[0] in ("cluster_collector", "cluster-collector"))
        }
