#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.ccc import version

from cmk.utils import paths

from cmk.gui.rest_api_types.site_connection import SiteConfig


def default_config_example() -> SiteConfig:
    r: SiteConfig = {
        "basic_settings": {
            "alias": "Die remote site 1",
            "site_id": "site_id_1",
        },
        "status_connection": {
            "connection": {
                "socket_type": "tcp",
                "host": "192.168.1.1",
                "port": 1253,
                "encrypted": True,
                "verify": False,
            },
            "proxy": {
                "use_livestatus_daemon": "with_proxy",
                "global_settings": False,
                "params": {
                    "channels": 15,
                    "heartbeat": {"interval": 12, "timeout": 3.0},
                    "channel_timeout": 3.5,
                    "query_timeout": 120.2,
                    "connect_retry": 4.6,
                    "cache": True,
                },
                "tcp": {"port": 6560, "only_from": ["192.168.1.1"], "tls": False},
            },
            "connect_timeout": 2,
            "persistent_connection": False,
            "url_prefix": "/heute_remote_1/",
            "status_host": {
                "status_host_set": "disabled",
            },
            "disable_in_status_gui": False,
        },
        "configuration_connection": {
            "enable_replication": True,
            "url_of_remote_site": "http://localhost/heute_remote_site_id_1/check_mk/",
            "disable_remote_configuration": True,
            "ignore_tls_errors": False,
            "direct_login_to_web_gui_allowed": True,
            "user_sync": {
                "sync_with_ldap_connections": "all",
            },
            "replicate_event_console": True,
            "replicate_extensions": True,
            "message_broker_port": 5672,
        },
    }

    if version.edition(paths.omd_root) is version.Edition.CME:
        r["basic_settings"] = {
            "alias": "Die remote site 1",
            "site_id": "site_id_1",
            "customer": "provider",
        }

    return r


def no_replication_config_example() -> SiteConfig:
    r: SiteConfig = default_config_example()

    r["configuration_connection"] = {"enable_replication": False}

    return r
