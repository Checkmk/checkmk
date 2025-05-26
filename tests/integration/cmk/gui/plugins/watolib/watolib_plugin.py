#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import override

import cmk.utils.paths
from cmk.utils.config_warnings import ConfigurationWarnings

from cmk.gui.type_defs import GlobalSettings
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    config_domain_registry,
    SerializedSettings,
)


class ConfigDomainTest(ABCConfigDomain):
    needs_sync = True
    needs_activation = True

    @override
    @classmethod
    def ident(cls):
        return "test"

    @override
    def config_dir(self) -> Path:
        return cmk.utils.paths.default_config_dir / "test.d/wato"

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def default_globals(self) -> GlobalSettings:
        return {}


config_domain_registry.register(ConfigDomainTest())
