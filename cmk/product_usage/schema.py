#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import typing
from uuid import UUID

import pydantic
import pydantic_core

type Checks = dict[str, CheckData]

ProductUsageSiteId = typing.NewType("ProductUsageSiteId", UUID)


class CheckData(typing.TypedDict):
    count: int
    count_hosts: int
    count_disabled: int


class GrafanaUsageData(pydantic.BaseModel):
    is_used: bool
    version: str
    is_grafana_cloud: bool


class Metadata(typing.TypedDict):
    version: str
    namespace: str
    name: str


class SelfDescribingModel(pydantic.BaseModel):
    __version__: str
    __namespace__: str
    __name__: str

    def model_dump_with_metadata(self) -> dict[str, typing.Any]:
        return {
            "metadata": self._metadata(),
            "data": self.model_dump(),
        }

    def _metadata(self) -> Metadata:
        return {
            "version": self.__version__,
            "namespace": self.__namespace__,
            "name": self.__name__,
        }

    def model_dump_with_metadata_json(self, indent: int = 0) -> bytes:
        return pydantic_core.to_json(self.model_dump_with_metadata(), indent=indent)


class SiteInfo(pydantic.BaseModel):
    id: pydantic.UUID4
    count_hosts: int
    count_services: int
    count_folders: int
    edition: str
    cmk_version: str


class ProductUsageData(SiteInfo):
    timestamp: int
    checks: Checks
    grafana: GrafanaUsageData | None = None


class ProductUsagePayload(SelfDescribingModel, ProductUsageData):
    __version__: str = "v1"
    __namespace__: str = "checkmk"
    __name__: str = "product_usage_analytics"


class AuditLogActorClass(pydantic.BaseModel):
    entries: int = pydantic.Field(
        description="The number of audit log entries of the actor class.",
        examples=[12],
    )
    last_entry_at: int | None = pydantic.Field(
        description=(
            "Unix timestamp in seconds of the newest audit log entry of the actor class,"
            " or null if the actor class has no entries."
        ),
        examples=[1767789000],
    )


class AuditLog(pydantic.BaseModel):
    interactive: AuditLogActorClass = pydantic.Field(
        description="Entries of the users that log in interactively.",
        examples=[{"entries": 12, "last_entry_at": 1767789000}],
    )
    automation: AuditLogActorClass = pydantic.Field(
        description="Entries of the automation users that the customer creates.",
        examples=[{"entries": 0, "last_entry_at": None}],
    )
    platform: AuditLogActorClass = pydantic.Field(
        description="Entries of the Cloud platform and of the site itself.",
        examples=[{"entries": 41, "last_entry_at": 1767790000}],
    )


class UserCount(pydantic.BaseModel):
    business: int = pydantic.Field(
        description="The number of users whose email address domain is not a free-mail domain.",
        examples=[2],
    )
    non_business: int = pydantic.Field(
        description="The number of users whose email address domain is a free-mail domain.",
        examples=[1],
    )


class Session(pydantic.BaseModel):
    started_at: int = pydantic.Field(
        description="Unix timestamp in seconds of when the session started.",
        examples=[1767789000],
    )
    last_activity: int = pydantic.Field(
        description="Unix timestamp in seconds of the last activity in the session.",
        examples=[1767790000],
    )


class CloudTrialPayload(ProductUsagePayload):
    __version__: str = "v1"
    __namespace__: str = "checkmk"
    __name__: str = "cloud_trial_analytics"

    site_created_at: None = pydantic.Field(
        default=None,
        description="Unix timestamp in seconds of when the site was created.",
        examples=[None],
    )
    count_users: UserCount | None = pydantic.Field(
        default=None,
        description=(
            "The number of users of the Cognito login who have signed in at least once,"
            " counted by business and non-business email address domain."
            " Addresses and domains are never collected."
        ),
        examples=[{"business": 2, "non_business": 1}],
    )
    sessions: list[Session] | None = pydantic.Field(
        default=None,
        description=(
            "Every stored login session with its start and last activity timestamps."
            " Sessions are not attributed to a user."
        ),
        examples=[[{"started_at": 1767789000, "last_activity": 1767790000}]],
    )
    audit_log: AuditLog | None = pydantic.Field(
        default=None,
        description=(
            "The number of audit log entries and the timestamp of the newest entry per actor"
            " class: interactive, automation and platform."
        ),
        examples=[
            {
                "interactive": {"entries": 12, "last_entry_at": 1767789000},
                "automation": {"entries": 0, "last_entry_at": None},
                "platform": {"entries": 41, "last_entry_at": 1767790000},
            }
        ],
    )
    count_hosts_default_services_only: int | None = pydantic.Field(
        default=None,
        description=(
            "The number of hosts with no services beyond Check_MK and Check_MK Discovery."
            " Hosts without services count too."
        ),
        examples=[2],
    )
