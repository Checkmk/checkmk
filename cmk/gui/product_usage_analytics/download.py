#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=cmk-module-layer-violation

import logging
from pathlib import Path
from typing import override

from cmk.utils import paths

from cmk.gui.http import ContentDispositionType, response
from cmk.gui.logged_in import user
from cmk.gui.pages import Page, PageRegistry

from cmk.product_usage.collection import collect_data


def register(page_registry: PageRegistry) -> None:
    page_registry.register(PageDownloadProductUsage)


class PageDownloadProductUsage(Page):
    @classmethod
    def ident(cls) -> str:
        return "download_product_usage"

    @override
    def page(self) -> None:
        user.need_permission("general.download_product_usage_analytics")

        logger = logging.getLogger("cmk.download_product_usage")
        data = collect_data(
            Path(paths.var_dir),
            Path(paths.check_mk_config_dir),
            Path(paths.omd_root),
            logger,
        )

        filename = "checkmk_product_usage.json"

        response.set_content_type("application/json")
        response.set_content_disposition(ContentDispositionType.ATTACHMENT, filename)
        response.set_data(data.model_dump_json(indent=4).encode("utf-8"))
