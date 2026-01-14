#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


import os
from collections.abc import Mapping, Sequence
from pathlib import Path

import pytest

from cmk.agent_based.v2 import CheckPlugin
from cmk.ccc.version import Edition
from cmk.checkengine.plugins import AgentBasedPlugins
from cmk.discover_plugins import discover_all_plugins, discover_families, PluginGroup
from cmk.server_side_calls_backend import load_active_checks
from cmk.utils import man_pages
from tests.testlib.common.repo import repo_path

_IF64_MAN_PAGE = man_pages.ManPage(
    name="if64",
    path=Path("/omd/sites/heute/lib/python3/cmk/plugins/collection/checkman/if64"),
    title="Monitor Network Interfaces via Standard MIB Using 64-Bit Counters",
    agents=["snmp"],
    catalog=["hw", "network", "generic"],
    license="GPLv2",
    distribution="check_mk",
    description=(
        "This check does the same as {interfaces} but uses 64-bit counters from\nthe {IF-MIB}"
        " {.1.3.6.1.2.1.31.1.1.1}. This allows to correctly\nmonitor switch ports with a traffic"
        " of more then 2GB per check interval.\n\nAlso, this check can use {ifAlias} instead if"
        " ..."  # shortened for this test
    ),
    item=None,
    discovery=None,
    cluster=None,
)


def man_page_dirs_for_test(tmp_path: Path) -> Mapping[str, Sequence[str]]:
    return {"additional_test_folders": [str(tmp_path)], **discover_families(raise_errors=True)}


@pytest.fixture(scope="module", name="catalog")
def get_catalog() -> man_pages.ManPageCatalog:
    return man_pages.load_man_page_catalog(
        discover_families(raise_errors=True), PluginGroup.CHECKMAN.value
    )


@pytest.fixture(scope="module", name="all_pages")
def get_all_pages() -> Mapping[str, man_pages.ManPage]:
    mpm = man_pages.make_man_page_path_map(
        discover_families(raise_errors=True), PluginGroup.CHECKMAN.value
    )
    return {name: man_pages.parse_man_page(name, path) for name, path in mpm.items()}


def test_man_page_path_only_shipped() -> None:
    mpm = man_pages.make_man_page_path_map(
        discover_families(raise_errors=True), PluginGroup.CHECKMAN.value
    )
    assert mpm["if64"] == repo_path() / "cmk" / "plugins" / "collection" / "checkman" / "if64"


def test_man_page_path_both_dirs(tmp_path: Path) -> None:
    (tmp_checkman := tmp_path / "checkman").mkdir()
    f1 = tmp_checkman / "file1"
    f1.write_text("x", encoding="utf-8")

    man_page_path_map = man_pages.make_man_page_path_map(
        man_page_dirs_for_test(tmp_path), PluginGroup.CHECKMAN.value
    )
    assert man_page_path_map["file1"] == tmp_checkman / "file1"
    assert "file2" not in man_page_path_map

    (tmp_checkman / "file2").touch()

    # This tests that make_manpage_path_map is not cached.
    # Not sure if this is realy required.
    man_page_path_map = man_pages.make_man_page_path_map(
        man_page_dirs_for_test(tmp_path), PluginGroup.CHECKMAN.value
    )
    assert man_page_path_map["file2"] == tmp_checkman / "file2"


def test_all_man_pages(tmp_path: Path) -> None:
    (tmp_checkman := tmp_path / "checkman").mkdir()
    (tmp_checkman / ".asd").write_text("", encoding="utf-8")
    (tmp_checkman / "asd~").write_text("", encoding="utf-8")
    (tmp_checkman / "if").write_text("", encoding="utf-8")

    pages = man_pages.make_man_page_path_map(
        man_page_dirs_for_test(tmp_path), PluginGroup.CHECKMAN.value
    )

    assert len(pages) > 1241
    assert ".asd" not in pages
    assert "asd~" not in pages

    assert pages["if"] == tmp_checkman / "if"
    assert pages["if64"] == repo_path() / "cmk" / "plugins" / "collection" / "checkman" / "if64"


def test_load_all_man_pages(all_pages: Mapping[str, man_pages.ManPage]) -> None:
    for _name, man_page in all_pages.items():
        assert isinstance(man_page, man_pages.ManPage)


def test_print_man_page_table(capsys: pytest.CaptureFixture[str]) -> None:
    man_page_path_map = man_pages.make_man_page_path_map(
        discover_families(raise_errors=True), PluginGroup.CHECKMAN.value
    )
    man_pages.print_man_page_table(man_page_path_map)
    out, err = capsys.readouterr()
    assert err == ""

    lines = out.split("\n")

    assert len(lines) > 1241
    assert "enterasys_powersupply" in out


def man_page_catalog_titles() -> None:
    assert man_pages.CATALOG_TITLES["hw"]
    assert man_pages.CATALOG_TITLES["os"]


def test_load_man_page_catalog(catalog: man_pages.ManPageCatalog) -> None:
    assert isinstance(catalog, dict)

    for path, entries in catalog.items():
        assert isinstance(path, tuple)
        assert isinstance(entries, list)

        # TODO: Test for unknown paths?

        # Test for non fallback man pages
        assert not any("Cannot parse man page" in e.title for e in entries)


def test_no_unsorted_man_pages(catalog: man_pages.ManPageCatalog) -> None:
    unsorted_page_names = [m.name for m in catalog.get(("unsorted",), [])]

    assert not unsorted_page_names


def test_manpage_files(all_pages: Mapping[str, man_pages.ManPage]) -> None:
    assert len(all_pages) > 1000


def test_cmk_plugins_families_manpages() -> None:
    """All v2 style check plug-ins should have the manpages in their families folder."""
    man_page_path_map = man_pages.make_man_page_path_map(
        discover_families(raise_errors=True), PluginGroup.CHECKMAN.value
    )
    check_plugins = discover_all_plugins(
        PluginGroup.AGENT_BASED, {CheckPlugin: "check_plugin_"}, raise_errors=True
    )
    assert not {
        (location, plugin.name, expected, actual)
        for location, plugin in check_plugins.plugins.items()
        if (
            (expected := os.path.join(*location.module.split(".")[:3]))
            not in (actual := str(man_page_path_map.get(plugin.name, "")))
        )
    }


def test_man_page_consistency(
    agent_based_plugins: AgentBasedPlugins,
    all_pages: Mapping[str, man_pages.ManPage],
) -> None:
    """Make sure we have one man page per plugin, and no additional ones"""
    expected_man_pages = (
        {str(plugin_name) for plugin_name in agent_based_plugins.check_plugins}
        | {f"check_{plugin.name}" for plugin in load_active_checks(raise_errors=False).values()}
        | {"check-mk", "check-mk-inventory"}
    )
    assert not set(all_pages).difference(expected_man_pages)
    assert not expected_man_pages.difference(all_pages)


def test_cluster_check_functions_match_manpages_cluster_sections(
    agent_based_plugins: AgentBasedPlugins,
    all_pages: Mapping[str, man_pages.ManPage],
) -> None:
    missing_cluster_description: set[str] = set()
    unexpected_cluster_description: set[str] = set()

    for plugin in agent_based_plugins.check_plugins.values():
        man_page = all_pages[str(plugin.name)]
        has_cluster_doc = bool(man_page.cluster)
        has_cluster_func = plugin.cluster_check_function is not None
        if has_cluster_doc is not has_cluster_func:
            (
                missing_cluster_description,
                unexpected_cluster_description,
            )[has_cluster_doc].add(str(plugin.name))

    assert not missing_cluster_description
    assert not unexpected_cluster_description


def test_no_subtree_and_entries_on_same_level(catalog: man_pages.ManPageCatalog) -> None:
    for category, entries in catalog.items():
        has_entries = bool(entries)
        has_categories = bool(man_pages._manpage_catalog_subtree_names(catalog, category))
        assert has_entries != has_categories, (
            "A category must only have entries or categories, not both"
        )


def test_print_man_page_nowiki_content() -> None:
    content = man_pages.NowikiManPageRenderer(_IF64_MAN_PAGE).render_page()
    assert content.startswith("TI:")
    assert "\nSA:" in content
    assert "License:" in content


@pytest.mark.usefixtures("capsys")
def test_print_man_page() -> None:
    rendered = man_pages.ConsoleManPageRenderer(_IF64_MAN_PAGE).render_page()
    assert rendered.startswith(" if64    ")
    assert "\n License: " in rendered


def test_missing_catalog_entries_of_man_pages(all_pages: Mapping[str, man_pages.ManPage]) -> None:
    found_catalog_entries_from_man_pages = {e for page in all_pages.values() for e in page.catalog}
    missing_catalog_entries = found_catalog_entries_from_man_pages - set(man_pages.CATALOG_TITLES)
    assert not missing_catalog_entries


_ALLOWED_AGENTS = [
    # TODO remove prefixes? eg. 'agent_'
    "3par",
    "agent_cisco_prime",
    "agent_redfish",
    "agent_redfish_power",
    "agent_ucs_bladecenter",
    "aix",
    "alertmanager",
    "allnet_ip_sensoric",
    "appdynamics",
    "aws",
    "aws_status",
    "azure",
    "azure_v2",
    "azure_status",
    "cisco_meraki",
    "custom_query_metric_backend",
    "datadog",
    "ddn_s2a",
    "elasticsearch",
    "emc",
    "freebsd",
    "fritzbox",
    "gcp",
    "gcp_status",
    "gerrit",
    "graylog",
    "hp_msa",
    "hpux",
    "ibm_svc",
    "jenkins",
    "jira",
    "kubernetes",
    "linux",
    "macosx",
    "metric_backend",
    "mobileiron",
    "mqtt",
    "netapp",
    "netbsd",
    "nutanix",
    "openbsd",
    "openvms",
    "openwrt",
    "otel",
    "prometheus",
    "proxmox_ve",
    "pure_storage_fa",
    "rabbitmq",
    "ruckus",
    "salesforce",
    "siemens_plc",
    "snmp",
    "solaris",
    "splunk",
    "storeonce",
    "storeonce4x",
    "vnx_quotas",
    "vsphere",
    "windows",
    "z_os",
    "zerto",
    # TODO lower case and/or cmk_bi?
    "BI",
    # TODO do we want to specify these?
    "active",
    "special",
]


def test_man_page_agents(all_pages: Mapping[str, man_pages.ManPage]) -> None:
    man_page_uses_forbidden_agents: dict[str, set[str]] = {}
    for name, page in all_pages.items():
        if forbidden := set(page.agents) - set(_ALLOWED_AGENTS):
            man_page_uses_forbidden_agents.setdefault(name, forbidden)
    assert not man_page_uses_forbidden_agents


def test_man_page_license(all_pages: Mapping[str, man_pages.ManPage]) -> None:
    license_not_open_source = set()
    license_not_enterprise = set()
    non_free_directories = {
        edition.long for edition in Edition if edition is not Edition.COMMUNITY
    } | {"nonfree"}

    for page in all_pages.values():
        if non_free_directories.intersection(page.path.relative_to(repo_path()).parts):
            if page.license != "Checkmk Enterprise License":
                license_not_enterprise.add(page.name)

        elif page.license != "GPLv2":
            license_not_open_source.add(page.name)

    assert not license_not_open_source, (
        "The following man pages should have 'GPLv2' as license but don't"
    )
    assert not license_not_enterprise, (
        "The following man pages should have 'Checkmk Enterprise License' as license but don't"
    )
