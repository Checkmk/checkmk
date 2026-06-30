#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from cmk.gui.openapi.framework.api_config import APIVersion
from cmk.gui.openapi.framework.model.base_models import LinkModel
from cmk.gui.openapi.restful_objects.constructors import (
    expand_rel,
    object_href,
    versioned_absolute_url,
)
from cmk.gui.openapi.restful_objects.type_defs import DomainType


def generate_links(
    domain_type: DomainType,
    identifier: str,
    editable: bool = True,
    deletable: bool = True,
    extra_links: list[LinkModel] | None = None,
    self_link: LinkModel | None = None,
    *,
    host_url: str | None = None,
    version: APIVersion | None = None,
) -> list[LinkModel]:
    # When the caller provides the request's host_url and API version, the self/update/delete
    # hrefs are built absolute so clients can follow them directly. Otherwise they stay relative.
    href = object_href(domain_type, identifier)
    uri = (
        versioned_absolute_url(href, host_url=host_url, version=version.value)
        if host_url is not None and version is not None
        else href
    )

    if self_link is not None:
        links = [self_link]
    else:
        links = [
            LinkModel(
                rel="self", href=uri, domainType="link", method="GET", type="application/json"
            )
        ]

    if editable:
        links.append(
            LinkModel(
                rel=expand_rel(".../update", {}),
                domainType="link",
                href=uri,
                method="PUT",
                type="application/json",
            )
        )
    if deletable:
        links.append(
            LinkModel(
                rel=expand_rel(".../delete", {}),
                href=uri,
                domainType="link",
                method="DELETE",
                type="application/json",
            )
        )
    if extra_links:
        links.extend(extra_links)

    return links
