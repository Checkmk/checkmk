#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Experimental flags: site-wide, file-backed boolean feature toggles.

An experimental flag lets us merge unfinished work to the master and 2.5 branches
without exposing it to users. Flags are declared as fields on the single
:class:`ExperimentalFlagConfig` model and persisted as JSON in
``$OMD_ROOT/etc/check_mk/experimental_flag.json``.

Every flag carries the metadata that keeps it from rotting: a description, the
ticket tracking its removal, the version by which it must be gone, and an owner.
The tests enforce that flags are removed before their deadline.
"""

from pathlib import Path
from typing import Annotated, cast, Final

from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo

CONFIG_FILENAME: Final = "experimental_flag.json"


def experimental_field(
    *,
    description: str,
    remove_ticket: str,
    remove_after: str,
    owner: str,
) -> FieldInfo:
    return cast(
        FieldInfo,
        Field(
            default=False,
            json_schema_extra={
                "description": description,
                "remove_ticket": remove_ticket,
                "remove_after": remove_after,
                "owner": owner,
            },
        ),
    )


class ExperimentalFlagConfig(BaseModel):
    """The single source of truth for all experimental flags.

    Flags are declared per branch via ``experimental_field()``, e.g.::

        new_monitoring_views: Annotated[bool, experimental_field(
            description="Enable the experimental new monitoring views.",
            remove_ticket="CMK-12345",
            remove_after="2.6.0",
            owner="some.owner@checkmk.com",
        )]

    ``extra="ignore"`` drops keys for flags that have already been removed, so
    deleting a flag does not break sites whose config file still mentions it.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")

    exp_relay_active_checks: Annotated[
        bool,
        experimental_field(
            description=(
                "Run the relay-supported active checks (check_httpv2, check_cert, "
                "check_icmp) on the relay for hosts monitored by a relay, including the "
                "ad-hoc run from the service discovery page. While disabled, active "
                "checks on relay-monitored hosts are reported as not supported there."
            ),
            remove_ticket="CMK-38421",
            remove_after="3.1.0",
            owner="pablo.municio@checkmk.com",
        ),
    ] = False


def load_experimental_flags(config_dir: Path) -> ExperimentalFlagConfig:
    """Read the experimental flags from ``config_dir``, defaulting to all-off."""
    try:
        raw = (config_dir / CONFIG_FILENAME).read_text()
    except FileNotFoundError:
        return ExperimentalFlagConfig()
    return ExperimentalFlagConfig.model_validate_json(raw)
