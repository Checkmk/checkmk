#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Annotated

import pydantic


def platform_creation_time(cloud_config_dir: Path) -> int | None:
    # The platform passes the creation time to a site only when it creates or updates the site
    path = _cloud_edition_config_path(cloud_config_dir)
    return _CloudEditionConfig.model_validate_json(path.read_bytes()).site_created_at


def instance_id_creation_time(omd_root: Path) -> int:
    # OMD writes the instance ID only when it creates the site, on "omd create", "omd cp" and a
    # restore as a new site
    return int((omd_root / "etc/omd/instance_id").stat().st_mtime)


def _cloud_edition_config_path(cloud_config_dir: Path) -> Path:
    # Like cmk.utils.nonfree.cloud.config.load_cloud_edition_config(): the platform still
    # writes the old name
    path = cloud_config_dir / "edition_config.json"
    return path if path.exists() else cloud_config_dir / "admin_panel_url.json"


class _CloudEditionConfig(pydantic.BaseModel):
    """The part of the Cloud edition config that the collector reads"""

    site_created_at: Annotated[int, pydantic.Field(strict=True, gt=0)] | None = None
