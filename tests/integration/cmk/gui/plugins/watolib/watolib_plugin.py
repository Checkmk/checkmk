#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import cmk.utils.paths

from cmk.gui.plugins.watolib.utils import (
    ABCConfigDomain,
    config_domain_registry,
    ConfigurationWarnings,
    SerializedSettings,
)


@config_domain_registry.register
class ConfigDomainTest(ABCConfigDomain):
    needs_sync = True
    needs_activation = True

    @classmethod
    def ident(cls):
        return "test"

    def config_dir(self):
        return cmk.utils.paths.default_config_dir + "/test.d/wato/"

    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    def default_globals(self):
        return {}
