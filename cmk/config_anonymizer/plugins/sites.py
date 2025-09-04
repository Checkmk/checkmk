#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import logging
from typing import Literal

from cmk.ccc.site import SiteId
from cmk.config_anonymizer.interface import AnonInterface
from cmk.config_anonymizer.step import AnonymizeStep
from cmk.gui.config import Config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.gui.watolib.config_sync import (
    _create_distributed_wato_file_for_base,
    _create_distributed_wato_file_for_dcd,
    _create_distributed_wato_file_for_omd,
)
from cmk.gui.watolib.sites import SitesConfigFile
from cmk.livestatus_client import (
    LocalSocketInfo,
    NetworkSocketDetails,
    NetworkSocketInfo,
    ProxyConfig,
    ProxyConfigParams,
    ProxyConfigTcp,
    SiteConfiguration,
    SiteConfigurations,
    TLSInfo,
    TLSParams,
    UnixSocketDetails,
    UnixSocketInfo,
)
from cmk.utils.paths import omd_root


def _anonymize_proxy_config(
    anon_interface: AnonInterface, proxy_config: ProxyConfig | None
) -> ProxyConfig | None:
    if proxy_config is None:
        return None

    anon_proxy_config_params = None
    if (proxy_config_params := proxy_config.get("params")) is not None:
        anon_proxy_config_params = ProxyConfigParams(
            channels=proxy_config_params["channels"],
            heartbeat=proxy_config_params["heartbeat"],
            channel_timeout=proxy_config_params["channel_timeout"],
            query_timeout=proxy_config_params["query_timeout"],
            connect_retry=proxy_config_params["connect_retry"],
            cache=proxy_config_params["cache"],
        )

    anon_proxy_config = ProxyConfig(
        cache=proxy_config["cache"],
        params=anon_proxy_config_params,
        tcp=ProxyConfigTcp(
            port=proxy_config["tcp"]["port"],
            only_from=[anon_interface.get_url(addr) for addr in proxy_config["tcp"]["only_from"]],
            tls=proxy_config["tcp"]["tls"],
        ),
    )

    return anon_proxy_config


def _anonymize_status_host(
    anon_interface: AnonInterface, status_host: tuple[SiteId, str] | None
) -> tuple[SiteId, str] | None:
    if status_host is None:
        return None

    site_id, host_name = status_host
    return SiteId(anon_interface.get_site(site_id)), anon_interface.get_host(host_name)


def _anonymize_user_sync(
    anon_interface: AnonInterface,
    user_sync: Literal["all"] | tuple[Literal["list"], list[str]] | None,
) -> Literal["all"] | tuple[Literal["list"], list[str]] | None:
    match user_sync:
        case None:
            return None
        case "all":
            return "all"
        case ("list", ldap_connections):
            return "list", [
                anon_interface.get_ldap_connection(ldap_connection)
                for ldap_connection in ldap_connections
            ]
        case _:
            raise ValueError(f"Invalid user_sync format: {user_sync}")


def _anonymize_tls(anon_interface: AnonInterface, tls_info: TLSInfo) -> TLSInfo:
    match tls_info:
        case ("encrypted", tls_params):
            ca_file_path = None
            if (ca_file_path := tls_params.get("ca_file_path")) is not None:
                ca_file_path = anon_interface.get_generic_mapping(ca_file_path, "ca_file")

            anon_tls_params = TLSParams(verify=tls_params["verify"], ca_file_path=ca_file_path)
            return "encrypted", anon_tls_params
        case ("plain_text", conf):
            return "plain_text", conf
        case _:
            raise ValueError(f"Invalid TLS info format: {tls_info}")


def _anonymize_socket(
    anon_interface: AnonInterface,
    socket: str | UnixSocketInfo | NetworkSocketInfo | LocalSocketInfo,
) -> str | UnixSocketInfo | NetworkSocketInfo | LocalSocketInfo:
    match socket:
        case str():
            return anon_interface.get_generic_mapping(socket, "socket")
        case ("unix", {"path": str(path)}):
            return "unix", UnixSocketDetails(path=anon_interface.get_unix_socket(path))
        case ("tcp", {"address": address, "tls": tls}):
            # Outsmart mypy
            assert isinstance(address, tuple)
            assert isinstance(tls, tuple)
            tls_info = tls[0], tls[1]
            ipv4, port = address
            return "tcp", NetworkSocketDetails(
                address=(anon_interface.get_ipv4_address(ipv4), port), tls=tls_info
            )
        case ("tcp6", {"address": address, "tls": tls}):
            # Outsmart mypy
            assert isinstance(address, tuple)
            assert isinstance(tls, tuple)
            tls_info = tls[0], tls[1]
            ipv6, port = address
            return "tcp6", NetworkSocketDetails(
                address=(anon_interface.get_ipv6_address(ipv6), port), tls=tls_info
            )
        case ("local", None):
            return "local", None
        case _:
            raise ValueError(f"Invalid socket format: {socket}")


class SitesSteps(AnonymizeStep):
    def run(
        self, anon_interface: AnonInterface, active_config: Config, logger: logging.Logger
    ) -> None:
        logger.warning("Process sites")

        if is_distributed_setup_remote_site(active_config.sites):
            logger.info("Skipping anonymization of .sites.mk for remote site")
            return
        is_remote = False  # .sites.mk only exists for central sites

        sites_config_file = SitesConfigFile()
        sites_config = sites_config_file.load_for_reading()
        anon_sites_config: SiteConfigurations = SiteConfigurations({})
        for site_id, site_config in sites_config.items():
            logger.info("Anonymizing site %s", site_id)

            anon_site_config = SiteConfiguration(
                alias=anon_interface.get_site_alias(site_config["alias"]),
                disable_wato=site_config["disable_wato"],
                disabled=site_config["disabled"],
                id=SiteId(anon_interface.get_site(site_config["id"])),
                insecure=site_config["insecure"],
                multisiteurl=f"{anon_interface.get_url(site_config['multisiteurl'])}/check_mk/",
                persist=site_config["persist"],
                replicate_ec=site_config["replicate_ec"],
                replicate_mkps=site_config["replicate_mkps"],
                replication=site_config["replication"],
                message_broker_port=site_config["message_broker_port"],
                status_host=_anonymize_status_host(anon_interface, site_config["status_host"]),
                timeout=site_config["timeout"],
                url_prefix=f"{anon_interface.get_url(site_config['url_prefix'])}/",
                user_login=site_config["user_login"],
                user_sync=_anonymize_user_sync(anon_interface, site_config["user_sync"]),
                is_trusted=site_config["is_trusted"],
                proxy=_anonymize_proxy_config(anon_interface, site_config["proxy"]),
                socket=_anonymize_socket(anon_interface, site_config["socket"]),
            )
            if (customer := site_config.get("customer")) is not None:
                anon_site_config["customer"] = anon_interface.get_customer(customer)

            if (secret := site_config.get("secret")) is not None:
                anon_site_config["secret"] = anon_interface.get_secret(secret)

            if (cache := site_config.get("cache")) is not None:
                anon_site_config["cache"] = cache

            if (tls := site_config.get("tls")) is not None:
                anon_site_config["tls"] = _anonymize_tls(anon_interface, tls)

            # TODO for the future globals omitted on purpose here.
            #  we will select important global settings in a separate step
            anon_sites_config[SiteId(anon_interface.get_site(site_id))] = anon_site_config

            _create_distributed_wato_file_for_base(
                anon_interface.relative_to_anon_dir(
                    omd_root / "etc/check_mk/conf.d/distributed_wato.mk"
                ),
                SiteId(anon_interface.get_site(site_id)),
                is_remote,
            )

            _create_distributed_wato_file_for_dcd(
                anon_interface.relative_to_anon_dir(
                    omd_root / "etc/check_mk/dcd.d/wato/distributed.mk"
                ),
                is_remote,
            )
            _create_distributed_wato_file_for_omd(
                anon_interface.relative_to_anon_dir(omd_root / "etc/omd/distributed.mk"), is_remote
            )

        sites_config_file._config_file_path = anon_interface.relative_to_anon_dir(
            sites_config_file._config_file_path
        )
        sites_config_file.save(anon_sites_config, pprint_value=True)


anonymize_step_sites = SitesSteps()
