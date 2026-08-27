#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.form_specs.unstable import OptionalChoice
from cmk.gui.form_specs.unstable.validators import validate_ip_network
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSiteManagement
from cmk.rulesets.internal.form_specs import ListOfStrings, ListOfStringsLayout
from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    String,
    validators,
)


def _livestatus_via_tcp() -> Dictionary:
    return Dictionary(
        elements={
            "port": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("TCP port"),
                    custom_validate=[validators.NumberInRange(min_value=1, max_value=65535)],
                    prefill=DefaultValue(6557),
                ),
            ),
            "only_from": DictElement(
                required=True,
                parameter_form=ListOfStrings(
                    title=Title("Restrict access to IP addresses"),
                    help_text=Help(
                        "The access to Livestatus via TCP will only be allowed from the "
                        "configured source IP addresses. You can either configure specific "
                        "IP addresses or networks in the syntax <tt>10.3.3.0/24</tt>."
                    ),
                    string_spec=String(custom_validate=[validate_ip_network]),
                    layout=ListOfStringsLayout.horizontal,
                    custom_validate=[validators.LengthInRange(min_value=1)],
                    prefill=DefaultValue(["0.0.0.0", "::/0"]),
                ),
            ),
            "instances": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Maximum number of parallel server instances"),
                    help_text=Help(
                        "Limits the number of Livestatus server processes that can be active "
                        "simultaneously."
                    ),
                    prefill=DefaultValue(500),
                ),
            ),
            "per_source": DictElement(
                required=True,
                parameter_form=Integer(
                    title=Title("Maximum parallel connections per source IP address"),
                    help_text=Help(
                        "Limits the number of simultaneous Livestatus connections allowed "
                        "from a single source IP address."
                    ),
                    prefill=DefaultValue(250),
                ),
            ),
            "tls": DictElement(
                parameter_form=FixedValue(
                    value=True,
                    title=Title("Encrypt communication"),
                    label=Label("Encrypt TCP Livestatus connections"),
                    help_text=Help(
                        "Since Checkmk 1.6 it is possible to encrypt the TCP Livestatus "
                        "connections using SSL. This is enabled by default for sites that "
                        "enable Livestatus via TCP with 1.6 or newer. Sites that already "
                        "have this option enabled keep the communication unencrypted for "
                        "compatibility reasons. However, it is highly recommended to "
                        "migrate to an encrypted communication."
                    ),
                ),
            ),
        },
        migrate=_migrate_tcp_only_from,
    )


def _migrate_tcp_only_from(livestatus_tcp: object) -> dict[str, object]:
    assert isinstance(livestatus_tcp, dict)
    if "only_from" in livestatus_tcp:
        return livestatus_tcp
    livestatus_tcp["only_from"] = ["0.0.0.0"]
    return livestatus_tcp


ConfigVariableSiteLivestatusTCP = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    primary_domain=ConfigDomainOMD,
    ident="site_livestatus_tcp",
    form_spec=lambda context: OptionalChoice(
        parameter_form=_livestatus_via_tcp(),
        title=Title("Access to Livestatus via TCP"),
        help_text=Help(
            "Check_MK Livestatus usually listens only on a local Unix socket - "
            "for reasons of performance and security. This option is used "
            "to make it reachable via TCP on a port configurable with LIVESTATUS_TCP_PORT."
        ),
        label=Label("Enable Livestatus access via network (TCP)"),
        none_label=Label("Livestatus is available locally"),
    ),
)
