#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import Checkbox
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupApplicationMonitoring


def register(config_variable_registry: ConfigVariableRegistry) -> None:
    config_variable_registry.register(ConfigVariableEnableOTel)


ConfigVariableEnableOTel = ConfigVariable(
    group=ConfigVariableGroupApplicationMonitoring,
    domain=ConfigDomainOMD,
    ident="site_opentelemetry_collector",
    valuespec=lambda: Checkbox(
        title=_("Enable OpenTelemetry collector (experimental)"),
        default_value=False,
    ),
)
