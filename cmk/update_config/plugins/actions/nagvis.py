#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
import subprocess
from collections.abc import Callable
from logging import Logger
from pathlib import Path
from typing import override

from cmk.ccc.site import get_omd_config
from cmk.ccc.version import Version
from cmk.update_config.internal import ExpiryVersion, UpdateAction
from cmk.update_config.registry import update_action_registry
from cmk.utils import paths

_DEPRECATION_WERK = 22512

_DEMO_MAPS = frozenset(
    {
        "demo-automap.cfg",
        "demo-automap2.cfg",
        "demo-geomap.cfg",
        "demo-germany.cfg",
        "demo-ham-racks.cfg",
        "demo-load.cfg",
        "demo-muc-srv1.cfg",
        "demo-overview.cfg",
        "demo-worldmap.cfg",
    }
)


def _is_update_from_before_3_0(from_version: str | None) -> bool:
    if from_version is None:
        return False
    try:
        # OMD_FROM_VERSION carries the edition suffix, e.g. "2.5.0p17.ultimate"
        base = Version.from_str(from_version.rsplit(".", 1)[0]).base
    except ValueError:
        return False
    return base is not None and base.major < 3


def _has_own_nagvis_maps(omd_root: Path) -> bool:
    return any(
        cfg.name not in _DEMO_MAPS for cfg in (omd_root / "etc" / "nagvis" / "maps").glob("*.cfg")
    )


def _enable_nagvis() -> None:
    subprocess.run(["omd", "config", "set", "NAGVIS", "on"], check=True)


class KeepNagVisForSitesWithMaps(UpdateAction):
    """The NAGVIS hook defaults to off; sites updated with their own maps keep NagVis"""

    def __init__(
        self,
        *,
        name: str,
        title: str,
        sort_index: int,
        expiry_version: ExpiryVersion,
        omd_root: Path,
        from_version: Callable[[], str | None],
        enable_nagvis: Callable[[], None],
    ) -> None:
        super().__init__(
            name=name, title=title, sort_index=sort_index, expiry_version=expiry_version
        )
        self._omd_root = omd_root
        self._from_version = from_version
        self._enable_nagvis = enable_nagvis

    @override
    def __call__(self, logger: Logger) -> None:
        if not _is_update_from_before_3_0(self._from_version()):
            return
        if "CONFIG_NAGVIS" not in get_omd_config(self._omd_root):
            return
        if _has_own_nagvis_maps(self._omd_root):
            self._enable_nagvis()
            logger.info(
                "NagVis is deprecated, but stays enabled, as this site has NagVis maps of its "
                "own. See Werk #%(werk)d for details.",
                {"werk": _DEPRECATION_WERK},
            )
            return
        logger.warning(
            "NagVis is deprecated and has been switched off, as this site has no NagVis maps "
            'of its own. To switch it on again, run "omd config set NAGVIS on". '
            "See Werk #%(werk)d for details.",
            {"werk": _DEPRECATION_WERK},
        )


update_action_registry.register(
    KeepNagVisForSitesWithMaps(
        name="nagvis",
        title="NagVis: Keep it enabled for sites with NagVis maps",
        sort_index=100,  # can run whenever
        expiry_version=ExpiryVersion.CMK_310,
        omd_root=paths.omd_root,
        from_version=lambda: os.environ.get("OMD_FROM_VERSION"),
        enable_nagvis=_enable_nagvis,
    )
)
