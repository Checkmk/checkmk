#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostUpdateAttributeModel
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted


@api_model
class UpdateHost:
    attributes: HostUpdateAttributeModel | ApiOmitted = api_field(
        description=(
            "Replace all currently set attributes on the host, with these attributes. "
            "Any previously set attributes which are not given here will be removed. "
            "Can't be used together with update_attributes or remove_attributes fields."
        ),
        example={"ipaddress": "192.168.0.123"},
        default_factory=ApiOmitted,
    )

    update_attributes: HostUpdateAttributeModel | ApiOmitted = api_field(
        description=(
            "Just update the hosts attributes with these attributes. The previously set "
            "attributes will be overwritten. Can't be used together with attributes or "
            "remove_attributes fields."
        ),
        example={"ipaddress": "192.168.0.123"},
        default_factory=ApiOmitted,
    )

    remove_attributes: list[str] | ApiOmitted = api_field(
        description=(
            "A list of attributes which should be removed. Can't be used together with "
            "attributes or update attributes fields."
        ),
        example=["tag_foobar"],
        default_factory=ApiOmitted,
    )

    def __post_init__(self) -> None:
        """Only one of the attributes field is allowed at a time."""
        data = {
            "attributes": self.attributes,
            "update_attributes": self.update_attributes,
            "remove_attributes": self.remove_attributes,
        }
        set_keys = [key for key, value in data.items() if not isinstance(value, ApiOmitted)]
        if len(set_keys) > 1:
            raise ValueError(
                f"This endpoint only allows 1 action (set/update/remove) per call, you specified {len(set_keys)} actions: {', '.join(set_keys)}."
            )
