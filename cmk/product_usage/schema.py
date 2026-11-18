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


class DistributedMonitoring(pydantic.BaseModel):
    is_remote_setup_site: bool = pydantic.Field(
        description=(
            "True if the site is a remote site of a distributed monitoring setup that the"
            " central site configures. Its users and configuration then come from the central"
            " site. False on standalone and central sites, and on remote sites that are"
            " connected for monitoring only. A site that was removed from a distributed"
            " monitoring setup and has not become a central site still reports true."
        ),
        examples=[False],
    )


class LanguageCounts(pydantic.BaseModel):
    count_per_language: dict[str, int] = pydantic.Field(
        description=(
            "The number of users per user interface language in use, by language code:"
            " the language set in the user's profile, or the default language if the profile"
            ' sets none. Languages that Checkmk does not ship are counted as "custom".'
        ),
        examples=[{"de": 3, "en": 2}],
    )
    count_with_default_language: int = pydantic.Field(
        description=(
            "The number of these users whose profile sets no language, so that they use the"
            " default language."
        ),
        examples=[1],
    )


class UserLanguages(pydantic.BaseModel):
    active: LanguageCounts = pydantic.Field(
        description=(
            "Users who logged in to the user interface or the REST API of this site, or used"
            " the user interface, in the last 30 days: the users that users.humans.active"
            " counts for 30 days."
        ),
        examples=[{"count_per_language": {"de": 3, "en": 2}, "count_with_default_language": 1}],
    )
    inactive: LanguageCounts = pydantic.Field(
        description=(
            "Users who did not log in to the user interface or the REST API of this site, nor"
            " use the user interface, in the last 30 days."
        ),
        examples=[{"count_per_language": {"en": 4}, "count_with_default_language": 2}],
    )


class Languages(pydantic.BaseModel):
    default_language: str = pydantic.Field(
        description=(
            "The default language of the user interface, as a language code."
            ' A language that Checkmk does not ship is reported as "custom".'
        ),
        examples=["en"],
    )
    users: UserLanguages = pydantic.Field(
        description=(
            "The user interface languages in use by interactive users, split into active and"
            " inactive users. Automation users are not counted."
            " On a remote site that the central site configures, the users are copied from the"
            " central site (see distributed_monitoring.is_remote_setup_site)."
        ),
        examples=[
            {
                "active": {
                    "count_per_language": {"de": 3, "en": 2},
                    "count_with_default_language": 1,
                },
                "inactive": {"count_per_language": {"en": 4}, "count_with_default_language": 2},
            }
        ],
    )


class Metadata(typing.TypedDict):
    version: str
    namespace: str
    name: str


class SelfDescribingModel(pydantic.BaseModel):
    metadata: typing.ClassVar[Metadata]

    def model_dump_with_metadata(self) -> dict[str, typing.Any]:
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
        description=(
            "The number of folders on the site. Names and paths are never collected."
            " On a remote site that the central site configures, the folders are copied from the"
            " central site (see distributed_monitoring.is_remote_setup_site)."
        ),
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
            " On a remote site that the central site configures, the users are copied from the"
            " central site (see distributed_monitoring.is_remote_setup_site)."
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
    distributed_monitoring: DistributedMonitoring | None = pydantic.Field(
        default=None,
        description="The role of the site in a distributed monitoring setup.",
        examples=[{"is_remote_setup_site": False}],
    )
    languages: Languages | None = pydantic.Field(
        default=None,
        description=(
            "The languages of the user interface: the default language of the site and the number"
            " of active and inactive users per language in use. User names are never collected."
        ),
        examples=[
            {
                "default_language": "en",
                "users": {
                    "active": {
                        "count_per_language": {"de": 3, "en": 2},
                        "count_with_default_language": 1,
                    },
                    "inactive": {"count_per_language": {"en": 4}, "count_with_default_language": 2},
                },
            }
        ],
    )
    grafana: GrafanaUsageData | None = pydantic.Field(
        default=None,
        description=(
            "This field captures technical details regarding the Grafana plug-in connection."
            " If the site is not connected to the Grafana plug-in, this field returns null."
        ),
        examples=[{"is_used": True, "version": "12.3.0", "is_grafana_cloud": False}],
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

    site_created_at: int | None = pydantic.Field(
        default=None,
        description="Unix timestamp in seconds of when the site was created.",
        examples=[1767700800],
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
