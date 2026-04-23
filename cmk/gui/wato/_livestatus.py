#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.gui.i18n import _
from cmk.gui.valuespec import (
    Dictionary,
    FixedValue,
    Integer,
    IPNetwork,
    ListOfStrings,
    Migrate,
    Optional,
)
from cmk.gui.watolib.config_domain_name import ConfigVariable
from cmk.gui.watolib.config_domains import ConfigDomainOMD
from cmk.gui.watolib.config_variable_groups import ConfigVariableGroupSiteManagement


def _livestatus_via_tcp() -> Dictionary:
    return Dictionary(
        elements=[
            (
                "port",
                Integer(
                    title=_("TCP port"),
                    minvalue=1,
                    maxvalue=65535,
                    default_value=6557,
                ),
            ),
            (
                "only_from",
                ListOfStrings(
                    title=_("Restrict access to IP addresses"),
                    help=_(
                        "The access to Livestatus via TCP will only be allowed from the "
                        "configured source IP addresses. You can either configure specific "
                        "IP addresses or networks in the syntax <tt>10.3.3.0/24</tt>."
                    ),
                    valuespec=IPNetwork(),
                    orientation="horizontal",
                    allow_empty=False,
                    default_value=["0.0.0.0", "::/0"],
                ),
            ),
            (
                "tls",
                FixedValue(
                    value=True,
                    title=_("Encrypt communication"),
                    totext=_("Encrypt TCP Livestatus connections"),
                    help=_(
                        "Since Checkmk 1.6 it is possible to encrypt the TCP Livestatus "
                        "connections using SSL. This is enabled by default for sites that "
                        "enable Livestatus via TCP with 1.6 or newer. Sites that already "
                        "have this option enabled keep the communication unencrypted for "
                        "compatibility reasons. However, it is highly recommended to "
                        "migrate to an encrypted communication."
                    ),
                ),
            ),
        ],
        optional_keys=["tls"],
    )


def _migrate_tcp_only_from(livestatus_tcp: dict[str, object]) -> dict[str, object]:
    if "only_from" in livestatus_tcp:
        return livestatus_tcp
    livestatus_tcp["only_from"] = ["0.0.0.0"]
    return livestatus_tcp


ConfigVariableSiteLivestatusTCP = ConfigVariable(
    group=ConfigVariableGroupSiteManagement,
    primary_domain=ConfigDomainOMD,
    ident="site_livestatus_tcp",
    valuespec=lambda context: Optional(
        valuespec=Migrate(
            _livestatus_via_tcp(),
            migrate=_migrate_tcp_only_from,
        ),
        title=_("Access to Livestatus via TCP"),
        help=_(
            "Check_MK Livestatus usually listens only on a local Unix socket - "
            "for reasons of performance and security. This option is used "
            "to make it reachable via TCP on a port configurable with LIVESTATUS_TCP_PORT."
        ),
        label=_("Enable Livestatus access via network (TCP)"),
        none_label=_("Livestatus is available locally"),
    ),
)
