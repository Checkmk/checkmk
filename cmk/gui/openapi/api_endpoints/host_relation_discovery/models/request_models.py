#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Annotated, Literal

from annotated_types import MinLen

from cmk.gui.openapi.framework.model import api_field, api_model


@api_model
class HostValueModel:
    source: Literal["label", "attribute"] = api_field(
        description="Whether the value is a host label or a custom host attribute.",
        example="label",
    )
    name: Annotated[str, MinLen(1)] = api_field(
        description="The name of the label or attribute.", example="cmdb/sn"
    )


@api_model
class SuggestEvidenceRequestModel:
    words: list[str] = api_field(
        description="Words the user typed. Each of them is reported with what it finds, "
        "even if no host carries it.",
        example=["oob"],
        default_factory=list,
    )
    values: list[HostValueModel] = api_field(
        description="Labels and attributes the user added. Each of them is reported with "
        "what it finds, however widely its values are shared.",
        example=[{"source": "label", "name": "cmdb/sn"}],
        default_factory=list,
    )
    look_in: Annotated[list[Literal["names", "values"]], MinLen(1)] = api_field(
        description="Where to look: in the host names, in the labels and attributes hosts "
        "share, or both.",
        example=["names"],
        default_factory=lambda: ["names", "values"],
    )
