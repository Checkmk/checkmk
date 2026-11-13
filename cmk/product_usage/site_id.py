#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""The random site ID product usage analytics sends."""

import typing
from pathlib import Path
from uuid import UUID, uuid4

ProductUsageSiteId = typing.NewType("ProductUsageSiteId", UUID)


def product_usage_site_id_file_path(var_dir: Path) -> Path:
    return var_dir / "product_usage" / "site_id"


def get_product_usage_site_id(file_path: Path) -> ProductUsageSiteId | None:
    try:
        with file_path.open("r", encoding="utf-8") as fp:
            return ProductUsageSiteId(UUID(fp.read()))
    except FileNotFoundError, ValueError:
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
