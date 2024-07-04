#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence

from cmk.utils.i18n import _

from cmk.gui.quick_setup.definitions import QuickSetup, QuickSetupId, QuickSetupStage, StageId


def prepare_aws(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Prepare AWS for Checkmk"),
        components=[],
    )


def configure_host_and_region(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Configure host & region"),
        sub_title=_("Name your host, path and select the region you would like to monitor"),
        components=[],
    )


def configure_services_to_monitor(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Configure services to monitor"),
        sub_title=_("Select & configure AWS services you would like to monitor"),
        components=[],
    )


def review_and_run_service_discovery(stage_id: StageId) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Review & run service discovery"),
        sub_title=_("Double check your configuration"),
        components=[],
    )


def aws_stages() -> Sequence[QuickSetupStage]:
    return [
        prepare_aws(StageId(1)),
        configure_host_and_region(StageId(2)),
        configure_services_to_monitor(StageId(3)),
        review_and_run_service_discovery(StageId(4)),
    ]


aws_quicksetup = QuickSetup(
    id=QuickSetupId("aws_quick_setup"),
    stages=aws_stages(),
)
