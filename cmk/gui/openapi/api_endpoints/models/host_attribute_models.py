#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from dataclasses import dataclass
from typing import Annotated

from pydantic import AfterValidator

from cmk.utils.tags import TagGroupID

from cmk.gui.openapi.endpoints._common.host_attribute_schemas import built_in_tag_group_config
from cmk.gui.openapi.framework.model import api_field, ApiOmitted


def _validate_tag_id(tag_id: str, built_in_tag_group_id: TagGroupID) -> str:
    tag_group = built_in_tag_group_config.get_tag_group(built_in_tag_group_id)
    assert tag_group is not None

    if tag_id not in [
        None if _tag_id is None else str(_tag_id) for _tag_id in tag_group.get_tag_ids()
    ]:
        raise ValueError(f"Tag ID '{tag_id}' is not valid for tag group '{built_in_tag_group_id}'.")

    return tag_id


@dataclass(kw_only=True)
class BaseHostTagGroupModel:
    tag_address_family: (
        Annotated[str, AfterValidator(lambda v: _validate_tag_id(v, TagGroupID("address_family")))]
        | ApiOmitted
    ) = api_field(description="The IP address family of the host.", example="ip-v4-only")

    tag_agent: (
        Annotated[str, AfterValidator(lambda v: _validate_tag_id(v, TagGroupID("agent")))]
        | ApiOmitted
    ) = api_field(description="Agent and API integrations", example="cmk-agent")

    tag_snmp_ds: (
        Annotated[str, AfterValidator(lambda v: _validate_tag_id(v, TagGroupID("snmp_ds")))]
        | ApiOmitted
    ) = api_field(description="The SNMP data source of the host.", example="snmp-v2")

    tag_piggyback: (
        Annotated[str, AfterValidator(lambda v: _validate_tag_id(v, TagGroupID("piggyback")))]
        | ApiOmitted
    ) = api_field(description="Use piggyback data for this host.", example="piggyback")
