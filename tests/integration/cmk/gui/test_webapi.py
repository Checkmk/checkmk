#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import base64
import copy
import json
import os
import subprocess
import sys
import time
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import pytest
from PIL import Image  # type: ignore[import]

from tests.testlib import APIError, wait_until
from tests.testlib.site import Site
from tests.testlib.utils import get_standard_linux_agent_output

import cmk.utils.version as cmk_version


@pytest.fixture(name="local_test_hosts")
def fixture_local_test_hosts(web, site: Site):  # pylint: disable=redefined-outer-name
    site.makedirs("var/check_mk/agent_output/")

    web.add_hosts(
        [
            (
                "test-host",
                "",
                {
                    "ipaddress": "127.0.0.1",
                },
            ),
            (
                "test-host2",
                "xy/zzz",
                {
                    "ipaddress": "127.0.0.1",
                },
            ),
        ]
    )

    site.write_text_file(
        "etc/check_mk/conf.d/local-test-hosts.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['test-host', 'test-host2']))\n",
    )

    for hostname in ["test-host", "test-host2"]:
        site.write_text_file(
            "var/check_mk/agent_output/%s" % hostname, get_standard_linux_agent_output()
        )

    yield

    for hostname in ["test-host", "test-host2"]:
        web.delete_host(hostname)
        site.delete_file("var/check_mk/agent_output/%s" % hostname)
    site.delete_file("etc/check_mk/conf.d/local-test-hosts.mk")


def test_global_settings(site, web):  # pylint: disable=redefined-outer-name
    r = web.get("wato.py?mode=globalvars")
    assert "Global settings" in r.text


def test_add_host(web):  # pylint: disable=redefined-outer-name
    try:
        # Also tests get_host
        web.add_host(
            "test-host",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )
    finally:
        web.delete_host("test-host")


def test_add_host_folder_create(web):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-host",
            attributes={
                "ipaddress": "127.0.0.1",
            },
            create_folders=True,
            folder="asd/eee",
        )
    finally:
        web.delete_host("test-host")


def test_add_host_no_folder_create(web):  # pylint: disable=redefined-outer-name
    with pytest.raises(APIError) as e:
        web.add_host(
            "test-host",
            attributes={
                "ipaddress": "127.0.0.1",
            },
            create_folders=False,
            folder="eins/zwei",
            expect_error=True,
        )

    exc_msg = "%s" % e
    assert "Unable to create parent folder" in exc_msg


def test_add_hosts(web):  # pylint: disable=redefined-outer-name
    hosts = ["test-hosts1", "test-hosts2"]
    try:
        web.add_hosts(
            [
                (
                    hostname,
                    "",
                    {
                        "ipaddress": "127.0.0.1",
                    },
                )
                for hostname in hosts
            ]
        )
    finally:
        web.delete_hosts(hosts)


def test_edit_host(web):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-edit-host",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        web.edit_host("test-edit-host", attributes={"ipaddress": "127.10.0.1"})
    finally:
        web.delete_host("test-edit-host")


def test_edit_hosts(web):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-edit-hosts1",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )
        web.add_host(
            "test-edit-hosts2",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        web.edit_hosts(
            [
                ("test-edit-hosts1", {"ipaddress": "127.10.0.1"}, []),
                ("test-edit-hosts2", {"ipaddress": "127.20.0.1"}, []),
            ]
        )
    finally:
        web.delete_hosts(["test-edit-hosts1", "test-edit-hosts2"])


def test_get_all_hosts_basic(web):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-host-list",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        hosts = web.get_all_hosts()
        assert "test-host-list" in hosts
    finally:
        web.delete_host("test-host-list")


def test_delete_host(web):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-host-delete",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )
    finally:
        web.delete_host("test-host-delete")


def test_delete_hosts(web):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-hosts-delete1",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )
        web.add_host(
            "test-hosts-delete2",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )
    finally:
        web.delete_hosts(["test-hosts-delete1", "test-hosts-delete2"])


def test_get_host_effective_attributes(web):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-host",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        host = web.get_host("test-host", effective_attributes=False)
        assert "tag_networking" not in host["attributes"]

        host = web.get_host("test-host", effective_attributes=True)
        assert "tag_networking" in host["attributes"]
        assert host["attributes"]["tag_networking"] == "lan"
    finally:
        web.delete_host("test-host")


def test_get_all_hosts_effective_attributes(
    web,
):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-host",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        hosts = web.get_all_hosts(effective_attributes=False)
        host = hosts["test-host"]
        assert "tag_networking" not in host["attributes"]

        hosts = web.get_all_hosts(effective_attributes=True)
        host = hosts["test-host"]
        assert "tag_networking" in host["attributes"]
        assert host["attributes"]["tag_networking"] == "lan"
    finally:
        web.delete_host("test-host")


def test_get_ruleset(web):  # pylint: disable=redefined-outer-name
    response = web.get_ruleset("extra_host_conf:notification_options")
    assert response == {
        "ruleset": {
            "": [
                {"id": "814bf932-6341-4f96-983d-283525b5416d", "value": "d,r,f,s", "condition": {}}
            ]
        },
        "configuration_hash": "a8ee55e0ced14609df741e5a82462e3a",
    }

    # TODO: Move testing of initial wato rules to unit tests
    response = web.get_ruleset("inventory_df_rules")
    assert response == {
        "ruleset": {
            "": [
                {
                    "id": "b0ee8a51-703c-47e4-aec4-76430281604d",
                    "condition": {
                        "host_labels": {
                            "cmk/check_mk_server": "yes",
                        },
                    },
                    "value": {
                        "ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"],
                        "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"],
                    },
                }
            ]
        },
        "configuration_hash": "68e05dd8ab82cea5bebc9c6184c0ee08",
    }


def test_set_ruleset(web):  # pylint: disable=redefined-outer-name
    orig_ruleset = web.get_ruleset("bulkwalk_hosts")
    assert orig_ruleset == {
        "ruleset": {
            "": [
                {
                    "id": "b92a5406-1d57-4f1d-953d-225b111239e5",
                    "value": True,
                    "condition": {"host_tags": {"snmp": "snmp", "snmp_ds": {"$ne": "snmp-v1"}}},
                    "options": {
                        "description": 'Hosts with the tag "snmp-v1" must not use bulkwalk'
                    },
                }
            ]
        },
        "configuration_hash": "9abf6316805b3daf10ac7745864f13f8",
    }

    # Now modify something
    ruleset = copy.deepcopy(orig_ruleset)
    ruleset["ruleset"][""][0]["value"] = False
    response = web.set_ruleset("bulkwalk_hosts", ruleset)
    assert response is None

    try:
        changed = web.get_ruleset("bulkwalk_hosts")
        assert changed["ruleset"][""][0]["value"] is False
    finally:
        # revert it back
        del orig_ruleset["configuration_hash"]
        response = web.set_ruleset("bulkwalk_hosts", orig_ruleset)
        assert response is None


def test_get_site(web, site: Site):  # pylint: disable=redefined-outer-name
    response = web.get_site(site.id)
    assert "site_config" in response


def test_get_all_sites(web, site: Site):  # pylint: disable=redefined-outer-name
    response = web.get_all_sites()
    assert "sites" in response
    assert site.id in response["sites"]


@pytest.mark.parametrize(
    "sock_spec",
    [
        "tcp:1.2.3.4:6557",
        (
            "tcp",
            {
                "address": ("1.2.3.4", 6557),
                "tls": ("plain_text", {}),
            },
        ),
    ],
)
def test_set_site(web, site, sock_spec):  # pylint: disable=redefined-outer-name
    original_site = web.get_site(site.id)
    assert site.id == original_site["site_id"]

    new_site_id = "testsite"
    new_site_config = copy.deepcopy(original_site["site_config"])
    new_site_config["socket"] = sock_spec

    expected_site_config = copy.deepcopy(original_site["site_config"])
    expected_site_config["socket"] = (
        "tcp",
        {
            "address": ("1.2.3.4", 6557),
            "tls": ("plain_text", {}),
        },
    )

    try:
        web.set_site(new_site_id, new_site_config)

        new_response = web.get_site(new_site_id)
        assert new_site_id == new_response["site_id"]
        assert new_response["site_config"] == expected_site_config

        original_response = web.get_site(site.id)
        assert site.id == original_response["site_id"]
        assert original_response == original_site
    finally:
        web.delete_site(new_site_id)


@pytest.mark.parametrize(
    "sock_spec",
    [
        "tcp:1.2.3.4:6557",
        (
            "tcp",
            {
                "address": ("1.2.3.4", 6557),
                "tls": ("plain_text", {}),
            },
        ),
    ],
)
def test_set_all_sites(web, site, sock_spec):  # pylint: disable=redefined-outer-name
    response = web.get_all_sites()
    del response["configuration_hash"]

    new_site_id = "testsite"

    new_site_config = copy.deepcopy(response["sites"][site.id])
    new_site_config["socket"] = sock_spec

    expected_site_config = copy.deepcopy(copy.deepcopy(response["sites"][site.id]))
    expected_site_config["socket"] = (
        "tcp",
        {
            "address": ("1.2.3.4", 6557),
            "tls": ("plain_text", {}),
        },
    )

    response["sites"][new_site_id] = new_site_config

    try:
        web.set_all_sites(response)

        response = web.get_site(new_site_id)
        assert new_site_id == response["site_id"]
        assert response["site_config"] == expected_site_config
    finally:
        web.delete_site(new_site_id)


def test_write_host_tags(web, site: Site):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-host-dmz",
            attributes={
                "ipaddress": "127.0.0.1",
                "tag_networking": "dmz",
            },
        )

        web.add_host(
            "test-host-lan",
            attributes={
                "ipaddress": "127.0.0.1",
                "tag_networking": "lan",
            },
        )

        web.add_host(
            "test-host-lan2",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        hosts = web.get_all_hosts(effective_attributes=True)
        assert hosts["test-host-dmz"]["attributes"]["tag_networking"] == "dmz"
        assert hosts["test-host-lan"]["attributes"]["tag_networking"] == "lan"
        assert hosts["test-host-lan2"]["attributes"]["tag_networking"] == "lan"

        cfg: Dict[str, Any] = {
            "FOLDER_PATH": "/",
            "all_hosts": [],
            "host_tags": {},
            "host_labels": {},
            "ipaddresses": {},
            "host_attributes": {},
            "explicit_host_conf": {},
            "host_contactgroups": [],
            "service_contactgroups": [],
        }

        exec(site.read_file("etc/check_mk/conf.d/wato/hosts.mk"), cfg, cfg)

        assert "dmz" in cfg["host_tags"]["test-host-dmz"]["networking"]
        assert "lan" not in cfg["host_tags"]["test-host-dmz"]["networking"]

        assert "dmz" not in cfg["host_tags"]["test-host-lan"]["networking"]
        assert "lan" in cfg["host_tags"]["test-host-lan"]["networking"]

        assert "dmz" not in cfg["host_tags"]["test-host-lan2"]["networking"]
        assert "lan" in cfg["host_tags"]["test-host-lan2"]["networking"]

    finally:
        web.delete_hosts(["test-host-lan2", "test-host-lan", "test-host-dmz"])


def test_write_host_labels(web, site: Site):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-host-lan",
            attributes={"ipaddress": "127.0.0.1", "labels": {"blä": "blüb"}},
            verify_set_attributes=False,
        )

        hosts = web.get_all_hosts(effective_attributes=True)
        assert hosts["test-host-lan"]["attributes"]["labels"] == {"blä": "blüb"}

        cfg: Dict[str, Any] = {
            "FOLDER_PATH": "/",
            "all_hosts": [],
            "host_tags": {},
            "host_labels": {},
            "ipaddresses": {},
            "host_attributes": {},
            "explicit_host_conf": {},
            "host_contactgroups": [],
            "service_contactgroups": [],
        }

        exec(site.read_file("etc/check_mk/conf.d/wato/hosts.mk"), cfg, cfg)

        assert cfg["host_labels"]["test-host-lan"] == {
            "blä": "blüb",
        }

        for label_id, label_value in cfg["host_labels"]["test-host-lan"].items():
            assert isinstance(label_id, str)
            assert isinstance(label_value, str)

    finally:
        web.delete_hosts(["test-host-lan"])


# TODO: Parameterize test for cme / non cme
@pytest.mark.parametrize(("group_type"), ["contact", "host", "service"])
def test_add_group(web, group_type):  # pylint: disable=redefined-outer-name
    group_id = "%s_testgroup_id" % group_type
    group_alias = "%s_testgroup_alias" % group_type
    try:
        attributes = {"alias": group_alias}

        if cmk_version.is_managed_edition():
            attributes["customer"] = "provider"

        web.add_group(group_type, group_id, attributes)
        all_groups = web.get_all_groups(group_type)

        assert group_id in all_groups
        assert group_alias == all_groups[group_id]["alias"]

        if cmk_version.is_managed_edition():
            assert all_groups[group_id]["provider"] == "provider"
    finally:
        all_groups = web.get_all_groups(group_type)
        if group_id in all_groups:
            web.delete_group(group_type, group_id)


# TODO: Parameterize test for cme / non cme
@pytest.mark.parametrize(("group_type"), ["contact", "host", "service"])
def test_edit_group(web, group_type):  # pylint: disable=redefined-outer-name
    group_id = "%s_testgroup_id" % group_type
    group_alias = "%s_testgroup_alias" % group_type
    group_alias2 = "%s_testgroup_otheralias" % group_type
    try:
        attributes = {"alias": group_alias}

        if cmk_version.is_managed_edition():
            attributes["customer"] = "provider"

        web.add_group(group_type, group_id, attributes)

        attributes["alias"] = group_alias2
        web.edit_group(group_type, group_id, attributes)

        all_groups = web.get_all_groups(group_type)
        assert group_id in all_groups
        assert group_alias2 == all_groups[group_id]["alias"]

        if cmk_version.is_managed_edition():
            assert all_groups[group_id]["customer"] == "provider"
    finally:
        web.delete_group(group_type, group_id)


# TODO: Parameterize test for cme / non cme
@pytest.mark.parametrize(("group_type"), ["contact", "host", "service"])
def test_edit_group_missing(web, group_type):  # pylint: disable=redefined-outer-name
    group_id = "%s_testgroup_id" % group_type
    group_alias = "%s_testgroup_alias" % group_type
    group_alias2 = "%s_testgroup_otheralias" % group_type
    try:
        attributes = {"alias": group_alias}

        if cmk_version.is_managed_edition():
            attributes["customer"] = "provider"

        web.add_group(group_type, group_id, attributes)
        try:
            # web.edit_group(group_type, group_id, {"alias": group_alias2}, expect_error = True)
            web.edit_group(
                group_type, "%s_missing" % group_id, {"alias": group_alias2}, expect_error=True
            )
        except APIError as e:
            assert str(e) != str(None)
            return

        raise AssertionError()
    finally:
        web.delete_group(group_type, group_id)


# TODO: Parameterize test for cme / non cme
def test_edit_cg_group_with_nagvis_maps(web, site):  # pylint: disable=redefined-outer-name
    dummy_map_filepath1 = Path(site.root, "etc", "nagvis", "maps", "blabla.cfg")
    dummy_map_filepath2 = Path(site.root, "etc", "nagvis", "maps", "bloblo.cfg")
    try:
        dummy_map_filepath1.open(mode="w")

        dummy_map_filepath2.open(mode="w")

        attributes = {"alias": "nagvis_test_alias", "nagvis_maps": ["blabla"]}

        if cmk_version.is_managed_edition():
            attributes["customer"] = "provider"

        web.add_group("contact", "nagvis_test", attributes)

        attributes["nagvis_maps"] = ["bloblo"]
        web.edit_group("contact", "nagvis_test", attributes)

        all_groups = web.get_all_groups("contact")
        assert "nagvis_test" in all_groups
        assert "bloblo" in all_groups["nagvis_test"]["nagvis_maps"]
    finally:
        web.delete_group("contact", "nagvis_test")
        dummy_map_filepath1.unlink()
        dummy_map_filepath2.unlink()


# TODO: Parameterize test for cme / non cme
@pytest.mark.parametrize(("group_type"), ["contact", "host", "service"])
def test_delete_group(web, group_type):  # pylint: disable=redefined-outer-name
    group_id = "%s_testgroup_id" % group_type
    group_alias = "%s_testgroup_alias" % group_type
    try:
        attributes = {"alias": group_alias}

        if cmk_version.is_managed_edition():
            attributes["customer"] = "provider"

        web.add_group(group_type, group_id, attributes)
    finally:
        web.delete_group(group_type, group_id)


def test_get_all_users(web):  # pylint: disable=redefined-outer-name
    users = {
        "klaus": {"alias": "mr. klaus", "pager": "99221199", "password": "1234"},
        "monroe": {"alias": "mr. monroe"},
    }
    expected_users = set(["cmkadmin", "automation"] + list(users.keys()))
    try:
        web.add_htpasswd_users(users)
        all_users = web.get_all_users()
        assert not expected_users - set(all_users.keys())
    finally:
        web.delete_htpasswd_users(list(users.keys()))


def test_add_htpasswd_users(web):  # pylint: disable=redefined-outer-name
    users = {
        "klaus": {"alias": "mr. klaus", "pager": "99221199", "password": "1234"},
        "monroe": {"alias": "mr. monroe"},
    }
    try:
        web.add_htpasswd_users(users)
    finally:
        web.delete_htpasswd_users(list(users.keys()))


def test_edit_htpasswd_users(web):  # pylint: disable=redefined-outer-name
    users = {
        "klaus": {"alias": "mr. klaus", "pager": "99221199", "password": "1234"},
        "monroe": {"alias": "mr. monroe"},
    }
    try:
        web.add_htpasswd_users(users)
        web.edit_htpasswd_users(
            {
                "monroe": {"set_attributes": {"alias": "ms. monroe"}},
                "klaus": {"unset_attributes": ["pager"]},
            }
        )
        all_users = web.get_all_users()
        assert "pager" not in all_users["klaus"]
        assert all_users["monroe"]["alias"] == "ms. monroe"
    finally:
        web.delete_htpasswd_users(list(users.keys()))


def test_discover_services(web, local_test_hosts):  # pylint: disable=redefined-outer-name
    web.discover_services("test-host")


def test_bulk_discovery_start_with_empty_hosts(
    web,
):  # pylint: disable=redefined-outer-name
    with pytest.raises(APIError, match="specify some host"):
        web.bulk_discovery_start(
            {
                "hostnames": [],
            },
            expect_error=True,
        )


def test_bulk_discovery_unknown_host(web):  # pylint: disable=redefined-outer-name
    with pytest.raises(APIError, match="does not exist"):
        web.bulk_discovery_start(
            {
                "hostnames": ["nono"],
            },
            expect_error=True,
        )


def _wait_for_bulk_discovery_job(web):  # pylint: disable=redefined-outer-name
    def job_completed():
        status = web.bulk_discovery_status()
        return status["job"]["state"] != "initialized" and status["is_active"] is False

    wait_until(job_completed, timeout=30, interval=1)


def test_bulk_discovery_start_with_defaults(
    web, local_test_hosts
):  # pylint: disable=redefined-outer-name
    result = web.bulk_discovery_start(
        {
            "hostnames": ["test-host"],
        }
    )
    assert result["started"] is True

    _wait_for_bulk_discovery_job(web)

    status = web.bulk_discovery_status()
    assert status["is_active"] is False
    assert status["job"]["state"] == "finished"
    assert "discovery successful" in status["job"]["result_msg"]
    assert "discovery started" in status["job"]["output"]
    assert "test-host: discovery successful" in status["job"]["output"]


def test_bulk_discovery_start_with_parameters(
    web, local_test_hosts
):  # pylint: disable=redefined-outer-name
    result = web.bulk_discovery_start(
        {
            "hostnames": ["test-host"],
            "mode": "new",
            "use_cache": True,
            "do_scan": True,
            "bulk_size": 5,
            "ignore_single_check_errors": True,
        }
    )
    assert result["started"] is True

    _wait_for_bulk_discovery_job(web)

    status = web.bulk_discovery_status()
    assert status["is_active"] is False
    assert status["job"]["state"] == "finished"


def test_bulk_discovery_start_multiple_with_subdir(
    web, local_test_hosts
):  # pylint: disable=redefined-outer-name
    result = web.bulk_discovery_start(
        {
            "hostnames": ["test-host", "test-host2"],
            "mode": "new",
            "use_cache": True,
            "do_scan": True,
            "bulk_size": 5,
            "ignore_single_check_errors": True,
        }
    )
    assert result["started"] is True

    _wait_for_bulk_discovery_job(web)

    status = web.bulk_discovery_status()
    assert status["is_active"] is False
    assert status["job"]["state"] == "finished"


def test_activate_changes(web, site: Site):  # pylint: disable=redefined-outer-name
    try:
        web.add_host(
            "test-host-activate",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        site.activate_changes_and_wait_for_core_reload()

        result = site.live.query("GET hosts\nColumns: name\nFilter: name = test-host-activate\n")
        assert result == [["test-host-activate"]]
    finally:
        web.delete_host("test-host-activate")
        site.activate_changes_and_wait_for_core_reload()


@pytest.fixture(scope="module")
def graph_test_config(web, site: Site):  # pylint: disable=redefined-outer-name
    # No graph yet...
    with pytest.raises(APIError) as exc_info:
        web.get_regular_graph("test-host-get-graph", "Check_MK", 0, expect_error=True)
        assert "Cannot calculate graph recipes" in "%s" % exc_info

    try:
        # Now add the host
        web.add_host(
            "test-host-get-graph",
            attributes={
                "ipaddress": "127.0.0.1",
            },
        )

        site.write_text_file(
            "etc/check_mk/conf.d/test-host-get-graph.mk",
            "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['test-host-get-graph']))\n",
        )

        site.makedirs("var/check_mk/agent_output/")
        site.write_text_file(
            "var/check_mk/agent_output/test-host-get-graph", get_standard_linux_agent_output()
        )

        web.discover_services("test-host-get-graph")
        site.activate_changes_and_wait_for_core_reload()
        site.schedule_check("test-host-get-graph", "Check_MK", 0)

        # Wait for RRD file creation. Isn't this a bug that the graph is not instantly available?
        rrd_path = (
            site.path("var/pnp4nagios/perfdata/test-host-get-graph/Check_MK_system_time.rrd")
            if cmk_version.is_raw_edition()
            else site.path("var/check_mk/rrd/test-host-get-graph/Check_MK.rrd")
        )
        for attempt in range(50):
            time.sleep(0.1)
            proc = subprocess.run(
                [site.path("bin/unixcat"), site.path("tmp/run/rrdcached.sock")],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                encoding="utf-8",
                input="FLUSH %s\n" % rrd_path,
            )

            if os.path.exists(rrd_path):
                break
            sys.stdout.write(
                "waiting for %s (attempt %d)%s%s\n"
                % (
                    rrd_path,
                    attempt + 1,  #
                    ", stdout: %s" % proc.stdout,
                    ", stderr: %s" % proc.stderr,
                )
            )
        else:
            raise AssertionError("RRD file %s missing" % rrd_path)

        yield
    finally:
        web.delete_host("test-host-get-graph")
        site.delete_file("etc/check_mk/conf.d/test-host-get-graph.mk")
    site.activate_changes_and_wait_for_core_reload()


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported in raw edition")
def test_get_graph_api(web, graph_test_config):  # pylint: disable=redefined-outer-name
    # Now we get a graph
    data = web.get_regular_graph("test-host-get-graph", "Check_MK", 0)

    if cmk_version.is_raw_edition():
        expected_curves = [
            "CPU time in user space",
            "CPU time in system space",
            "Total",
        ]
    else:
        expected_curves = [
            "CPU time in user space",
            "CPU time in operating system",
            "Time spent waiting for Checkmk agent",
            "Time spent waiting for special agent",
            "Total execution time",
        ]

    assert len(data["curves"]) == len(expected_curves)
    for idx, title in enumerate(expected_curves):
        assert data["curves"][idx]["title"] == title


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported in raw edition")
def test_get_graph_image(web, graph_test_config):  # pylint: disable=redefined-outer-name
    result = web.post(
        "graph_image.py",
        data={
            "request": json.dumps(
                {
                    "specification": [
                        "template",
                        {
                            "service_description": "Check_MK",
                            "site": web.site.id,
                            "graph_index": 0,
                            "host_name": "test-host-get-graph",
                        },
                    ],
                }
            ),
        },
    )

    content = result.content

    assert content.startswith(b"\x89PNG")

    try:
        Image.open(BytesIO(content))
    except IOError:
        raise Exception("Failed to open image: %r" % content)


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported in raw edition")
def test_get_graph_notification_image(
    web, graph_test_config
):  # pylint: disable=redefined-outer-name
    result = web.get("ajax_graph_images.py?host=test-host-get-graph&service=Check_MK")

    # Provides a json list containing base64 encoded PNG images of the current 24h graphs
    encoded_graph_list = json.loads(result.text)
    assert isinstance(encoded_graph_list, list)
    assert len(encoded_graph_list) > 0

    for encoded_graph_image in encoded_graph_list:
        graph_image = base64.b64decode(encoded_graph_image)

        assert graph_image.startswith(b"\x89PNG")

        try:
            Image.open(BytesIO(graph_image))
        except IOError:
            raise Exception("Failed to open image: %r" % graph_image)


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported in raw edition")
def test_get_graph_hover(web, graph_test_config):  # pylint: disable=redefined-outer-name
    metrics: List[Dict[str, Any]] = [
        {
            "color": "#87f058",
            "line_type": "stack",
            "expression": [
                "operator",
                "+",
                [
                    [
                        "rrd",
                        "test-host-get-graph",
                        "test-host-get-graph",
                        "Check_MK",
                        "user_time",
                        None,
                        1,
                    ],
                    [
                        "rrd",
                        "test-host-get-graph",
                        "test-host-get-graph",
                        "Check_MK",
                        "children_user_time",
                        None,
                        1,
                    ],
                ],
            ],
            "unit": "s",
            "title": "CPU time in user space",
        },
        {
            "color": "#ff8840",
            "line_type": "stack",
            "expression": [
                "operator",
                "+",
                [
                    [
                        "rrd",
                        "test-host-get-graph",
                        "test-host-get-graph",
                        "Check_MK",
                        "system_time",
                        None,
                        1,
                    ],
                    [
                        "rrd",
                        "test-host-get-graph",
                        "test-host-get-graph",
                        "Check_MK",
                        "children_system_time",
                        None,
                        1,
                    ],
                ],
            ],
            "unit": "s",
            "title": "CPU time in operating system",
        },
        {
            "color": "#00b2ff",
            "line_type": "stack",
            "expression": [
                "rrd",
                "test-host-get-graph",
                "test-host-get-graph",
                "Check_MK",
                "cmk_time_agent",
                None,
                1,
            ],
            "unit": "s",
            "title": "Time spent waiting for Check_MK agent",
        },
        {
            "color": "#d080af",
            "line_type": "line",
            "expression": [
                "rrd",
                "test-host-get-graph",
                "test-host-get-graph",
                "Check_MK",
                "execution_time",
                None,
                1,
            ],
            "unit": "s",
            "title": "Total execution time",
        },
    ]
    graph_context = {
        "definition": {
            "explicit_vertical_range": [None, None],
            "title": "Time usage by phase",
            "horizontal_rules": [],
            "specification": [
                "template",
                {
                    "service_description": "Check_MK",
                    "site": web.site.id,
                    "graph_index": 0,
                    "host_name": "test-host-get-graph",
                },
            ],
            "consolidation_function": "max",
            "metrics": metrics,
            "omit_zero_metrics": False,
            "unit": "s",
        },
        "graph_id": "graph_0",
        "data_range": {"step": 20, "time_range": [time.time() - 3600, time.time()]},
        "render_options": {
            "preview": False,
            "editing": False,
            "font_size": 8,
            "show_graph_time": True,
            "resizable": True,
            "show_time_axis": True,
            "fixed_timerange": False,
            "foreground_color": "#000000",
            "title_format": "plain",
            "canvas_color": "#ffffff",
            "show_legend": True,
            "interaction": True,
            "show_time_range_previews": True,
            "show_title": True,
            "show_margin": True,
            "vertical_axis_width": "fixed",
            "show_controls": True,
            "show_pin": True,
            "background_color": "#f8f4f0",
            "show_vertical_axis": True,
            "size": [70, 16],
        },
    }

    result = web.post(
        "ajax_graph_hover.py",
        data={
            "context": json.dumps(graph_context),
            "hover_time": int(time.time() - 300),
        },
    )

    data = result.json()

    assert "rendered_hover_time" in data
    assert len(data["curve_values"]) == 4

    for index, metric in enumerate(metrics[::-1]):
        curve_value = data["curve_values"][index]

        assert curve_value["color"] == metric["color"]
        assert curve_value["title"] == metric["title"]

        # TODO: Wait for first values?
        assert curve_value["rendered_value"][0] is None
        assert curve_value["rendered_value"][1] == "n/a"
        # assert isinstance(curve_value["rendered_value"][0], (int, float))
        # assert curve_value["rendered_value"][1] != ""


def test_get_inventory(web):  # pylint: disable=redefined-outer-name
    host_name = "test-host"
    inventory_dir = "var/check_mk/inventory"
    try:
        web.add_host(host_name, attributes={"ipaddress": "127.0.0.1"})
        # NOTE: Deleting the host deletes the file, too.
        web.site.makedirs(inventory_dir)
        web.site.write_text_file(
            os.path.join(inventory_dir, host_name),
            "{'hardware': {'memory': {'ram': 10000, 'foo': 1}, 'blubb': 42}}",
        )

        inv = web.get_inventory([host_name])
        assert inv[host_name] == {
            "Attributes": {},
            "Table": {},
            "Nodes": {
                "hardware": {
                    "Attributes": {"Pairs": {"blubb": 42}},
                    "Table": {},
                    "Nodes": {
                        "memory": {
                            "Attributes": {"Pairs": {"ram": 10000, "foo": 1}},
                            "Table": {},
                            "Nodes": {},
                        }
                    },
                }
            },
        }

        inv = web.get_inventory([host_name], paths=[".hardware.memory."])
        assert inv[host_name] == {
            "Attributes": {},
            "Table": {},
            "Nodes": {
                "hardware": {
                    "Attributes": {},
                    "Table": {},
                    "Nodes": {
                        "memory": {
                            "Attributes": {"Pairs": {"ram": 10000, "foo": 1}},
                            "Table": {},
                            "Nodes": {},
                        }
                    },
                }
            },
        }

        inv = web.get_inventory([host_name], paths=[".hardware.mumpf."])
        assert inv[host_name] == {"Attributes": {}, "Nodes": {}, "Table": {}}
    finally:
        web.delete_host(host_name)


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported in raw edition")
def test_get_user_sites(web, graph_test_config):  # pylint: disable=redefined-outer-name
    assert web.get_user_sites()[0][0] == web.site.id


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported in raw edition")
def test_get_host_names(web, graph_test_config):  # pylint: disable=redefined-outer-name
    assert "test-host-get-graph" in web.get_host_names(request={})


@pytest.mark.skip("the test is too strict, the indices are a random permutation of 0..2")
def test_get_metrics_of_host(web, graph_test_config):  # pylint: disable=redefined-outer-name
    # Do not validate the whole response, just a sample entry
    response = web.get_metrics_of_host(request={"hostname": "test-host-get-graph"})
    assert response["CPU load"] == {
        "check_command": "check_mk-cpu.loads",
        "metrics": {
            "load1": {"index": 1, "name": "load1", "title": "CPU load average of last minute"},
            "load15": {
                "index": 0,
                "name": "load15",
                "title": "CPU load average of last 15 minutes",
            },
            "load5": {"index": 2, "name": "load5", "title": "CPU load average of last 5 minutes"},
        },
    }


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported in raw edition")
def test_get_graph_recipes(web, graph_test_config):  # pylint: disable=redefined-outer-name
    if cmk_version.is_raw_edition():
        expected_recipe = [
            {
                "title": "Used CPU Time",
                "metrics": [
                    {
                        "unit": "s",
                        "color": "#60f020",
                        "title": "CPU time in user space",
                        "line_type": "area",
                        "expression": [
                            "rrd",
                            web.site.id,
                            "test-host-get-graph",
                            "Check_MK",
                            "user_time",
                            "max",
                            1.0,
                        ],
                    },
                    {
                        "unit": "s",
                        "color": "#aef090",
                        "title": "Child time in user space",
                        "line_type": "stack",
                        "expression": [
                            "rrd",
                            web.site.id,
                            "test-host-get-graph",
                            "Check_MK",
                            "children_user_time",
                            "max",
                            1.0,
                        ],
                    },
                    {
                        "unit": "s",
                        "color": "#ff6000",
                        "title": "CPU time in system space",
                        "line_type": "stack",
                        "expression": [
                            "rrd",
                            web.site.id,
                            "test-host-get-graph",
                            "Check_MK",
                            "system_time",
                            "max",
                            1.0,
                        ],
                    },
                    {
                        "unit": "s",
                        "color": "#ffb080",
                        "title": "Child time in system space",
                        "line_type": "stack",
                        "expression": [
                            "rrd",
                            web.site.id,
                            "test-host-get-graph",
                            "Check_MK",
                            "children_system_time",
                            "max",
                            1.0,
                        ],
                    },
                    {
                        "unit": "s",
                        "color": "#888888",
                        "title": "Total",
                        "line_type": "line",
                        "expression": [
                            "operator",
                            "+",
                            [
                                [
                                    "rrd",
                                    web.site.id,
                                    "test-host-get-graph",
                                    "Check_MK",
                                    "user_time",
                                    "max",
                                    1.0,
                                ],
                                [
                                    "operator",
                                    "+",
                                    [
                                        [
                                            "rrd",
                                            web.site.id,
                                            "test-host-get-graph",
                                            "Check_MK",
                                            "children_user_time",
                                            "max",
                                            1.0,
                                        ],
                                        [
                                            "operator",
                                            "+",
                                            [
                                                [
                                                    "rrd",
                                                    web.site.id,
                                                    "test-host-get-graph",
                                                    "Check_MK",
                                                    "system_time",
                                                    "max",
                                                    1.0,
                                                ],
                                                [
                                                    "rrd",
                                                    web.site.id,
                                                    "test-host-get-graph",
                                                    "Check_MK",
                                                    "children_system_time",
                                                    "max",
                                                    1.0,
                                                ],
                                            ],
                                        ],
                                    ],
                                ],
                            ],
                        ],
                    },
                ],
                "unit": "s",
                "explicit_vertical_range": [None, None],
                "horizontal_rules": [],
                "omit_zero_metrics": True,
                "consolidation_function": "max",
                "specification": [
                    "template",
                    {
                        "service_description": "Check_MK",
                        "site": web.site.id,
                        "graph_index": 0,
                        "host_name": "test-host-get-graph",
                        "graph_id": "used_cpu_time",
                    },
                ],
            }
        ]

    else:
        expected_recipe = [
            {
                "consolidation_function": "max",
                "explicit_vertical_range": [None, None],
                "horizontal_rules": [],
                "metrics": [
                    {
                        "color": "#87f058",
                        "expression": [
                            "operator",
                            "+",
                            [
                                [
                                    "rrd",
                                    web.site.id,
                                    "test-host-get-graph",
                                    "Check_MK",
                                    "user_time",
                                    "max",
                                    1.0,
                                ],
                                [
                                    "rrd",
                                    web.site.id,
                                    "test-host-get-graph",
                                    "Check_MK",
                                    "children_user_time",
                                    "max",
                                    1.0,
                                ],
                            ],
                        ],
                        "line_type": "stack",
                        "title": "CPU time in user space",
                        "unit": "s",
                    },
                    {
                        "color": "#ff8840",
                        "expression": [
                            "operator",
                            "+",
                            [
                                [
                                    "rrd",
                                    web.site.id,
                                    "test-host-get-graph",
                                    "Check_MK",
                                    "system_time",
                                    "max",
                                    1.0,
                                ],
                                [
                                    "rrd",
                                    web.site.id,
                                    "test-host-get-graph",
                                    "Check_MK",
                                    "children_system_time",
                                    "max",
                                    1.0,
                                ],
                            ],
                        ],
                        "line_type": "stack",
                        "title": "CPU time in operating system",
                        "unit": "s",
                    },
                    {
                        "color": "#0093ff",
                        "expression": [
                            "rrd",
                            web.site.id,
                            "test-host-get-graph",
                            "Check_MK",
                            "cmk_time_agent",
                            "max",
                            1.0,
                        ],
                        "line_type": "stack",
                        "title": "Time spent waiting for Checkmk agent",
                        "unit": "s",
                    },
                    {
                        "color": "#00d1ff",
                        "expression": [
                            "rrd",
                            web.site.id,
                            "test-host-get-graph",
                            "Check_MK",
                            "cmk_time_ds",
                            "max",
                            1.0,
                        ],
                        "line_type": "stack",
                        "title": "Time spent waiting for special agent",
                        "unit": "s",
                    },
                    {
                        "color": "#d080af",
                        "expression": [
                            "rrd",
                            web.site.id,
                            "test-host-get-graph",
                            "Check_MK",
                            "execution_time",
                            "max",
                            1.0,
                        ],
                        "line_type": "line",
                        "title": "Total execution time",
                        "unit": "s",
                    },
                ],
                "omit_zero_metrics": False,
                "specification": [
                    "template",
                    {
                        "graph_index": 0,
                        "graph_id": "cmk_cpu_time_by_phase",
                        "host_name": "test-host-get-graph",
                        "service_description": "Check_MK",
                        "site": web.site.id,
                    },
                ],
                "title": "Time usage by phase",
                "unit": "s",
            },
        ]

    assert (
        web.get_graph_recipes(
            request={
                "specification": [
                    "template",
                    {
                        "service_description": "Check_MK",
                        "site": web.site.id,
                        "graph_index": 0,
                        "host_name": "test-host-get-graph",
                    },
                ],
            }
        )
        == expected_recipe
    )


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported with raw edition")
def test_get_combined_graph_identifications(
    web, graph_test_config
):  # pylint: disable=redefined-outer-name
    result = web.get_combined_graph_identifications(
        request={
            "single_infos": ["host"],
            "datasource": "services",
            "context": {
                "service": {"service": "CPU load"},
                "siteopt": {"site": web.site.id},
                "host": {"host": "test-host-get-graph"},
            },
        }
    )

    assert result == [
        {
            "identification": [
                "combined",
                {
                    "context": {
                        "host": {"host": "test-host-get-graph"},
                        "service": {"service": "CPU load"},
                        "siteopt": {
                            "site": web.site.id,
                        },
                    },
                    "datasource": "services",
                    "graph_template": "cpu_load",
                    "presentation": "sum",
                    "single_infos": ["host"],
                },
            ],
            "title": "CPU Load - %(load1:max@count) CPU Cores",
        },
    ]


@pytest.mark.skipif(cmk_version.is_raw_edition(), reason="not supported in raw edition")
def test_get_graph_annotations(web, graph_test_config):  # pylint: disable=redefined-outer-name
    now = time.time()
    start_time, end_time = now - 3601, now

    result = web.get_graph_annotations(
        request={
            "context": {
                "site": {
                    "site": web.site.id,
                },
                "service": {
                    "service": "CPU load",
                },
                "host": "test-host-get-graph",
            },
            "start_time": start_time,
            "end_time": end_time,
        }
    )

    assert len(result["availability_timelines"]) == 1
    assert result["availability_timelines"][0]["display_name"] == "CPU load"


def test_get_hosttags(web):  # pylint: disable=redefined-outer-name
    host_tags = web.get_hosttags()
    assert isinstance(host_tags["configuration_hash"], str)
    assert host_tags["aux_tags"] == []

    assert isinstance(host_tags["tag_groups"], list)
    assert host_tags["tag_groups"][0]["id"] == "criticality"


def test_set_hosttags(web):  # pylint: disable=redefined-outer-name
    original_host_tags = web.get_hosttags()

    location_tag_group = {
        "id": "location",
        "tags": [
            {"aux_tags": [], "id": "munich", "title": "Munich"},
            {"aux_tags": [], "id": "essen", "title": "Essen"},
            {"aux_tags": [], "id": "berlin", "title": "Berlin"},
        ],
        "title": "Location",
    }
    host_tags = copy.deepcopy(original_host_tags)
    host_tags["tag_groups"].append(location_tag_group)

    try:
        web.set_hosttags(
            request={
                "aux_tags": host_tags["aux_tags"],
                "tag_groups": host_tags["tag_groups"],
                "configuration_hash": host_tags["configuration_hash"],
            }
        )

        new_host_tags = web.get_hosttags()
        assert location_tag_group in new_host_tags["tag_groups"]
    finally:
        web.set_hosttags(
            request={
                "aux_tags": original_host_tags["aux_tags"],
                "tag_groups": original_host_tags["tag_groups"],
            }
        )
