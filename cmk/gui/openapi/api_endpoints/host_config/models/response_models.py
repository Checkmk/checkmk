#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Annotated, Literal

from pydantic import AfterValidator

from cmk.gui.openapi.api_endpoints.models.folder_models import FolderModel
from cmk.gui.openapi.api_endpoints.models.host_attribute_models import HostAttributeResponseModel
from cmk.gui.openapi.framework.model import api_field, api_model, ApiOmitted
from cmk.gui.openapi.framework.model.base_models import (
    DomainObjectCollectionModel,
    DomainObjectModel,
    LinkModel,
)
from cmk.gui.openapi.framework.model.common_fields import AnnotatedFolder
from cmk.gui.openapi.framework.model.converter import HostConverter
from cmk.gui.openapi.framework.model.response import ApiErrorDataclass


@api_model
class HostExtensionsModel:
    folder: AnnotatedFolder = api_field(description="The folder, in which this host resides.")
    attributes: HostAttributeResponseModel = api_field(description="Attributes of this host.")
    effective_attributes: HostAttributeResponseModel | ApiOmitted = api_field(
        description="All attributes of this host and all parent folders.",
        default_factory=ApiOmitted,
    )
    is_cluster: bool = api_field(
        description="If this is a cluster host, i.e. a container for other hosts."
    )
    is_offline: bool = api_field(description="Whether the host is offline.")
    cluster_nodes: Sequence[Annotated[str, AfterValidator(HostConverter().host_name)]] | None = (
        api_field(
            description="In the case this is a cluster host, these are the cluster nodes.",
        )
    )


@api_model
class HostMembersModel(DomainObjectModel):
    folder_config: FolderModel = api_field(
        description="The folder in which this host resides. It is represented by a hexadecimal "
        "identifier which is it's 'primary key'. The folder can be accessed via the "
        "`self`-link provided in the links array."
    )


@api_model
class HostConfigModel(DomainObjectModel):
    domainType: Literal["host_config"] = api_field(description="The domain type of the object.")
    # The list endpoint omits the links entirely when they were not requested
    # (``include_links=False``), matching the behaviour of the previous implementation.
    links: list[LinkModel] | ApiOmitted = api_field(  # type: ignore[assignment]
        title="Links",
        description="List of links to other resources.",
        default_factory=ApiOmitted,
    )
    members: HostMembersModel | None = api_field(
        description="All the members of the host object.",
    )
    extensions: HostExtensionsModel = api_field(
        description="All the data and metadata of this host."
    )


@api_model
class HostConfigCollectionModel(DomainObjectCollectionModel):
    domainType: Literal["host_config"] = api_field(
        description="The domain type of the objects in the collection",
        example="host_config",
    )
    # TODO: add proper example
    value: list[HostConfigModel] = api_field(description="A list of host objects", example="")


@api_model
class FailedHostsModel:
    succeeded_hosts: HostConfigCollectionModel = api_field(
        description="Hosts that were successfully created.",
    )
    failed_hosts: dict[str, str] = api_field(
        description="A mapping of host that failed to be created, with the reason for failure.",
    )


@api_model
class BulkHostActionWithFailedHostsModel(ApiErrorDataclass):
    status: int = api_field(
        title="HTTP status code", description="The HTTP status code.", example=400
    )
    title: str = api_field(
        title="Error title",
        description="A summary of the problem.",
        example="Some actions failed",
    )
    detail: str = api_field(
        title="Error message",
        description="Detailed information on what exactly went wrong.",
        example="Some of the actions were performed but the following were faulty and were skipped: ['host1', 'host2'].",
    )
    ext: FailedHostsModel = api_field(
        title="Error extensions",
        description="Details for which hosts have failed",
    )
