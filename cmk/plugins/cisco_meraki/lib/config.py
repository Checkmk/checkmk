#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from meraki import DashboardAPI  # type: ignore[import-not-found]

from .constants import BASE_CACHE_FILE_DIR


@dataclass(frozen=True)
class MerakiConfig:
    # TODO: maybe not rely on the concrete type in the future.
    dashboard: DashboardAPI
    hostname: str
    section_names: Sequence[str]
    cache_dir: Path

    @classmethod
    def build(cls, dashboard: DashboardAPI, hostname: str, section_names: Sequence[str]) -> Self:
        return cls(
            dashboard=dashboard,
            hostname=hostname,
            section_names=section_names,
            cache_dir=BASE_CACHE_FILE_DIR,
        )


def get_meraki_dashboard(api_key: str, debug: bool, proxy: str | None) -> DashboardAPI:
    return DashboardAPI(
        api_key=api_key,
        print_console=True,
        output_log=False,
        suppress_logging=not (debug),
        # TODO: dashboard api always expects a string, but proxy can be None.
        requests_proxy=proxy,
    )
