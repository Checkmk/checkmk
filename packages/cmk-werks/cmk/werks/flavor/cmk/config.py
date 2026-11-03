#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from contextlib import suppress
from typing import override

from cmk.werks.tool.config import BaseConfig

from .models import EditionV2, EditionV3


class CmkConfig(BaseConfig):
    editions: list[tuple[str, str]]
    edition_components: dict[str, list[tuple[str, str]]]

    @override
    def all_components(self) -> list[tuple[str, str]]:
        return sum(self.edition_components.values(), self.components)

    @override
    def edition_choices(self) -> list[tuple[str, str]]:
        return self.editions

    @override
    def components_of(self, edition: str | None) -> list[tuple[str, str]]:
        if edition is None:
            return self.components
        return self.components + self.edition_components.get(edition, [])

    @override
    def canonical_edition(self, edition: str) -> str:
        with suppress(ValueError):
            return EditionV3.from_v2(EditionV2(edition)).value
        return edition
