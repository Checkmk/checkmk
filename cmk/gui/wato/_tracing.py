#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ipaddress

from cmk.gui.form_specs.generators.cascading_choice_utils import (
    CascadingDataConversion,
    enable_deprecated_cascading_elements,
)
from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
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
from cmk.rulesets.v1 import form_specs as fs
from cmk.rulesets.v1 import Help, Label, Title


def register(config_variable_registry: ConfigVariableRegistry) -> None:
    config_variable_registry.register(ConfigVariableSiteTraceSend)
    config_variable_registry.register(ConfigVariableSiteTraceReceive)


ConfigVariableSiteTraceSend = ConfigVariable(
    group=ConfigVariableGroupSupport,
    primary_domain=ConfigDomainOMD,
    ident="site_trace_send",
    form_spec=lambda context: enable_deprecated_cascading_elements(
        fs.CascadingSingleChoice(
            title=Title("Send traces from Checkmk"),
            help_text=Help(
                "Select where to send OpenTelemetry traces of Checkmk services to. "
                "The most basic approach is to send traces to the site's local Jaeger "
                "instance. To be able to do so, you additionally have to configure the global "
                'setting "Support > Receive traces". In case you want to do tracing in '
                "distributed setups, you need to configure that option in the central site only "
                'and set this option to "Send traces to the central site\'s Jaeger instance". '
                "Alternatively you can send the traces to another OpenTelemetry Collector via "
                "OTLP."
            ),
            prefill=fs.DefaultValue("no_tracing"),
            elements=[
                fs.CascadingSingleChoiceElement(
                    name="no_tracing",
                    title=Title("Don't send any traces"),
                    parameter_form=fs.FixedValue(value=True, label=Label("")),
                ),
                fs.CascadingSingleChoiceElement(
                    name="local_site",
                    title=Title("Send traces to site local Jaeger instance"),
                    parameter_form=fs.FixedValue(value=True, label=Label("")),
                ),
                fs.CascadingSingleChoiceElement(
                    name="other_collector",
                    title=Title("Send traces to another OpenTelemetry Collector"),
                    parameter_form=fs.Dictionary(
                        elements={
                            "url": fs.DictElement(
                                required=True,
                                parameter_form=fs.String(
                                    title=Title("OTLP endpoint"),
                                    prefill=fs.InputHint("https://collector.example.com:4317"),
                                    custom_validate=(
                                        fs.validators.LengthInRange(min_value=1),
                                        fs.validators.Url(
                                            protocols=[
                                                fs.validators.UrlProtocol.HTTP,
                                                fs.validators.UrlProtocol.HTTPS,
                                            ]
                                        ),
                                    ),
                                ),
                            ),
                        },
                    ),
                ),
            ],
        ),
        [
            CascadingDataConversion(
                name_in_form_spec="no_tracing", value_on_disk="no_tracing", has_form_spec=False
            ),
            CascadingDataConversion(
                name_in_form_spec="local_site", value_on_disk="local_site", has_form_spec=False
            ),
        ],
    ),
)

ConfigVariableSiteTraceReceive = ConfigVariable(
    group=ConfigVariableGroupSupport,
    primary_domain=ConfigDomainOMD,
    ident="site_trace_receive",
    valuespec=lambda context: Optional(
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
            "use cases. "
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
