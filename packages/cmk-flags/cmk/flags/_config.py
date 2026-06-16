#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Release flags: site-wide, file-backed boolean feature toggles.

A release flag lets us merge unfinished work to the master and 2.5 branches
without exposing it to users. Flags are declared as fields on the single
:class:`ReleaseFlagConfig` model and persisted as JSON in
``$OMD_ROOT/etc/check_mk/release_flag.json``.

Every flag carries the metadata that keeps it from rotting: a description, the
ticket tracking its removal, the version by which it must be gone, and an owner.
The tests enforce that flags are removed before their deadline.
"""

from pathlib import Path
from typing import cast, Final

from pydantic import BaseModel, ConfigDict, Field
from pydantic.fields import FieldInfo

CONFIG_FILENAME: Final = "release_flag.json"


def release_field(
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


class ReleaseFlagConfig(BaseModel):
    """The single source of truth for all release flags.

    Flags are declared per branch via ``release_field()``, e.g.::

        new_monitoring_views: Annotated[bool, release_field(
            description="Enable the experimental new monitoring views.",
            remove_ticket="CMK-12345",
            remove_after="2.6.0",
            owner="some.owner@checkmk.com",
        )]

    ``extra="ignore"`` drops keys for flags that have already been removed, so
    deleting a flag does not break sites whose config file still mentions it.
    """

    model_config = ConfigDict(frozen=True, extra="ignore")


def load_release_flags(config_dir: Path) -> ReleaseFlagConfig:
    """Read the release flags from ``config_dir``, defaulting to all-off."""
    try:
        raw = (config_dir / CONFIG_FILENAME).read_text()
    except FileNotFoundError:
        return ReleaseFlagConfig()
    return ReleaseFlagConfig.model_validate_json(raw)
