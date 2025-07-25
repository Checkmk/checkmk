# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from collections.abc import Collection
from typing import Protocol


class AutocompleteRequirements(Protocol):
    def get_available_resource_attributes(self) -> Collection[str]: ...
