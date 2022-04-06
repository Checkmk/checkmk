#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Any, Optional

from cmk.utils import store

from cmk.gui import watolib
from cmk.gui.globals import active_config


class BILayoutManagement:
    _config_file = Path(watolib.multisite_dir()) / "bi_layouts.mk"

    @classmethod
    def save_layouts(cls) -> None:
        store.save_to_mk_file(
            str(BILayoutManagement._config_file),
            "bi_layouts",
            active_config.bi_layouts,
            pprint_value=True,
        )

    @classmethod
    def load_bi_template_layout(cls, template_id: Optional[str]) -> Any:
        return active_config.bi_layouts["templates"].get(template_id)

    @classmethod
    def load_bi_aggregation_layout(cls, aggregation_name: Optional[str]) -> Any:
        return active_config.bi_layouts["aggregations"].get(aggregation_name)

    @classmethod
    def get_all_bi_template_layouts(cls) -> Any:
        return active_config.bi_layouts["templates"]

    @classmethod
    def get_all_bi_aggregation_layouts(cls) -> Any:
        return active_config.bi_layouts["aggregations"]
