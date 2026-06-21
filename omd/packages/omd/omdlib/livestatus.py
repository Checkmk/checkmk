#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from pathlib import Path

from omdlib.config_api import Config, Hook, ip_address_list_has_error, null_action, PortHook

LIVESTATUS_CONFIG_HEADER = """# This file is managed by OMD
# Do not change anything in this file. Use omd config instead.
"""
LIVESTATUS_CONFIG_TEMPLATE = """service livestatus
{{
        # ----------------------------------------------------------
        # Livestatus-specific connection parameters that cannot
        # currently be modified by omd config
        type = UNLISTED
        socket_type = stream
        protocol = tcp
        wait = no
        # Disable TCP delay to make connection more responsive.
        flags = NODELAY

        # ----------------------------------------------------------
        # These parameters can be controlled by omd config.
        # For details, please see `man 5 xinetd.conf`.

        # Limit the maximum number of connections per second. A cps of
        # "X Y" limits to X connections per second and disables the
        # service for Y seconds, if this threshold has been reached.
        cps             = 100 3

        # Set the number of maximum allowed parallel instances of this
        # server. Please make sure that this value is at least as high
        # as the number of threads defined with num_client_threads in
        # etc/mk-livestatus/nagios.cfg.
        instances       = {LIVESTATUS_TCP_INSTANCES}

        # Limit the maximum number of simultaneous connections from
        # each distinct source IP address.
        per_source      = {LIVESTATUS_TCP_PER_SOURCE}

        # Restrict access to the listed remote hosts. The value is a
        # space-separated list of IPv4 or IPv6 addresses. If unset,
        # any host may connect.
        only_from       = {LIVESTATUS_TCP_ONLY_FROM}

        # TCP port number this service will listen on.
        port = {LIVESTATUS_TCP_PORT}
        # ----------------------------------------------------------

        user		= {OMD_SITE}
        server		= {OMD_ROOT}/bin/unixcat
        server_args     = {OMD_ROOT}/tmp/run/live-tcp
}}
"""


def write_livestatus_xinetd_conf(site_name: str, site_home: Path, config: Config) -> None:
    match config["LIVESTATUS_TCP"]:
        case "off":
            content = LIVESTATUS_CONFIG_HEADER
        case "on":
            content = LIVESTATUS_CONFIG_HEADER + LIVESTATUS_CONFIG_TEMPLATE.format(
                LIVESTATUS_TCP_ONLY_FROM=config["LIVESTATUS_TCP_ONLY_FROM"],
                LIVESTATUS_TCP_PORT=config["LIVESTATUS_TCP_PORT"],
                LIVESTATUS_TCP_INSTANCES=config["LIVESTATUS_TCP_INSTANCES"],
                LIVESTATUS_TCP_PER_SOURCE=config["LIVESTATUS_TCP_PER_SOURCE"],
                OMD_SITE=site_name,
                OMD_ROOT=site_home,
            )
        case _:
            raise NotImplementedError(
                f"Invalid value for LIVESTATUS_TCP: {config['LIVESTATUS_TCP']}"
            )

    conf_path = Path(site_home, "etc/xinetd.d/livestatusv1")
    conf_path.parent.mkdir(parents=True, exist_ok=True)
    with conf_path.open("w", encoding="utf-8") as livestatus_xinetd_conf:
        livestatus_xinetd_conf.write(content)


LIVESTATUS_TCP = Hook(
    name="LIVESTATUS_TCP",
    choices=[("on", "enable"), ("off", "disable")],
    default=lambda _edition: "off",
    depends=lambda c: c.get("CORE") != "none",
    activation=write_livestatus_xinetd_conf,
)

LIVESTATUS_TCP_INSTANCES = Hook(
    name="LIVESTATUS_TCP_INSTANCES",
    choices=re.compile(r"[0-9]+$"),
    default=lambda _edition: "500",
    depends=lambda c: c.get("CORE") != "none" and c.get("LIVESTATUS_TCP") == "on",
    activation=write_livestatus_xinetd_conf,
)

LIVESTATUS_TCP_ONLY_FROM = Hook(
    name="LIVESTATUS_TCP_ONLY_FROM",
    choices=ip_address_list_has_error,
    default=lambda _edition: "0.0.0.0 ::/0",
    depends=lambda c: c.get("CORE") != "none" and c.get("LIVESTATUS_TCP") == "on",
    activation=write_livestatus_xinetd_conf,
)

LIVESTATUS_TCP_PER_SOURCE = Hook(
    name="LIVESTATUS_TCP_PER_SOURCE",
    choices=re.compile(r"[0-9]+$"),
    default=lambda _edition: "250",
    depends=lambda c: c.get("CORE") != "none" and c.get("LIVESTATUS_TCP") == "on",
    activation=write_livestatus_xinetd_conf,
)

LIVESTATUS_TCP_PORT = PortHook(
    name="LIVESTATUS_TCP_PORT",
    display_name="Livestatus port",
    default_port=6557,
    activation=write_livestatus_xinetd_conf,
    choices=re.compile(r"[0-9]{1,5}$"),
    depends=lambda c: c.get("CORE") != "none" and c.get("LIVESTATUS_TCP") == "on",
)

# Do not patch the xinetd config directly here, because that would lead to
# later conflicts during omd cp/mv. The xinetd config points to a link
# live-tcp instead which always points to the correct socket. This is
# done by "omd", because the hook can not change things in tmp since the
# tmpfs may not be available during hook execution.
LIVESTATUS_TCP_TLS = Hook(
    name="LIVESTATUS_TCP_TLS",
    choices=[("on", "encrypt"), ("off", "clear text")],
    default=lambda _edition: "on",
    depends=lambda c: c.get("CORE") != "none" and c.get("LIVESTATUS_TCP") == "on",
    activation=null_action,
)
