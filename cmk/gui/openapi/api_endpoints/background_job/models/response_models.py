#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="mutable-override"

from typing import Literal

from cmk.gui.openapi.framework.model import api_field, api_model
from cmk.gui.openapi.framework.model.base_models import DomainObjectModel


@api_model
class StatusLogInfoModel:
    JobProgressUpdate: list[str] = api_field(
        description="The progress update logs of the background job",
        example=["Parsed configuration", "Saved configuration"],
    )
    JobResult: list[str] = api_field(
        description="The result logs of the background job",
        example=["Job finished"],
    )
    JobException: list[str] = api_field(
        description="The exception logs of the background job",
        example=["error_1", "error_2"],
    )


@api_model
class BackgroundJobStatusModel:
    state: str = api_field(
        description="The state of the background job",
        example="finished",
    )
    log_info: StatusLogInfoModel = api_field(
        description="The logs of the background job",
        example={
            "JobProgressUpdate": ["Parsed configuration", "Saved configuration"],
            "JobResult": ["Job finished"],
            "JobException": ["error_1", "error_2"],
        },
    )


@api_model
class BackgroundJobSnapshotExtensionsModel:
    site_id: str = api_field(
        description="The site ID where the background job is located",
        example="foobar",
    )
    status: BackgroundJobStatusModel = api_field(
        description="The status of the background job",
    )
    active: bool = api_field(
        description="This field indicates if the background job is running.",
        example=True,
    )


@api_model
class BackgroundJobSnapshotObjectModel(DomainObjectModel):
    domainType: Literal["background_job"] = api_field(
        description="The domain type of the object",
    )
    extensions: BackgroundJobSnapshotExtensionsModel = api_field(
        description="The attributes of the background job",
    )
