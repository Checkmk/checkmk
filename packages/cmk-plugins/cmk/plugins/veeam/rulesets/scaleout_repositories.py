#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Literal

from cmk.rulesets.v1 import Title
from cmk.rulesets.v1.form_specs import DefaultValue, DictElement, Dictionary, ServiceState
from cmk.rulesets.v1.rule_specs import CheckParameters, HostAndItemCondition, Topic


def _status_element(title: Title, default: Literal[0, 1, 2, 3]) -> DictElement[Literal[0, 1, 2, 3]]:
    return DictElement[Literal[0, 1, 2, 3]](
        parameter_form=ServiceState(title=title, prefill=DefaultValue(default)),
    )


def _parameter_form_veeam_scaleout_repositories() -> Dictionary:
    return Dictionary(
        elements={
            "status_normal": _status_element(Title("Extent status: Normal"), ServiceState.OK),
            "status_pending": _status_element(Title("Extent status: Pending"), ServiceState.OK),
            "status_sealed": _status_element(Title("Extent status: Sealed"), ServiceState.OK),
            "status_evacuate": _status_element(Title("Extent status: Evacuate"), ServiceState.WARN),
            "status_maintenance": _status_element(
                Title("Extent status: Maintenance"), ServiceState.WARN
            ),
            "status_resync_required": _status_element(
                Title("Extent status: Resync required"), ServiceState.WARN
            ),
            "status_tenant_evacuating": _status_element(
                Title("Extent status: Tenant evacuating"), ServiceState.WARN
            ),
            "no_extents_state": _status_element(
                Title("State when no performance extents are configured"), ServiceState.WARN
            ),
        },
    )


rule_spec_veeam_scaleout_repositories = CheckParameters(
    name="veeam_scaleout_repositories",
    title=Title("Veeam: Scale-out repository"),
    topic=Topic.APPLICATIONS,
    parameter_form=_parameter_form_veeam_scaleout_repositories,
    condition=HostAndItemCondition(item_title=Title("Scale-out repository name")),
)
