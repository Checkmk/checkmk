#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
import io
import socket
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Literal

import cmk.utils.paths
from cmk.base import config
from cmk.base.community_app import make_app
from cmk.base.configlib.loaded_config import CustomCheck
from cmk.base.configlib.servicename import make_final_service_name_config
from cmk.base.core.nagios._create_config import create_nagios_servicedefs, NagiosConfig
from cmk.ccc.hostaddress import HostAddress, HostName
from cmk.ruleset_matcher.matcher import RuleSpec
from cmk.utils import ip_lookup
from tests.testlib.common.empty_config import EMPTY_CONFIG, EMPTY_NAGIOS_CORE_CONFIG


def _nagios_ping_service(*, family: Literal[4, 6], ip: str, description: str) -> str:
    ipv6_flag = "-6 " if family == 6 else ""
    return (
        "define service {\n"
        f"  check_command                 check-mk-ping!{ipv6_flag}"
        f"-w 200.00,80.00% -c 500.00,100.00% {ip}\n"
        "  check_interval                1.0\n"
        "  host_name                     my_host\n"
        f"  service_description           {description}\n"
        "  use                           check_mk_pingonly\n"
        "}"
    )


def test_fallback_ping_service_for_single_stack_host() -> None:
    service_config = _generated_ping_service_config(
        host_attrs={
            "_ADDRESS_4": "127.0.0.1",
            "address": "127.0.0.1",
            "_ADDRESS_FAMILY": "4",
        },
        ip_stack_config=ip_lookup.IPStackConfig.IPv4,
        host_ip_family=socket.AddressFamily.AF_INET,
    )

    assert (
        service_config
        == _nagios_ping_service(family=4, ip="127.0.0.1", description="PING") + "\n\n"
    )


def test_secondary_ping_service_is_ipv6_when_the_primary_is_ipv4() -> None:
    service_config = _generated_ping_service_config(
        host_attrs={
            "_ADDRESS_4": "127.0.0.1",
            "_ADDRESS_6": "::1",
            "address": "127.0.0.1",
            "_ADDRESS_FAMILY": "4",
        },
        ip_stack_config=ip_lookup.IPStackConfig.DUAL_STACK,
        host_ip_family=socket.AddressFamily.AF_INET,
    )

    assert _nagios_ping_service(family=4, ip="127.0.0.1", description="PING") in service_config
    assert _nagios_ping_service(family=6, ip="::1", description="PING IPv6") in service_config


def test_secondary_ping_service_is_ipv4_when_the_primary_is_ipv6() -> None:
    service_config = _generated_ping_service_config(
        host_attrs={
            "_ADDRESS_4": "127.0.0.1",
            "_ADDRESS_6": "::1",
            "address": "::1",
            "_ADDRESS_FAMILY": "6",
        },
        ip_stack_config=ip_lookup.IPStackConfig.DUAL_STACK,
        host_ip_family=socket.AddressFamily.AF_INET6,
    )

    assert _nagios_ping_service(family=6, ip="::1", description="PING") in service_config
    assert _nagios_ping_service(family=4, ip="127.0.0.1", description="PING IPv4") in service_config


def test_disabled_services_suppresses_the_secondary_ping() -> None:
    service_config = _generated_ping_service_config(
        host_attrs={
            "_ADDRESS_4": "127.0.0.1",
            "_ADDRESS_6": "::1",
            "address": "127.0.0.1",
            "_ADDRESS_FAMILY": "4",
        },
        ip_stack_config=ip_lookup.IPStackConfig.DUAL_STACK,
        host_ip_family=socket.AddressFamily.AF_INET,
        ignored_services=[
            {
                "id": "disable-ping-ipv6",
                "value": True,
                "condition": {"service_description": [{"$regex": "PING IPv6"}]},
            }
        ],
    )

    assert (
        service_config
        == _nagios_ping_service(family=4, ip="127.0.0.1", description="PING") + "\n\n"
    )


def test_disabled_services_leaves_no_ping_service_when_the_host_has_other_services() -> None:
    service_config = _generated_ping_service_config(
        host_attrs={
            "_ADDRESS_4": "127.0.0.1",
            "_ADDRESS_6": "::1",
            "address": "127.0.0.1",
            "_ADDRESS_FAMILY": "4",
        },
        ip_stack_config=ip_lookup.IPStackConfig.DUAL_STACK,
        host_ip_family=socket.AddressFamily.AF_INET,
        ignored_services=[
            {
                "id": "disable-ping-ipv6",
                "value": True,
                "condition": {"service_description": [{"$regex": "PING IPv6"}]},
            }
        ],
        custom_checks=[
            {
                "id": "my-custom-check",
                "value": {"service_description": "My custom check", "command_line": "echo hi"},
                "condition": {},
            }
        ],
    )

    assert "check-mk-ping" not in service_config


def test_no_fallback_ping_service_for_host_with_other_services() -> None:
    service_config = _generated_ping_service_config(
        host_attrs={
            "_ADDRESS_4": "127.0.0.1",
            "_ADDRESS_6": "::1",
            "address": "127.0.0.1",
            "_ADDRESS_FAMILY": "4",
        },
        ip_stack_config=ip_lookup.IPStackConfig.DUAL_STACK,
        host_ip_family=socket.AddressFamily.AF_INET,
        custom_checks=[
            {
                "id": "my-custom-check",
                "value": {"service_description": "My custom check", "command_line": "echo hi"},
                "condition": {},
            }
        ],
    )

    assert service_config == (
        "\n"
        "\n"
        "# Custom checks\n"
        "define service {\n"
        "  active_checks_enabled         1\n"
        "  check_command                 check-mk-custom!echo hi\n"
        "  check_interval                1.0\n"
        "  host_name                     my_host\n"
        "  service_description           My custom check\n"
        "  use                           check_mk_perf,check_mk_default\n"
        "}\n"
        "\n"
        "define service {\n"
        "  check_command                 check-mk-ping!-6 -w 200.00,80.00% -c 500.00,100.00% ::1\n"
        "  check_interval                1.0\n"
        "  host_name                     my_host\n"
        "  service_description           PING IPv6\n"
        "  use                           check_mk_pingonly\n"
        "}\n"
        "\n"
    )


def test_secondary_ping_service_replaced_by_preconfigured_service() -> None:
    service_config = _generated_ping_service_config(
        host_attrs={
            "_ADDRESS_4": "127.0.0.1",
            "_ADDRESS_6": "::1",
            "address": "127.0.0.1",
            "_ADDRESS_FAMILY": "4",
        },
        ip_stack_config=ip_lookup.IPStackConfig.DUAL_STACK,
        host_ip_family=socket.AddressFamily.AF_INET,
        custom_checks=[
            {
                "id": "user-defined-ping-ipv6",
                "value": {"service_description": "PING IPv6", "command_line": "echo hi"},
                "condition": {},
            }
        ],
    )

    assert service_config == (
        "\n"
        "\n"
        "# Custom checks\n"
        "define service {\n"
        "  active_checks_enabled         1\n"
        "  check_command                 check-mk-custom!echo hi\n"
        "  check_interval                1.0\n"
        "  host_name                     my_host\n"
        "  service_description           PING IPv6\n"
        "  use                           check_mk_perf,check_mk_default\n"
        "}\n"
        "\n"
    )


def _generated_ping_service_config(
    *,
    host_attrs: dict[str, object],
    ip_stack_config: ip_lookup.IPStackConfig,
    host_ip_family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6],
    ignored_services: Sequence[RuleSpec[object]] = (),
    custom_checks: Sequence[RuleSpec[CustomCheck]] = (),
) -> str:
    loaded_config = dataclasses.replace(
        EMPTY_CONFIG,
        all_hosts=["my_host"],
        ignored_services=ignored_services,
        custom_checks=custom_checks,
    )
    hostname = HostName("my_host")
    hosts_config = config.make_hosts_config(loaded_config)
    config_cache = config.ConfigCache(
        loaded_config,
        make_app().edition,
        hosts_config,
        config.make_host_tags(loaded_config, config.make_hosts_config(loaded_config)),
        autochecks_dir=cmk.utils.paths.autochecks_dir,
        discovered_host_labels_dir=cmk.utils.paths.discovered_host_labels_dir,
        builtin_host_labels_file=Path("/dev/null"),
    )

    final_service_name_config = make_final_service_name_config(
        config_cache._loaded_config, config_cache.ruleset_matcher
    )
    outfile = io.StringIO()
    create_nagios_servicedefs(
        cfg=NagiosConfig(outfile, [hostname], timeperiods={}),
        hosts_config=hosts_config,
        config_cache=config_cache,
        core_objects_config=_make_core_objects_config(config_cache),
        nagios_core_config=EMPTY_NAGIOS_CORE_CONFIG,
        final_service_name_config=final_service_name_config,
        passive_service_name_config=config_cache.make_passive_service_name_config(
            final_service_name_config
        ),
        enforced_services_table=lambda hn: {},
        plugins={},
        hostname=hostname,
        ip_stack_config=ip_stack_config,
        host_ip_family=host_ip_family,
        host_attrs=host_attrs,
        stored_passwords={},
        license_counter=Counter("services"),
        ip_address_of=ip_address_of_return_local,
        service_depends_on=lambda *a: (),
        for_relay=False,
    )
    return outfile.getvalue()


def _make_core_objects_config(config_cache: config.ConfigCache) -> config.CoreObjectsConfig:
    return config.CoreObjectsConfig(
        config_cache._loaded_config,
        config_cache.ruleset_matcher,
        config_cache.label_manager,
    )


def ip_address_of_return_local(
    host_name: HostName,
    family: Literal[socket.AddressFamily.AF_INET, socket.AddressFamily.AF_INET6] | None = None,
) -> HostAddress:
    return HostAddress("127.0.0.1")
