#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
# ruff: noqa: W291

from pathlib import Path

from cmk.gui.exceptions import MKUserError

_DEFAULT_XINETD_CONF = """service livestatus
{{
	type		= UNLISTED
	socket_type	= stream
	protocol	= tcp
	wait		= no

        # limit to 100 connections per second. Disable 3 secs if above.
	cps             = 100 3

        # set the number of maximum allowed parallel instances of unixcat.
        # Please make sure that this values is at least as high as 
        # the number of threads defined with num_client_threads in
        # etc/mk-livestatus/nagios.cfg
        instances       = 500

        # limit the maximum number of simultaneous connections from
        # one source IP address
        per_source      = 250 

        # Disable TCP delay, makes connection more responsive
	flags           = NODELAY
# configure the IP address(es) of your Nagios server here:
	only_from       = {livestatus_tcp_only_from}

# ----------------------------------------------------------
# These parameters are handled and affected by OMD
# Do not change anything beyond this point.

# Disabling is done via omd config set LIVESTATUS_TCP [on/off].
# Do not change this:
	disable		= no

# TCP port number. Can be configure via LIVESTATUS_TCP_PORT
	port		= {livestatus_tcp_port}

# Paths and users. Manual changes here will break some omd
# commands such as 'cp', 'mv' and 'update'. Do not toutch!
	user		= {omd_site}
	server		= {omd_root}/bin/unixcat
	server_args     = {omd_root}/tmp/run/live-tcp
# ----------------------------------------------------------
}}
"""


def _load_omd_config(site_root: Path) -> dict[str, object]:
    omd_config_file = site_root / "etc/omd/site.conf"
    if not omd_config_file.exists():
        return {}

    settings = dict[str, object]()
    try:
        with omd_config_file.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()

                if line == "" or line.startswith("#"):
                    continue

                var, value = line.split("=", 1)

                if not var.startswith("CONFIG_"):
                    continue

                key = var[7:].strip()
                val = value.strip().strip("'")

                settings[key] = val
    except Exception as e:
        raise MKUserError(
            None, ("Cannot read omd configuration file %s: %s") % (omd_config_file, e)
        )

    return settings


def _read_xinetd_config(site_root: Path) -> str | None:
    xinetd_config_file = site_root / "etc/xinetd.d/mk-livestatus"
    if not xinetd_config_file.exists():
        return None
    return xinetd_config_file.read_text(encoding="utf-8")


def xinetd_has_local_modifications(site_root: Path, site_id: str) -> bool:
    omd_config = _load_omd_config(site_root)
    deprecated_xinetd_config = _read_xinetd_config(site_root)
    if deprecated_xinetd_config is None:
        # Livestatus xinetd config does not exists.
        # This means that Livestatus TCP is not in use and we
        # can safely skip the update actions.
        return False
    xinetd_default_config = _DEFAULT_XINETD_CONF.format(
        omd_root=site_root,
        omd_site=site_id,
        livestatus_tcp_port=omd_config.get("LIVESTATUS_TCP_PORT", 6558),
        livestatus_tcp_only_from=omd_config.get("LIVESTATUS_TCP_ONLY_FROM", "0.0.0.0 ::/0"),
    )
    return deprecated_xinetd_config != xinetd_default_config
