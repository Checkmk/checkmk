#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from uuid import UUID

from cmk.product_usage.site_id import (
    get_or_create_product_usage_site_id,
    get_product_usage_site_id,
    product_usage_site_id_file_path,
)
from cmk.utils.paths import var_dir


def test_get_or_create_product_usage_site_id() -> None:
    product_usage_site_id_fp = product_usage_site_id_file_path(var_dir)

    assert get_product_usage_site_id(product_usage_site_id_fp) is None

    product_usage_site_id = get_or_create_product_usage_site_id(product_usage_site_id_fp)

    assert isinstance(product_usage_site_id, UUID)

    # We get the ID again to verify it was stored correctly
    assert get_product_usage_site_id(product_usage_site_id_fp) == product_usage_site_id
