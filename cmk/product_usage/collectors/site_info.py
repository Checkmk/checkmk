#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
import typing
from pathlib import Path
from uuid import UUID, uuid4

import cmk.ccc.version as cmk_version
from cmk.livestatus_client import LocalConnection
from cmk.livestatus_client.queries import Query
from cmk.livestatus_client.tables import Status
from cmk.product_usage.exceptions import (
    SiteInfoInvalidError,
    SiteInfoItemsInvalidError,
)
from cmk.product_usage.schema import ProductUsageSiteId, SiteInfo


def collect(cmk_config_dir: Path, var_dir: Path, omd_root: Path) -> SiteInfo:
    site_id_fp = product_usage_site_id_file_path(var_dir)
    site_id = get_or_create_product_usage_site_id(site_id_fp)

    checkmk_info = get_checkmk_info(omd_root)
    site_status = get_site_status()

    wato_path = Path(cmk_config_dir / "wato")

    response_dict = dict(
        id=str(site_id),
        count_hosts=site_status.count_hosts,
        count_services=site_status.count_services,
        count_folders=get_number_of_folders(str(wato_path)),
        edition=checkmk_info.edition,
        cmk_version=checkmk_info.version,
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


def product_usage_site_id_file_path(var_dir: Path) -> Path:
    return var_dir / "product_usage" / "site_id"


def get_product_usage_site_id(file_path: Path) -> ProductUsageSiteId | None:
    try:
        with file_path.open("r", encoding="utf-8") as fp:
            return ProductUsageSiteId(UUID(fp.read()))
    except (FileNotFoundError, ValueError):
        return None


def store_product_usage_site_id(file_path: Path, site_id: ProductUsageSiteId) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(str(site_id))


def get_or_create_product_usage_site_id(file_path: Path) -> ProductUsageSiteId:
    site_id = get_product_usage_site_id(file_path)
    if site_id is None:
        site_id = ProductUsageSiteId(uuid4())
        store_product_usage_site_id(file_path, site_id)
    return site_id


class SiteStatus(typing.NamedTuple):
    count_hosts: int
    count_services: int


def get_site_status() -> SiteStatus:
    query = Query([Status.num_hosts, Status.num_services]).compile()

    connection = LocalConnection()
    response = connection.query(query)

    if len(response) != 1:
        raise SiteInfoInvalidError

    if len(response[0]) != 2:
        raise SiteInfoItemsInvalidError

    return SiteStatus(
        count_hosts=response[0][0],
        count_services=response[0][1],
    )


class CheckmkInfo(typing.NamedTuple):
    version: str
    edition: str


def get_checkmk_info(omd_root: Path) -> CheckmkInfo:
    general_version_infos = cmk_version.get_general_version_infos(omd_root)
    return CheckmkInfo(
        version=general_version_infos["version"], edition=general_version_infos["edition"]
    )
