#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections import defaultdict
from itertools import chain
from typing import Dict, Generator, Sequence, Set, Tuple

from tests.testlib.base import Scenario

from cmk.utils.type_defs import ParsedSectionName

import cmk.base.api.agent_based.register as agent_based_register
from cmk.base.api.agent_based.type_defs import SectionPlugin, SNMPSectionPlugin
from cmk.base.plugin_contexts import current_host


def _section_permutations(
    parsed_section_names: Sequence[ParsedSectionName],
) -> Generator[Tuple[SectionPlugin, ...], None, None]:

    if not parsed_section_names:
        yield ()
        return

    if len(parsed_section_names) >= 1:
        for section_name in agent_based_register.get_section_producers(parsed_section_names[0]):
            for perm in _section_permutations(parsed_section_names[1:]):
                yield (agent_based_register.get_section_plugin(section_name),) + perm


def _get_empty_parsed_result(section: SectionPlugin) -> object:
    return (
        section.parse_function(len(section.trees) * [[]])  # type: ignore[arg-type]
        if isinstance(section, SNMPSectionPlugin)
        else None
    )


def test_check_plugins_do_not_discover_upon_empty_snmp_input(monkeypatch, fix_register):
    """
    In Checkmk < 1.6 the parse function has not been called for empty table data,
    unless "handle_empty_info" has been set.

    From version 2.0 on, the parse function will be called allways.
    In case no further processing is desired, the parse functions should return `None`.

    (Returning something falsey usually means nothing will be discovered!)

    Since this was the behaviour for *almost* every plugin we maintain this test
    with a list of known exceptions, to ensure the old behaviour is not changed.

    However: There is nothing wrong with not returning None, in principle.
    If you whish to do that (see one of the listed exeptions for examples),
    just add an exception below. If maintaining this test becvomes too tedious,
    we can probably just remove it.
    """
    Scenario().apply(monkeypatch)  # host_extra_conf needs the ruleset_matcher

    plugins_expected_to_discover_upon_empty = {
        "printer_alerts",
        "liebert_system_events",
        "apc_inrow_system_events",
    }

    plugins_discovering_upon_empty = set()
    for plugin in fix_register.check_plugins.values():
        for sections in _section_permutations(plugin.sections):
            kwargs = {str(section.name): _get_empty_parsed_result(section) for section in sections}
            if all(v is None for v in kwargs.values()):
                continue

            if len(kwargs) > 1:
                kwargs = {f"section_{k}": v for k, v in kwargs.items()}
            else:
                kwargs = {"section": v for v in kwargs.values()}

            if plugin.discovery_default_parameters is not None:
                kwargs["params"] = (
                    plugin.discovery_default_parameters
                    if (plugin.discovery_ruleset_type == "merged")
                    else [plugin.discovery_default_parameters]
                )

            with current_host("testhost"):  # host_extra_conf needs a host_name()
                if list(plugin.discovery_function(**kwargs)):
                    plugins_discovering_upon_empty.add(str(plugin.name))

    assert plugins_discovering_upon_empty == plugins_expected_to_discover_upon_empty


def test_no_plugins_with_trivial_sections(fix_register):
    """
    This is a sanity test for registered inventory and check plugins. It ensures that plugins
    have a non trivial section. Trivial sections may be created accidentally e.g. if a typo
    is introduced in the section or plugin name during the migration to the new API. If a
    trivial section without a parse_function is sufficient for your plugin you have to add it
    to the known exceptions below.
    """
    known_exceptions = {
        ParsedSectionName(s)
        for s in [
            "aix_baselevel",
            "aix_lparstat_inventory",
            "aix_packages",
            "aix_service_packs",
            "couchbase_nodes_ports",
            "docker_container_network",
            "docker_container_node_name",
            "docker_node_images",
            "k8s_assigned_pods",
            "k8s_daemon_pod_containers",
            "k8s_job_container",
            "k8s_pod_info",
            "k8s_selector",
            "k8s_service_info",
            "lnx_block_devices",
            "lnx_cpuinfo",
            "lnx_distro",
            "lnx_ip_r",
            "lnx_packages",
            "lnx_sysctl",
            "lnx_uname",
            "lnx_video",
            "mssql_clusters",
            "oracle_systemparameter",
            "prtconf",
            "solaris_addresses",
            "solaris_pkginfo",
            "solaris_prtdiag",
            "solaris_prtpicl",
            "solaris_psrinfo",
            "solaris_psrinfo_table",
            "solaris_routes",
            "solaris_uname",
            "statgrab_net",
            "win_bios",
            "win_computersystem",
            "win_cpuinfo",
            "win_disks",
            "win_exefiles",
            "win_ip_r",
            "win_networkadapter",
            "win_os",
            "win_reg_uninstall",
            "win_system",
            "win_video",
            "win_wmi_software",
            "win_wmi_updates",
        ]
    }

    # fix_register does not include trivial sections created by the trivial_section_factory
    registered_sections = {
        s.parsed_section_name
        for s in chain(fix_register.agent_sections.values(), fix_register.snmp_sections.values())
    }

    plugins_with_trivial_sections: Dict[str, Set[str]] = defaultdict(set)
    for plugin in chain(
        fix_register.check_plugins.values(), fix_register.inventory_plugins.values()
    ):
        for section in plugin.sections:
            if section not in registered_sections and section not in known_exceptions:
                plugins_with_trivial_sections[plugin.name].add(str(section))

    if plugins_with_trivial_sections:
        msg = "\n".join(
            f"{plugin}: {', '.join(sections)}"
            for plugin, sections in sorted(plugins_with_trivial_sections.items())
        )
        assert 0, f"""Found new plugins with trivial sections:
PLUGIN - TRIVIAL SECTIONS'
----------------
{msg}"""
