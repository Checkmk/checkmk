#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable
from pathlib import Path
from typing import Final, override

from cmk.gui.htmllib.generator import HTMLWriter
from cmk.gui.i18n import _, _l
from cmk.gui.type_defs import GlobalSettings
from cmk.gui.wato._http_proxy import http_proxy_reference_form_spec
from cmk.gui.watolib.config_domain_name import (
    ABCConfigDomain,
    ConfigDomainName,
    ConfigVariable,
    ConfigVariableGroup,
    SerializedSettings,
)
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Title
from cmk.utils.config_warnings import ConfigurationWarnings
from cmk.utils.paths import default_config_dir, omd_root
from cmk.web.utils.html import HTML

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

    @classmethod
    @override
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


def make_product_usage_analytics_config_variable(
    hint: Callable[[], HTML] = HTML.empty,
) -> ConfigVariable:
    return ConfigVariable(
        group=ConfigVariableGroupProductUsageAnalytics,
        primary_domain=ConfigDomainProductUsageAnalytics,
        ident="product_usage_analytics",
        domain_hint=HTML.without_escaping(
            _(
                "Inspect product usage data: Run <tt>cmk-product-usage --dry-run</tt> as site user, or %(link)s. "
                "This allows you to review the data locally; it does not enable the feature or transmit any information."
            )
            % {
                "link": HTMLWriter.render_a(
                    content=_("download the full JSON report"),
                    href="download_product_usage.py",
                )
            }
        ),
        hint=hint,
        form_spec=lambda context: fs.Dictionary(
            title=Title("Product usage analytics"),
            elements={
                "enabled": fs.DictElement(
                    required=True,
                    parameter_form=fs.SingleChoice(
                        title=Title("Enable product usage analytics"),
                        help_text=Help(
                            "Consent to product usage analytics data collection. "
                            "By default, this is disabled, the user will be asked for consent via pop-up. "
                            "Run <tt>cmk-product-usage --dry-run</tt> in the command line to see a preview of the data."
                        ),
                        elements=[
                            fs.SingleChoiceElement(
                                name="enabled",
                                title=Title(
                                    "Allow collection and transmission of product usage data"
                                ),
                            ),
                            fs.SingleChoiceElement(
                                name="disabled",
                                title=Title("Do not collect product usage data"),
                            ),
                            fs.SingleChoiceElement(
                                name="not_decided",
                                title=Title("Disabled. Reminder scheduled"),
                            ),
                        ],
                        prefill=fs.DefaultValue("enabled"),
                    ),
                ),
                "proxy_setting": fs.DictElement(
                    required=True,
                    parameter_form=http_proxy_reference_form_spec(),
                ),
            },
            help_text=Help(
                "<p><b>Network configuration: </b>"
                "To transmit analytics data, ensure your firewall permits outbound traffic to "
                "<tt>https://analytics.checkmk.com/upload</tt> on port <tt>443</tt>. "
                "If you are using a proxy, please verify that it allows connections to this destination.</p>"
                "<p><b>Per-site configuration: </b>"
                "You have to ensure connectivity for <b>each site individually</b>. "
                "As every site collects and transmits data independently, "
                "please verify that your firewall rules permit traffic from every site to prevent local transmission errors.</p>"
            ),
        ),
    )


ConfigVariableProductUsageAnalytics = make_product_usage_analytics_config_variable()
