#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""The options a user picks from in a drop-down.

An id of None marks the entry that stands for "nothing selected".
"""

ChoiceText = str
ChoiceId = str | None
Choice = tuple[ChoiceId, ChoiceText]
Choices = list[Choice]  # TODO: Change to Sequence, perhaps DropdownChoiceEntries[str]

__all__ = ["Choice", "ChoiceId", "ChoiceText", "Choices"]
