#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The stored configuration of the ``mk_oracle_unified`` agent rule.

What an ``agent_config:mk_oracle_unified`` rule looks like in ``rules.mk``, which
is also what the Setup form offers. The bakery parses it back to build
``mk-oracle.yml``, and the legacy ruleset migration in ``cmk/update_config``
writes it.

A key whose shape changes gets a new name rather than a new meaning, so that the
name alone says which shape a stored value has. ``_migrate`` in
``rulesets/mk_oracle_unified.py`` maps the retired names onto the current ones.

``SecretT`` is the one field the two sides model differently. A rule stores a
password store reference, and the backend has replaced it with a ``Secret`` by
the time the bakery sees the value. Setup uses the default parametrisation, the
bakery ``[Secret]``.
"""

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel

StoredPassword = tuple[
    Literal["cmk_postprocessed"],
    Literal["explicit_password", "stored_password"],
    tuple[str, str],
]

# Present means collected, and the flag says whether it is cached. A section
# that is not collected is absent.
type StoredSectionOptions = Mapping[str, bool]
type AuthType = Literal["standard", "wallet"]
type UseHostClient = tuple[Literal["auto", "never", "always"], None] | tuple[Literal["custom"], str]


class StoredAuthUserPasswordData[SecretT = StoredPassword](BaseModel):
    username: str | None
    password: SecretT | None


class StoredAsmAuthConf[SecretT = StoredPassword](BaseModel):
    username: str
    password: SecretT
    role: str | None = None


class StoredAuthConf[SecretT = StoredPassword](BaseModel):
    auth_type: tuple[AuthType, StoredAuthUserPasswordData[SecretT] | None] | None = None
    role: str | None = None
    asm_auth: StoredAsmAuthConf[SecretT] | None = None


class StoredDescriptorConf(BaseModel):
    # All three are optional, as they were before the revision. The form asks for
    # a service name, but a rule migrated from the legacy ruleset may name an
    # instance only.
    service_name: str | None = None
    instance_name: str | None = None
    sid: str | None = None


# An alias and a SID are a single string. A service name is three fields, so it
# keeps a dictionary of its own.
type StoredOracleId = (
    tuple[Literal["alias"], str]
    | tuple[Literal["sid"], str]
    | tuple[Literal["descriptor"], StoredDescriptorConf]
)


class StoredConnectionConf(BaseModel):
    host: str | None = None
    port: int | None = None
    timeout: int | None = None
    tns_admin: str | None = None
    oracle_local_registry: str | None = None


class StoredDiscoveryConf(BaseModel):
    enabled: Literal["enabled", "disabled"]
    include: list[str] | None = None
    exclude: list[str] | None = None


class StoredOracleSafeEntries(BaseModel):
    safe_entries: list[str] | None = None


class StoredExcludedSectionConf(BaseModel):
    target_id: StoredOracleId
    sections: list[str] | None = None


class StoredInstanceConf[SecretT = StoredPassword](BaseModel):
    oracle_id: StoredOracleId
    auth: StoredAuthConf[SecretT] | None = None
    connection: StoredConnectionConf | None = None
    piggyback_host: str | None = None


class StoredConfig[SecretT = StoredPassword](BaseModel):
    deploy_rev2: Literal["deploy", "do_not_deploy"]
    auth: StoredAuthConf[SecretT]
    connection: StoredConnectionConf
    cache_age: int | None = None
    custom_metrics_cache_age: int | None = None
    discovery: StoredDiscoveryConf | None = None
    sections: StoredSectionOptions | None = None
    excluded_sections: list[StoredExcludedSectionConf] | None = None
    instances_rev2: list[StoredInstanceConf[SecretT]] | None = None
    # Dropped from the form by CMK-37226, but a rule written before that still
    # carries it and the bakery still writes it to mk-oracle.yml. CMK-37191
    # dropped max_queries the same way, and the bakery no longer writes it, so
    # it is not a field here at all.
    max_connections: int | None = None
    ignore_db_name: bool | None = None
    use_host_client: UseHostClient | None = None
    validate_permissions: (
        tuple[Literal["enabled"], StoredOracleSafeEntries | None]
        | tuple[Literal["disabled"], None]
        | None
    ) = None

    def get_active_cache_age(self) -> int:
        """Return cache age in seconds, default is 600 seconds: must be in sync with agent plugin"""
        return self.cache_age or 600

    def get_active_custom_metrics_cache_age(self) -> int:
        """Return metrics cache age in seconds, default is 600 seconds: must be in sync with agent plugin"""
        return self.custom_metrics_cache_age or 600
