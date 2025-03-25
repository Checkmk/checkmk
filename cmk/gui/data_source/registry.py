#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from __future__ import annotations

import hashlib

from cmk.ccc.plugin_registry import Registry

from cmk.gui.type_defs import Row

from .base import ABCDataSource


class DataSourceRegistry(Registry[type[ABCDataSource]]):
    def plugin_name(self, instance: type[ABCDataSource]) -> str:
        return instance().ident

    # TODO: Sort the datasources by (assumed) common usage
    def data_source_choices(self) -> list[tuple[str, str]]:
        datasources = []
        for ident, ds_class in self.items():
            datasources.append((ident, ds_class().title))
        return sorted(datasources, key=lambda x: x[1])


data_source_registry = DataSourceRegistry()


def row_id(datasource: str, row: Row) -> str:
    """Calculates a uniq id for each data row which identifies the current
    row accross different page loadings."""
    key = ""
    for col in data_source_registry[datasource]().id_keys:
        key += "~%s" % row[col]
    return hashlib.sha256(key.encode("utf-8")).hexdigest()
