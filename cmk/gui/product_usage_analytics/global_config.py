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

PRODUCT_USAGE_ANALYTICS_CONFIG_ID: Final[ConfigDomainName] = "product_usage_analytics"

PRODUCT_USAGE_ANALYTICS_CONFIG_FILENAME: Final = "product_usage_analytics.mk"
PRODUCT_USAGE_ANALYTICS_CONFIG_DIR: Final = default_config_dir
PRODUCT_USAGE_ANALYTICS_CONFIG_DIR_RELATIVE: Final = PRODUCT_USAGE_ANALYTICS_CONFIG_DIR.relative_to(
    omd_root
)
PRODUCT_USAGE_ANALYTICS_CONFIG_FILE_RELATIVE: Final = (
    PRODUCT_USAGE_ANALYTICS_CONFIG_DIR_RELATIVE / PRODUCT_USAGE_ANALYTICS_CONFIG_FILENAME
)

ConfigVariableGroupProductUsageAnalytics = ConfigVariableGroup(
    title=_l("Product usage analytics"),
    sort_index=100,
)


class ConfigDomainProductUsageAnalytics(ABCConfigDomain):
    always_activate = True

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return PRODUCT_USAGE_ANALYTICS_CONFIG_ID

    @override
    def config_dir(self) -> Path:
        return PRODUCT_USAGE_ANALYTICS_CONFIG_DIR

    @override
    def config_file(self, site_specific: bool) -> Path:
        return self.config_dir() / PRODUCT_USAGE_ANALYTICS_CONFIG_FILENAME

    @override
    def create_artifacts(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def activate(self, settings: SerializedSettings | None = None) -> ConfigurationWarnings:
        return []

    @override
    def default_globals(self) -> GlobalSettings:
        return {
            "product_usage_analytics": {
                "enabled": "not_decided",
                "proxy_setting": ("environment", "environment"),
            }
        }


ConfigVariableProductUsageAnalytics = ConfigVariable(
    group=ConfigVariableGroupProductUsageAnalytics,
    primary_domain=ConfigDomainProductUsageAnalytics,
    ident="product_usage_analytics",
    hint=lambda: HTML.without_escaping(
        _(
            "Preview product usage data: Run <tt>cmk-product-usage --dry-run</tt> on the command line as site user, or download your data by %s."
        )
        % HTMLWriter.render_a(
            content=_("clicking here"),
            href="download_product_usage.py",
        )
    ),
    valuespec=lambda context: Dictionary(
        title=_("Product usage analytics"),
        elements=[
            (
                "enabled",
                DropdownChoice(
                    title=_("Enable product usage analytics"),
                    help=_(
                        "Consent to product usage analytics data collection. "
                        "By default, this is disabled, the user will be asked for consent via pop-up. "
                        "Run  <tt>cmk-product-usage --dry-run</tt> in the command line to see a preview of the data."
                    ),
                    choices=[
                        ("enabled", _("Allow collection and transmission of product usage data")),
                        ("disabled", _("Do not collect and transmit product usage data")),
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
        default_keys=["enabled", "proxy_setting"],
    ),
)
