#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Final

from cmk.gui.openapi.api_endpoints.custom_host_attributes.models.response_models import (
    CustomHostAttrExtensions,
    CustomHostAttrObject,
)
from cmk.gui.openapi.framework import ETag
from cmk.gui.openapi.framework.model.constructors import generate_links
from cmk.gui.openapi.utils import ProblemException
from cmk.gui.type_defs import CustomHostAttrSpec
from cmk.gui.utils import permission_verification as permissions
from cmk.gui.watolib.custom_attributes import CustomAttrSpecs, load_custom_attrs_from_mk_file

PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.custom_attributes"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)

RW_PERMISSIONS = permissions.AllPerm(
    [
        permissions.Perm("wato.edit"),
        permissions.Perm("wato.custom_attributes"),
        permissions.Optional(permissions.Perm("wato.all_folders")),
    ]
)

DOMAIN_TYPE: Final = "custom_host_attribute"


def attr_etag(attr: CustomHostAttrSpec) -> ETag:
    return ETag(dict(attr))


def serialize_attr(attr: CustomHostAttrSpec) -> CustomHostAttrObject:
    return CustomHostAttrObject(
        domainType=DOMAIN_TYPE,
        id=attr["name"],
        title=attr["title"],
        links=generate_links(
            domain_type=DOMAIN_TYPE,
            identifier=attr["name"],
            deletable=True,
            editable=True,
        ),
        extensions=CustomHostAttrExtensions(
            topic=attr["topic"],
            help=attr["help"],
            show_in_table=attr["show_in_table"] or False,
            add_custom_macro=attr["add_custom_macro"] or False,
        ),
    )


def find_attr_or_raise(name: str, lock: bool) -> tuple[CustomHostAttrSpec, CustomAttrSpecs]:
    """AfterValidator: check the named attribute exists in the store; return name unchanged."""
    all_attrs = load_custom_attrs_from_mk_file(lock=lock)
    if (attr := next((a for a in all_attrs["host"] if a["name"] == name), None)) is None:
        raise ProblemException(
            status=404,
            title="The requested custom host attribute was not found",
            detail=f"There is no custom host attribute with the name {name!r}",
        )
    return attr, all_attrs
