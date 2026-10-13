#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The settings the action dialogs offer to edit, read back so the dialogs honour them.

The classic command forms seed their options from these two global settings; the panels
link to the same settings, so they have to read them from the same place or the link would
lead somewhere that changes nothing.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import get_args, Literal

from cmk.gui.config import Config
from cmk.gui.i18n import _u

UntilKeyword = Literal["next_day", "next_week", "next_month", "next_year"]

# The classic form's own fallback: `ack_expire` is absent from the setting's default, so
# there is nothing to read unless an admin has set one.
_DEFAULT_EXPIRE_SECONDS = 3600


@dataclass(frozen=True, kw_only=True)
class AcknowledgeDefaults:
    sticky: bool
    persistent: bool
    notify: bool
    expire_seconds: int


@dataclass(frozen=True, kw_only=True)
class DowntimePreset:
    """A duration the site offers, either a fixed span or the end of a calendar period.

    `end` is one slot rather than two, because that is what the setting stores: the form's
    duration/until discriminator never reaches disk, so a range carries a span in seconds or
    a keyword, and can carry neither both nor none.
    """

    title: str
    end: int | UntilKeyword


def acknowledge_defaults(config: Config) -> AcknowledgeDefaults:
    values = config.acknowledge_problems
    return AcknowledgeDefaults(
        sticky=bool(values.get("ack_sticky", False)),
        persistent=bool(values.get("ack_persistent", False)),
        notify=bool(values.get("ack_notify", True)),
        expire_seconds=int(values.get("ack_expire", _DEFAULT_EXPIRE_SECONDS)),
    )


def downtime_presets(config: Config) -> Sequence[DowntimePreset]:
    """The configured time ranges, titles translated the way the classic form translates them."""
    presets: list[DowntimePreset] = []
    for time_range in config.user_downtime_timeranges:
        end = time_range["end"]
        title = _u(time_range["title"])
        if isinstance(end, int) or end in get_args(UntilKeyword):
            presets.append(DowntimePreset(title=title, end=end))
        # Anything else is an end the panel has no way to render, so leave it out rather
        # than offer a duration that would not resolve to a time.
    return presets
