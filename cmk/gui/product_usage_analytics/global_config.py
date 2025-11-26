#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import os
from pathlib import Path
from typing import Final, override

import cmk.ccc.version as cmk_version

from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.paths import default_config_dir, omd_root

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.utils.html import HTML
from cmk.gui.valuespec import Dictionary, DropdownChoice, ValueSpec
from cmk.gui.wato._http_proxy import HTTPProxyReference
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    ConfigVariable,
    ConfigVariableGroup,
    SerializedSettings,
)

PRODUCT_USAGE_ANALYTICS_CONFIG_ID: Final[ConfigDomainName] = "product_usage_analytics"

PRODUCT_USAGE_ANALYTICS_CONFIG_FILENAME: Final = "product_usage_analytics.mk"
PRODUCT_USAGE_ANALYTICS_CONFIG_DIR: Final = Path(default_config_dir)
PRODUCT_USAGE_ANALYTICS_CONFIG_DIR_RELATIVE: Final = PRODUCT_USAGE_ANALYTICS_CONFIG_DIR.relative_to(
    omd_root
)
PRODUCT_USAGE_ANALYTICS_CONFIG_FILE_RELATIVE: Final = (
    PRODUCT_USAGE_ANALYTICS_CONFIG_DIR_RELATIVE / PRODUCT_USAGE_ANALYTICS_CONFIG_FILENAME
)


class ConfigVariableGroupProductUsageAnalytics(ConfigVariableGroup):
    def title(self) -> str:
        return _("Product usage analytics")

    def sort_index(self) -> int:
        return 100


class ConfigDomainProductUsageAnalytics(ABCConfigDomain):
    always_activate = True

    @override
    @classmethod
    def ident(cls) -> ConfigDomainName:
        return PRODUCT_USAGE_ANALYTICS_CONFIG_ID

    @override
    def config_dir(self) -> str:
        return str(PRODUCT_USAGE_ANALYTICS_CONFIG_DIR)

    @override
    def config_file(self, site_specific: bool) -> str:
        return os.path.join(self.config_dir(), PRODUCT_USAGE_ANALYTICS_CONFIG_FILENAME)

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


class ConfigVariableProductUsageAnalytics(ConfigVariable):
    def group(self) -> type[ConfigVariableGroup]:
        return ConfigVariableGroupProductUsageAnalytics

    def domain(self) -> ABCConfigDomain:
        return ConfigDomainProductUsageAnalytics()

    def ident(self) -> str:
        return "product_usage_analytics"

    def domain_hint(self) -> HTML:
        return HTML.without_escaping(
            _(
                "Inspect product usage data: Run <tt>cmk-product-usage --dry-run</tt> as site user, or %s. "
                "This allows you to review the data locally; it does not enable the feature or transmit any information."
            )
            % HTMLWriter.render_a(
                content=_("download the full JSON report"),
                href="download_product_usage.py",
            )
        )

    def hint(self) -> HTML:
        if cmk_version.edition(omd_root) is not cmk_version.Edition.CME:
            return HTML.empty()
        return HTML.without_escaping(
            _(
                "<b>Consent Requirement: </b>"
                "You must request and receive permission from each customer before enabling the collection of product analytics data. "
                "Do not activate data collection for any site unless the customer has agreed to data transmission. "
                "For configuration options specifically for multi-tenant sites, please visit the %s."
            )
            % HTMLWriter.render_a(
                content=_("User Guide"),
                href=f"{user.get_docs_base_url()}/product_usage_analytics.html#distributed",
                target="_blank",
            )
        )

    def valuespec(self) -> ValueSpec:
        return Dictionary(
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
                            (
                                "enabled",
                                _("Allow collection and transmission of product usage data"),
                            ),
                            ("disabled", _("Do not collect product usage data")),
                            ("not_decided", _("Disabled. Reminder scheduled")),
                        ],
                        default_value="not_decided",
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
            help=_(
                "<p><b>Network Configuration: </b>"
                "To transmit analytics data, ensure your firewall permits outbound traffic to "
                "<tt>https://analytics.checkmk.com/upload</tt> on port <tt>443</tt>. "
                "If you are using a proxy, please verify that it allows connections to this destination.</p>"
                "<p><b>Per-Site Configuration: </b>"
                "You have to ensure connectivity for <b>each site individually</b>. "
                "As every site collects and transmits data independently, "
                "please verify that your firewall rules permit traffic from every site to prevent local transmission errors.</p>"
            ),
        )
