#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from pathlib import Path
from typing import Final, override

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import (
    Dictionary,
    DropdownChoice,
)
from cmk.gui.wato._http_proxy import HTTPProxyReference
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    ConfigVariable,
    ConfigVariableGroup,
    SerializedSettings,
)
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.paths import default_config_dir, omd_root

PRODUCT_TELEMETRY_CONFIG_ID: Final[ConfigDomainName] = "telemetry"

PRODUCT_TELEMETRY_CONFIG_FILENAME: Final = "telemetry.mk"
PRODUCT_TELEMETRY_CONFIG_DIR: Final = default_config_dir
PRODUCT_TELEMETRY_CONFIG_DIR_RELATIVE: Final = PRODUCT_TELEMETRY_CONFIG_DIR.relative_to(omd_root)
PRODUCT_TELEMETRY_CONFIG_FILE_RELATIVE: Final = (
    PRODUCT_TELEMETRY_CONFIG_DIR_RELATIVE / PRODUCT_TELEMETRY_CONFIG_FILENAME
)

ConfigVariableGroupProductTelemetry = ConfigVariableGroup(
    title=_l("Product telemetry"),
    sort_index=100,
)


class ConfigDomainProductTelemetry(ABCConfigDomain):
    always_activate = True

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return PRODUCT_TELEMETRY_CONFIG_ID

    @override
    def config_dir(self) -> Path:
        return PRODUCT_TELEMETRY_CONFIG_DIR

    @override
    def config_file(self, site_specific: bool) -> Path:
        return self.config_dir() / PRODUCT_TELEMETRY_CONFIG_FILENAME

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def default_globals(self) -> GlobalSettings:
        return {
            "product_telemetry": {
                "enable_telemetry": "not_decided",
                "proxy_setting": ("environment", "environment"),
            }
        }


ConfigVariableProductTelemetry = ConfigVariable(
    group=ConfigVariableGroupProductTelemetry,
    primary_domain=ConfigDomainProductTelemetry,
    ident="product_telemetry",
    hint=lambda: HTML.without_escaping(
        _(
            "Preview telemetry data: Run <tt>cmk-telemetry --dry-run</tt> on the command line as site user, or download your data by %s."
        )
        % HTMLWriter.render_a(
            content=_("clicking here"),
            href="download_telemetry.py",
        )
    ),
    valuespec=lambda context: Dictionary(
        title=_("Product telemetry"),
        elements=[
            (
                "enable_telemetry",
                DropdownChoice(
                    title=_("Enable product telemetry"),
                    help=_(
                        "Consent to product telemetry data collection. "
                        "By default, this is disabled, the user will be asked for consent via pop-up. "
                        "Run  <tt>cmk-telemetry --dry-run</tt> in the command line to see a preview of the data."
                    ),
                    choices=[
                        ("enabled", _("Allow collection and transmission of telemetry data")),
                        ("disabled", _("Do not collect and transmit telemetry data")),
                        ("not_decided", _("Disabled. Reminder scheduled")),
                    ],
                    html_attrs={"width": "fit-content"},
                ),
            ),
            (
                "proxy_setting",
                HTTPProxyReference(),
            ),
        ],
        optional_keys=[],
        default_keys=["enable_telemetry", "proxy_setting"],
    ),
)
