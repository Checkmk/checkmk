#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from pathlib import Path

from cmk.livestatus_client import LocalConnection
from cmk.product_telemetry.exceptions import (
    SiteInfoInvalidError,
    SiteInfoItemsInvalidError,
)
from cmk.product_telemetry.schema import SiteInfo
from cmk.utils.licensing.helper import get_instance_id_file_path, load_instance_id
from cmk.utils.livestatus_helpers.queries import Query
from cmk.utils.livestatus_helpers.tables import Status
from cmk.utils.paths import omd_root


def collect(cmk_config_dir: Path) -> SiteInfo:
    # TODO: don't use licensing site ID otherwise telemetry data won't be anonymous anymore. Use a
    # site ID dedicated to product telemetry.
    site_id = load_instance_id(get_instance_id_file_path(omd_root))

    query = Query(
        [Status.num_hosts, Status.num_services, Status.edition, Status.program_version]
    ).compile()

    connection = LocalConnection()
    response = connection.query(query)

    if len(response) != 1:
        raise SiteInfoInvalidError

    if len(response[0]) != 4:
        raise SiteInfoItemsInvalidError

    wato_path = Path(cmk_config_dir / "wato")

    response_dict = dict(
        id=str(site_id),
        count_hosts=response[0][0],
        count_services=response[0][1],
        count_folders=get_number_of_folders(str(wato_path)),
        edition=response[0][2],
        cmk_version=response[0][3],
    )

    return SiteInfo.model_validate(response_dict)


def get_number_of_folders(path: str) -> int:
    count = 0
    with os.scandir(path) as entries:
        for entry in entries:
            if entry.is_dir(follow_symlinks=False):
                count += 1
                count += get_number_of_folders(entry.path)
    return count
