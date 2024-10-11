#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import dataclass

from livestatus import MultiSiteConnection

from cmk.ccc.plugin_registry import Registry
from cmk.ccc.version import Edition


@dataclass(frozen=True)
class Features:
    edition: Edition
    multi_site_connection_class: type[MultiSiteConnection]


class FeaturesRegistry(Registry[Features]):
    def plugin_name(self, instance: Features) -> str:
        return str(instance.edition)


features_registry = FeaturesRegistry()
