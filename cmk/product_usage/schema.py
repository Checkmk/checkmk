#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import typing

import pydantic
import pydantic_core

type Checks = dict[str, CheckData]


class CheckData(typing.TypedDict):
    count: typing.Annotated[
        int,
        pydantic.Field(
            description="The number of services created by the specific check plug-in across all hosts.",
            examples=[400],
        ),
    ]
    count_hosts: typing.Annotated[
        int,
        pydantic.Field(
            description="The number of unique hosts on which the plug-in is active.",
            examples=[56],
        ),
    ]
    count_disabled: typing.Annotated[
        int,
        pydantic.Field(
            description=(
                "The number of services created by the plug-in that have been disabled via"
                ' "Disabled services" rules (Setup > Services > Service discovery rules >'
                " Disabled services)."
            ),
            examples=[15],
        ),
    ]


class GrafanaUsageData(pydantic.BaseModel):
    is_used: bool = pydantic.Field(
        description="True if Grafana is currently making active requests to the site.",
        examples=[True],
    )
    version: str = pydantic.Field(
        description="The version of Grafana detected via connection headers.",
        examples=["12.3.0"],
    )
    is_grafana_cloud: bool = pydantic.Field(
        description="True if the request originates from a Grafana Cloud instance.",
        examples=[False],
    )


ActiveUsers = typing.TypedDict(
    "ActiveUsers",
    {
        "24h": typing.Annotated[
            int,
            pydantic.Field(
                description="The number of users that were active in the last 24 hours.",
                examples=[5],
            ),
        ],
        "7d": typing.Annotated[
            int,
            pydantic.Field(
                description="The number of users that were active in the last 7 days.",
                examples=[12],
            ),
        ],
        "30d": typing.Annotated[
            int,
            pydantic.Field(
                description="The number of users that were active in the last 30 days.",
                examples=[20],
            ),
        ],
    },
)


class UserGroupData(typing.TypedDict):
    total: typing.Annotated[
        int,
        pydantic.Field(
            description="The number of users of this kind configured on the site.",
            examples=[25],
        ),
    ]
    by_role: typing.Annotated[
        dict[str, int],
        pydantic.Field(
            description=(
                "The number of users per role. Built-in roles are counted under their ID."
                " All custom roles are counted together under 'custom', their names and IDs are"
                " never collected. A user with several roles is counted once for each of them,"
                " so the sum can be larger than the total."
            ),
            examples=[{"admin": 2, "user": 20, "custom": 3}],
        ),
    ]
    by_connector_type: typing.Annotated[
        dict[str, int],
        pydantic.Field(
            description=(
                "The number of users per type of the connection the users are managed by, for"
                " example 'htpasswd', 'ldap', 'saml2' or 'oauth2'. Users of a connection that no"
                " longer exists are counted under 'unknown'. Connection IDs are never collected."
            ),
            examples=[{"htpasswd": 5, "ldap": 20}],
        ),
    ]
    active: typing.Annotated[
        ActiveUsers,
        pydantic.Field(
            description=(
                "The number of users that used the GUI or the REST API in the given period."
                " Only the counts are collected, no times of individual users."
            ),
            examples=[{"24h": 5, "7d": 12, "30d": 20}],
        ),
    ]


class UsersData(typing.TypedDict):
    humans: typing.Annotated[
        UserGroupData,
        pydantic.Field(
            description="Counts of the users that are not automation users.",
            examples=[
                {
                    "total": 25,
                    "by_role": {"admin": 2, "user": 20, "custom": 3},
                    "by_connector_type": {"htpasswd": 5, "ldap": 20},
                    "active": {"24h": 5, "7d": 12, "30d": 20},
                }
            ],
        ),
    ]
    automation: typing.Annotated[
        UserGroupData,
        pydantic.Field(
            description="Counts of the automation users.",
            examples=[
                {
                    "total": 2,
                    "by_role": {"admin": 1, "agent_registration": 1},
                    "by_connector_type": {"htpasswd": 2},
                    "active": {"24h": 1, "7d": 1, "30d": 2},
                }
            ],
        ),
    ]


class InventoryData(pydantic.BaseModel):
    hosts_with_inventory: int = pydantic.Field(
        description="The number of monitored hosts that have HW/SW Inventory data.",
        examples=[150],
    )


class AgentUpdaterData(pydantic.BaseModel):
    state: typing.Literal["ok", "warn"] = pydantic.Field(
        description=(
            'The state of the "Agent updater" item of the "Analyze configuration" page.'
            ' It is "ok" as long as the legacy agent updater is supported.'
        ),
        examples=["ok"],
    )
    count_hosts_no_updater: int = pydantic.Field(
        description=(
            "The number of hosts whose baked agent enables agent updates,"
            " but for which no updater has contacted the site in the last 7 days."
        ),
        examples=[3],
    )
    count_hosts_controller_only: int = pydantic.Field(
        description="The number of hosts that use the Agent Controller updater only.",
        examples=[97],
    )
    count_hosts_legacy_only: int = pydantic.Field(
        description="The number of hosts that use the legacy agent updater only.",
        examples=[5],
    )
    count_hosts_both_installed_by_controller: int = pydantic.Field(
        description=(
            "The number of hosts that use both updaters and whose currently installed agent"
            " package the legacy agent updater did not install. A host whose installer the"
            " site cannot name is counted here as well."
        ),
        examples=[12],
    )
    count_hosts_both_installed_by_legacy: int = pydantic.Field(
        description=(
            "The number of hosts that use both updaters and whose currently installed agent"
            " package the legacy agent updater installed."
        ),
        examples=[1],
    )


class Metadata(typing.TypedDict):
    version: str
    namespace: str
    name: str


class SelfDescribingModel(pydantic.BaseModel):
    metadata: typing.ClassVar[Metadata]

    def model_dump_with_metadata(self) -> dict[str, object]:
        return {
            "metadata": self.metadata,
            "data": self.model_dump(),
        }

    def model_dump_with_metadata_json(self, indent: int = 0) -> bytes:
        return pydantic_core.to_json(self.model_dump_with_metadata(), indent=indent)

    @classmethod
    def model_json_schema_with_metadata(cls) -> dict[str, object]:
        """JSON schema of the document written by `model_dump_with_metadata`"""
        data_schema = cls.model_json_schema()
        # Hoist the definitions to the root, where the "#/$defs/..." references point to.
        defs = data_schema.pop("$defs", {})
        return {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "metadata": {
                    "type": "object",
                    "properties": {key: {"const": value} for key, value in cls.metadata.items()},
                    "required": list(cls.metadata),
                },
                "data": data_schema,
            },
            "required": ["metadata", "data"],
            "$defs": defs,
        }


class SiteInfo(pydantic.BaseModel):
    id: pydantic.UUID4 = pydantic.Field(
        description=(
            "Random identifier of the site, generated on the first collection."
            " It is not derived from the site name or any other site property."
        ),
        examples=["3f2b8c1e-5a4d-4e7b-9c6f-2d1a0b8e7f53"],
    )
    count_hosts: int = pydantic.Field(
        description="Total number of hosts monitored on the site.",
        examples=[200],
    )
    count_services: int = pydantic.Field(
        description="Total number of services monitored on the site.",
        examples=[4500],
    )
    count_folders: int = pydantic.Field(
        description="The number of folders on the site. Names and paths are never collected.",
        examples=[15],
    )
    edition: str = pydantic.Field(
        description="The specific Checkmk edition in use.",
        examples=["cloud"],
    )
    cmk_version: str = pydantic.Field(
        description=(
            "The version of Checkmk running on the site."
            " This includes the specific build identifier."
        ),
        examples=["2.5.0-2026.01.06"],
    )
    os: str | None = pydantic.Field(
        default=None,
        description=(
            "The operating system the site is running on, as reported by the OS release files."
            " This is the same value that is reported with the license usage."
        ),
        examples=["Ubuntu 24.04.3 LTS"],
    )


class ProductUsageData(SiteInfo):
    timestamp: int = pydantic.Field(
        description="Unix timestamp in seconds of when the data was collected.",
        examples=[1767700800],
    )
    checks: Checks = pydantic.Field(
        description=(
            "These metrics help us understand which features and plug-ins are most valuable to"
            " our users. We collect counts for each plug-in used by the site. The Identifier used"
            " is the technical name/ID of the check command."
        ),
        examples=[{"check_mk-df": {"count": 400, "count_hosts": 56, "count_disabled": 15}}],
    )
    users: UsersData | None = pydantic.Field(
        default=None,
        description=(
            "Counts of the users configured on the site. User names, aliases, email addresses"
            " and other user attributes are never collected."
        ),
        examples=[
            {
                "humans": {
                    "total": 25,
                    "by_role": {"admin": 2, "user": 20, "custom": 3},
                    "by_connector_type": {"htpasswd": 5, "ldap": 20},
                    "active": {"24h": 5, "7d": 12, "30d": 20},
                },
                "automation": {
                    "total": 2,
                    "by_role": {"admin": 1, "agent_registration": 1},
                    "by_connector_type": {"htpasswd": 2},
                    "active": {"24h": 1, "7d": 1, "30d": 2},
                },
            }
        ],
    )
    inventory: InventoryData | None = pydantic.Field(
        default=None,
        description="Usage of the HW/SW Inventory.",
        examples=[{"hosts_with_inventory": 150}],
    )
    grafana: GrafanaUsageData | None = pydantic.Field(
        default=None,
        description=(
            "This field captures technical details regarding the Grafana plug-in connection."
            " If the site is not connected to the Grafana plug-in, this field returns null."
        ),
        examples=[{"is_used": True, "version": "12.3.0", "is_grafana_cloud": False}],
    )
    agent_updater: AgentUpdaterData | None = pydantic.Field(
        default=None,
        description=(
            "Which agent updater the hosts of this site run, counted over the hosts whose"
            " baked agent enables agent updates. No host names or addresses are collected."
            " This field returns null where the site cannot count them: on a remote site,"
            " and in an edition without the Agent Bakery."
        ),
        examples=[
            {
                "state": "ok",
                "count_hosts_no_updater": 3,
                "count_hosts_controller_only": 97,
                "count_hosts_legacy_only": 5,
                "count_hosts_both_installed_by_controller": 12,
                "count_hosts_both_installed_by_legacy": 1,
            }
        ],
    )


class ProductUsagePayload(SelfDescribingModel, ProductUsageData):
    metadata: typing.ClassVar[Metadata] = {
        "version": "v1",
        "namespace": "checkmk",
        "name": "product_usage_analytics",
    }


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


class CloudTrialPayload(ProductUsagePayload):
    metadata: typing.ClassVar[Metadata] = {
        "version": "v1",
        "namespace": "checkmk",
        "name": "cloud_trial_analytics",
    }

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
    sessions: None = pydantic.Field(
        default=None,
        description=(
            "Every stored login session with its start and last activity timestamps."
            " Sessions are not attributed to a user."
        ),
        examples=[None],
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
