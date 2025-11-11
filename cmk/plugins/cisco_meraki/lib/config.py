#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import Namespace
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Self

from meraki import DashboardAPI  # type: ignore[import-not-found]

from . import constants


@dataclass(frozen=True)
class MerakiConfig:
    org_ids: Sequence[str]
    section_names: Sequence[str]
    cache_dir: Path

    @classmethod
    def build(cls, args: Namespace) -> Self:
        return cls(
            org_ids=args.orgs,
            section_names=args.sections,
            cache_dir=constants.BASE_CACHE_FILE_DIR / args.hostname,
        )

    @property
    def organizations_required(self) -> bool:
        return any(
            s in self.section_names
            for s in [
                constants.SEC_NAME_LICENSES_OVERVIEW,
                constants.SEC_NAME_DEVICE_STATUSES,
                constants.SEC_NAME_SENSOR_READINGS,
            ]
        )

    @property
    def devices_required(self) -> bool:
        return any(
            s in self.section_names
            for s in [
                constants.SEC_NAME_DEVICE_STATUSES,
                constants.SEC_NAME_SENSOR_READINGS,
            ]
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
