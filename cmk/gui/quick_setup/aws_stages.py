#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Mapping

from cmk.utils.i18n import _

from cmk.gui.quick_setup.definitions import QuickSetup, QuickSetupId, QuickSetupStage, StageId


def prepare_aws(stage_id: int) -> QuickSetupStage:
    return QuickSetupStage(
        stage_id=stage_id,
        title=_("Prepare AWS for Checkmk"),
        components=[],
    )


def aws_stages() -> Mapping[StageId, QuickSetupStage]:
    return {1: prepare_aws(1)}


aws_quicksetup = QuickSetup(
    id=QuickSetupId("aws_quicksetup"),
    stages=aws_stages(),
)
