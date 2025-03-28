#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ipaddress

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    CascadingDropdown,
    Dictionary,
    HTTPUrl,
    IPAddress,
    NetworkPort,
    Optional,
    Transform,
)
from cmk.gui.watolib.config_domain_name import (
    ConfigVariable,
    ConfigVariableRegistry,
)
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSupport


def register(config_variable_registry: ConfigVariableRegistry) -> None:
    config_variable_registry.register(ConfigVariableSiteTraceSend)
    config_variable_registry.register(ConfigVariableSiteTraceReceive)


ConfigVariableSiteTraceSend = ConfigVariable(
    group=ConfigVariableGroupSupport,
    domain=ConfigDomainOMD,
    ident="site_trace_send",
    valuespec=lambda: CascadingDropdown(
        title=_("Send traces from Checkmk"),
        help=_(
            "Select where to send OpenTelemetry traces of Checkmk services to. "
            "The most basic approach is to send traces to the site's local Jaeger "
            "instance. To be able to do so, you additionally have to configure the global "
            'setting "Support > Receive traces". In case you want to do tracing in '
            "distributed setups, you need to configure that option in the central site only "
            'and set this option to "Send traces to the central sites Jaeger instance". '
            "Alternatively you can send the traces to another OpenTelemetry collector via OTLP."
        ),
        sorted=False,
        choices=[
            ("no_tracing", _("Don't send any traces")),
            ("local_site", _("Send traces to site local Jaeger instance")),
            # Will be implemented later on
            # ("central_site", _("Send traces to the central sites Jaeger instance")),
            (
                "other_collector",
                _("Send traces to another OpenTelemetry collector"),
                Dictionary(
                    elements=[
                        (
                            "url",
                            HTTPUrl(
                                title=_("OTLP endpoint"),
                            ),
                        ),
                    ],
                    optional_keys=[],
                ),
            ),
        ],
    ),
)

ConfigVariableSiteTraceReceive = ConfigVariable(
    group=ConfigVariableGroupSupport,
    domain=ConfigDomainOMD,
    ident="site_trace_receive",
    valuespec=lambda: Optional(
        title=_("Receive traces"),
        valuespec=Dictionary(
            elements=[
                (
                    "address",
                    Transform(
                        IPAddress(
                            title=_("Listen for spans on this local IP address"),
                            default_value="::1",
                        ),
                        to_valuespec=lambda v: (
                            v[1:-1] if v.startswith("[") and v.endswith("]") else v
                        ),
                        from_valuespec=_ipv6_from_vs,
                    ),
                ),
                (
                    "port",
                    NetworkPort(
                        title=_("TCP port"),
                        minvalue=1025,
                        default_value=4317,
                    ),
                ),
            ],
            optional_keys=[],
        ),
        help=_(
            "This option enables receiving OpenTelemetry traces in a Jaeger instance "
            "running in the Checkmk site. This instance is run for diagnostic "
            "purposes of Checkmk and currently not intended to be used for external "
            "use cases."
            "In addition to this option, you need to configure the global setting "
            '"Support > Send traces from Checkmk".'
        ),
        label=_("Enable receiving traces"),
        none_label=_("Receiving traces is disabled"),
        indent=False,
    ),
)


def _ipv6_from_vs(value: str) -> str:
    try:
        ipaddress.IPv6Address(value)
        return f"[{value}]"
    except ValueError:
        return value
