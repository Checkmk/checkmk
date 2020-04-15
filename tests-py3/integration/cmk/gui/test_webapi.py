#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# pylint: disable=redefined-outer-name
# flake8: noqa

import base64
import copy
import json
import os
from io import BytesIO
import subprocess
import sys
import time
import six

import pytest  # type: ignore[import]
from PIL import Image  # type: ignore[import]

import cmk.utils.version as cmk_version
from testlib import web, APIError, wait_until  # pylint: disable=unused-import # noqa: F401
from testlib.utils import get_standard_linux_agent_output


@pytest.fixture(name="local_test_hosts")
def fixture_local_test_hosts(web, site):
    site.makedirs("var/check_mk/agent_output/")

    web.add_hosts([
        ("test-host", "", {
            "ipaddress": "127.0.0.1",
        }),
        ("test-host2", "xy/zzz", {
            "ipaddress": "127.0.0.1",
        }),
    ])

    site.write_file(
        "etc/check_mk/conf.d/local-test-hosts.mk",
        "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['test-host', 'test-host2']))\n"
    )

    for hostname in ["test-host", "test-host2"]:
        site.write_file("var/check_mk/agent_output/%s" % hostname,
                        get_standard_linux_agent_output())

    yield

    for hostname in ["test-host", "test-host2"]:
        web.delete_host(hostname)
        site.delete_file("var/check_mk/agent_output/%s" % hostname)
    site.delete_file("etc/check_mk/conf.d/local-test-hosts.mk")


def test_global_settings(site, web):
    r = web.get("wato.py")
    assert "Global Settings" in r.text


def test_add_host(web):
    try:
        # Also tests get_host
        web.add_host("test-host", attributes={
            "ipaddress": "127.0.0.1",
        })
    finally:
        web.delete_host("test-host")


def test_add_host_folder_create(web):
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


def test_add_host_no_folder_create(web):
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


def test_add_hosts(web):
    hosts = ["test-hosts1", "test-hosts2"]
    try:
        web.add_hosts([(hostname, "", {
            "ipaddress": "127.0.0.1",
        }) for hostname in hosts])
    finally:
        web.delete_hosts(hosts)


def test_edit_host(web):
    try:
        web.add_host("test-edit-host", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.edit_host("test-edit-host", attributes={"ipaddress": "127.10.0.1"})
    finally:
        web.delete_host("test-edit-host")


def test_edit_hosts(web):
    try:
        web.add_host("test-edit-hosts1", attributes={
            "ipaddress": "127.0.0.1",
        })
        web.add_host("test-edit-hosts2", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.edit_hosts([
            ("test-edit-hosts1", {
                "ipaddress": "127.10.0.1"
            }, []),
            ("test-edit-hosts2", {
                "ipaddress": "127.20.0.1"
            }, []),
        ])
    finally:
        web.delete_hosts(["test-edit-hosts1", "test-edit-hosts2"])


def test_get_all_hosts_basic(web):
    try:
        web.add_host("test-host-list", attributes={
            "ipaddress": "127.0.0.1",
        })

        hosts = web.get_all_hosts()
        assert "test-host-list" in hosts
    finally:
        web.delete_host("test-host-list")


def test_delete_host(web):
    try:
        web.add_host("test-host-delete", attributes={
            "ipaddress": "127.0.0.1",
        })
    finally:
        web.delete_host("test-host-delete")


def test_delete_hosts(web):
    try:
        web.add_host("test-hosts-delete1", attributes={
            "ipaddress": "127.0.0.1",
        })
        web.add_host("test-hosts-delete2", attributes={
            "ipaddress": "127.0.0.1",
        })
    finally:
        web.delete_hosts(["test-hosts-delete1", "test-hosts-delete2"])


def test_get_host_effective_attributes(web):
    try:
        web.add_host("test-host", attributes={
            "ipaddress": "127.0.0.1",
        })

        host = web.get_host("test-host", effective_attributes=False)
        assert "tag_networking" not in host["attributes"]

        host = web.get_host("test-host", effective_attributes=True)
        assert "tag_networking" in host["attributes"]
        assert host["attributes"]["tag_networking"] == "lan"
    finally:
        web.delete_host("test-host")


def test_get_all_hosts_effective_attributes(web):
    try:
        web.add_host("test-host", attributes={
            "ipaddress": "127.0.0.1",
        })

        hosts = web.get_all_hosts(effective_attributes=False)
        host = hosts["test-host"]
        assert "tag_networking" not in host["attributes"]

        hosts = web.get_all_hosts(effective_attributes=True)
        host = hosts["test-host"]
        assert "tag_networking" in host["attributes"]
        assert host["attributes"]["tag_networking"] == "lan"
    finally:
        web.delete_host("test-host")


def test_get_ruleset(web):
    response = web.get_ruleset("extra_host_conf:notification_options")
    assert response == {
        'ruleset': {
            '': [{
                'value': 'd,r,f,s',
                'condition': {}
            }]
        },
        'configuration_hash': 'b76f205bbe674300f677a282d9ccd71f',
    }

    # TODO: Move testing of initial wato rules to unit tests
    response = web.get_ruleset("inventory_df_rules")
    assert response == {
        'ruleset': {
            '': [{
                'condition': {
                    'host_labels': {
                        u'cmk/check_mk_server': u'yes',
                    },
                },
                'value': {
                    'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'],
                    'never_ignore_mountpoints': [u'~.*/omd/sites/[^/]+/tmp$']
                }
            }]
        },
        'configuration_hash': '0ef816195d483f9ed828a4dc84bdf706',
    }


def test_set_ruleset(web):
    orig_ruleset = web.get_ruleset("bulkwalk_hosts")
    assert orig_ruleset == {
        'ruleset': {
            '': [{
                'value': True,
                'condition': {
                    'host_tags': {
                        'snmp': 'snmp',
                        'snmp_ds': {
                            '$ne': 'snmp-v1'
                        }
                    }
                },
                'options': {
                    'description': u'Hosts with the tag "snmp-v1" must not use bulkwalk'
                }
            }]
        },
        'configuration_hash': '0cca93426feb558f7c9f09631340c63c',
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


def test_get_site(web, site):
    response = web.get_site(site.id)
    assert "site_config" in response


def test_get_all_sites(web, site):
    response = web.get_all_sites()
    assert "sites" in response
    assert site.id in response["sites"]


@pytest.mark.parametrize("sock_spec", [
    "tcp:1.2.3.4:6557",
    ("tcp", {
        "address": ("1.2.3.4", 6557),
        "tls": ("plain_text", {}),
    }),
])
def test_set_site(web, site, sock_spec):
    original_site = web.get_site(site.id)
    assert site.id == original_site["site_id"]

    new_site_id = "testsite"
    new_site_config = copy.deepcopy(original_site["site_config"])
    new_site_config["socket"] = sock_spec

    expected_site_config = copy.deepcopy(original_site["site_config"])
    expected_site_config["socket"] = ("tcp", {
        "address": ("1.2.3.4", 6557),
        "tls": ("plain_text", {}),
    })

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


@pytest.mark.parametrize("sock_spec", [
    "tcp:1.2.3.4:6557",
    ("tcp", {
        "address": ("1.2.3.4", 6557),
        "tls": ("plain_text", {}),
    }),
])
def test_set_all_sites(web, site, sock_spec):
    response = web.get_all_sites()
    del response["configuration_hash"]

    new_site_id = "testsite"

    new_site_config = copy.deepcopy(response["sites"][site.id])
    new_site_config["socket"] = sock_spec

    expected_site_config = copy.deepcopy(copy.deepcopy(response["sites"][site.id]))
    expected_site_config["socket"] = ("tcp", {
        "address": ("1.2.3.4", 6557),
        "tls": ("plain_text", {}),
    })

    response["sites"][new_site_id] = new_site_config

    try:
        web.set_all_sites(response)

        response = web.get_site(new_site_id)
        assert new_site_id == response["site_id"]
        assert response["site_config"] == expected_site_config
    finally:
        web.delete_site(new_site_id)


def test_write_host_tags(web, site):
    try:
        web.add_host("test-host-dmz",
                     attributes={
                         "ipaddress": "127.0.0.1",
                         "tag_networking": "dmz",
                     })

        web.add_host("test-host-lan",
                     attributes={
                         "ipaddress": "127.0.0.1",
                         "tag_networking": "lan",
                     })

        web.add_host("test-host-lan2", attributes={
            "ipaddress": "127.0.0.1",
        })

        hosts = web.get_all_hosts(effective_attributes=True)
        assert hosts["test-host-dmz"]["attributes"]["tag_networking"] == "dmz"
        assert hosts["test-host-lan"]["attributes"]["tag_networking"] == "lan"
        assert hosts["test-host-lan2"]["attributes"]["tag_networking"] == "lan"

        cfg = {
            "FOLDER_PATH": "/",
            "all_hosts": [],
            "host_tags": {},
            "host_labels": {},
            "ipaddresses": {},
            "host_attributes": {},
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


def test_write_host_labels(web, site):
    try:
        web.add_host("test-host-lan",
                     attributes={
                         "ipaddress": "127.0.0.1",
                         'labels': {
                             'blä': 'blüb'
                         }
                     },
                     verify_set_attributes=False)

        hosts = web.get_all_hosts(effective_attributes=True)
        assert hosts["test-host-lan"]["attributes"]["labels"] == {u'blä': u'blüb'}

        cfg = {
            "FOLDER_PATH": "/",
            "all_hosts": [],
            "host_tags": {},
            "host_labels": {},
            "ipaddresses": {},
            "host_attributes": {},
        }

        exec(site.read_file("etc/check_mk/conf.d/wato/hosts.mk"), cfg, cfg)

        assert cfg["host_labels"]["test-host-lan"] == {
            u"blä": u"blüb",
        }

        for label_id, label_value in cfg["host_labels"]["test-host-lan"].items():
            assert isinstance(label_id, six.text_type)
            assert isinstance(label_value, six.text_type)

    finally:
        web.delete_hosts(["test-host-lan"])


# TODO: Parameterize test for cme / non cme
@pytest.mark.parametrize(("group_type"), ["contact", "host", "service"])
def test_add_group(web, group_type):
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
def test_edit_group(web, group_type):
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
def test_edit_group_missing(web, group_type):
    group_id = "%s_testgroup_id" % group_type
    group_alias = "%s_testgroup_alias" % group_type
    group_alias2 = "%s_testgroup_otheralias" % group_type
    try:
        attributes = {"alias": group_alias}

        if cmk_version.is_managed_edition():
            attributes["customer"] = "provider"

        web.add_group(group_type, group_id, attributes)
        try:
            #web.edit_group(group_type, group_id, {"alias": group_alias2}, expect_error = True)
            web.edit_group(group_type,
                           "%s_missing" % group_id, {"alias": group_alias2},
                           expect_error=True)
        except APIError as e:
            assert str(e) != str(None)
            return

        assert False
    finally:
        web.delete_group(group_type, group_id)


# TODO: Parameterize test for cme / non cme
def test_edit_cg_group_with_nagvis_maps(web, site):
    dummy_map_filepath1 = "%s/etc/nagvis/maps/blabla.cfg" % site.root
    dummy_map_filepath2 = "%s/etc/nagvis/maps/bloblo.cfg" % site.root
    try:
        open(dummy_map_filepath1, "w")
        open(dummy_map_filepath2, "w")

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
        os.unlink(dummy_map_filepath1)
        os.unlink(dummy_map_filepath2)


# TODO: Parameterize test for cme / non cme
@pytest.mark.parametrize(("group_type"), ["contact", "host", "service"])
def test_delete_group(web, group_type):
    group_id = "%s_testgroup_id" % group_type
    group_alias = "%s_testgroup_alias" % group_type
    try:
        attributes = {"alias": group_alias}

        if cmk_version.is_managed_edition():
            attributes["customer"] = "provider"

        web.add_group(group_type, group_id, attributes)
    finally:
        web.delete_group(group_type, group_id)


def test_get_all_users(web):
    users = {
        "klaus": {
            "alias": "mr. klaus",
            "pager": "99221199",
            "password": "1234"
        },
        "monroe": {
            "alias": "mr. monroe"
        }
    }
    expected_users = set(["cmkadmin", "automation"] + list(users.keys()))
    try:
        _response = web.add_htpasswd_users(users)
        all_users = web.get_all_users()
        assert not expected_users - set(all_users.keys())
    finally:
        web.delete_htpasswd_users(list(users.keys()))


def test_add_htpasswd_users(web):
    users = {
        "klaus": {
            "alias": "mr. klaus",
            "pager": "99221199",
            "password": "1234"
        },
        "monroe": {
            "alias": "mr. monroe"
        }
    }
    try:
        web.add_htpasswd_users(users)
    finally:
        web.delete_htpasswd_users(list(users.keys()))


def test_edit_htpasswd_users(web):
    users = {
        "klaus": {
            "alias": "mr. klaus",
            "pager": "99221199",
            "password": "1234"
        },
        "monroe": {
            "alias": "mr. monroe"
        }
    }
    try:
        web.add_htpasswd_users(users)
        web.edit_htpasswd_users({
            "monroe": {
                "set_attributes": {
                    "alias": "ms. monroe"
                }
            },
            "klaus": {
                "unset_attributes": ["pager"]
            }
        })
        all_users = web.get_all_users()
        assert not "pager" in all_users["klaus"]
        assert all_users["monroe"]["alias"] == "ms. monroe"
    finally:
        web.delete_htpasswd_users(list(users.keys()))


def test_discover_services(web):
    try:
        web.add_host("test-host-discovery", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.discover_services("test-host-discovery")
    finally:
        web.delete_host("test-host-discovery")


def test_bulk_discovery_start_with_empty_hosts(web):
    with pytest.raises(APIError, match="specify some host"):
        web.bulk_discovery_start({
            "hostnames": [],
        }, expect_error=True)


def test_bulk_discovery_unknown_host(web):
    with pytest.raises(APIError, match="does not exist"):
        web.bulk_discovery_start({
            "hostnames": ["nono"],
        }, expect_error=True)


def _wait_for_bulk_discovery_job(web):
    def job_completed():
        status = web.bulk_discovery_status()
        return status["job"]["state"] != "initialized" and status["is_active"] is False

    wait_until(job_completed, timeout=30, interval=1)


def test_bulk_discovery_start_with_defaults(web, local_test_hosts):
    result = web.bulk_discovery_start({
        "hostnames": ["test-host"],
    })
    assert result["started"] is True

    _wait_for_bulk_discovery_job(web)

    status = web.bulk_discovery_status()
    assert status["is_active"] is False
    assert status["job"]["state"] == "finished"
    assert "discovery successful" in status["job"]["result_msg"]
    assert "discovery started" in status["job"]["output"]
    assert "test-host: discovery successful" in status["job"]["output"]
    assert "63 added" in status["job"]["output"]
    assert "discovery successful" in status["job"]["output"]


def test_bulk_discovery_start_with_parameters(web, local_test_hosts):
    result = web.bulk_discovery_start({
        "hostnames": ["test-host"],
        "mode": "new",
        "use_cache": True,
        "do_scan": True,
        "bulk_size": 5,
        "ignore_single_check_errors": True,
    })
    assert result["started"] is True

    _wait_for_bulk_discovery_job(web)

    status = web.bulk_discovery_status()
    assert status["is_active"] is False
    assert status["job"]["state"] == "finished"


def test_bulk_discovery_start_multiple_with_subdir(web, local_test_hosts):
    result = web.bulk_discovery_start({
        "hostnames": ["test-host", "test-host2"],
        "mode": "new",
        "use_cache": True,
        "do_scan": True,
        "bulk_size": 5,
        "ignore_single_check_errors": True,
    })
    assert result["started"] is True

    _wait_for_bulk_discovery_job(web)

    status = web.bulk_discovery_status()
    assert status["is_active"] is False
    assert status["job"]["state"] == "finished"


def test_activate_changes(web, site):
    try:
        web.add_host("test-host-activate", attributes={
            "ipaddress": "127.0.0.1",
        })

        web.activate_changes()

        result = site.live.query("GET hosts\nColumns: name\nFilter: name = test-host-activate\n")
        assert result == [["test-host-activate"]]
    finally:
        web.delete_host("test-host-activate")
        web.activate_changes()


@pytest.fixture(scope="module")
def graph_test_config(web, site):
    # No graph yet...
    with pytest.raises(APIError) as exc_info:
        web.get_regular_graph("test-host-get-graph", "Check_MK", 0, expect_error=True)
        assert "Cannot calculate graph recipes" in "%s" % exc_info

    try:
        # Now add the host
        web.add_host("test-host-get-graph", attributes={
            "ipaddress": "127.0.0.1",
        })

        site.write_file(
            "etc/check_mk/conf.d/test-host-get-graph.mk",
            "datasource_programs.append(('cat ~/var/check_mk/agent_output/<HOST>', [], ['test-host-get-graph']))\n"
        )

        site.makedirs("var/check_mk/agent_output/")
        site.write_file("var/check_mk/agent_output/test-host-get-graph",
                        get_standard_linux_agent_output())

        web.discover_services("test-host-get-graph")
        web.activate_changes()
        site.schedule_check("test-host-get-graph", "Check_MK", 0)

        # Wait for RRD file creation. Isn't this a bug that the graph is not instantly available?
        rrd_path = site.path("var/check_mk/rrd/test-host-get-graph/Check_MK.rrd")
        for attempt in range(50):
            time.sleep(0.1)
            proc = subprocess.Popen([site.path("bin/unixcat"),
                                     site.path("tmp/run/rrdcached.sock")],
                                    stdin=subprocess.PIPE,
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,
                                    encoding="utf-8")
            out, err = proc.communicate("FLUSH %s\n" % rrd_path)
            if os.path.exists(rrd_path):
                break
            sys.stdout.write("waiting for %s (attempt %d)%s%s\n" % (
                rrd_path,
                attempt + 1,  #
                ", stdout: %s" % out if out else "",
                ", stderr: %s" % err if err else ""))
        else:
            assert False, "RRD file %s missing" % rrd_path

        yield
    finally:
        web.delete_host("test-host-get-graph")
        site.delete_file("etc/check_mk/conf.d/test-host-get-graph.mk")
    web.activate_changes()


def test_get_graph_api(web, graph_test_config):
    # Now we get a graph
    data = web.get_regular_graph("test-host-get-graph", "Check_MK", 0)

    assert len(data["curves"]) == 5
    assert data["curves"][0]["title"] == "CPU time in user space"
    assert data["curves"][1]["title"] == "CPU time in operating system"
    assert data["curves"][2]["title"] == "Time spent waiting for Check_MK agent"
    assert data["curves"][3]["title"] == "Time spent waiting for special agent"
    assert data["curves"][4]["title"] == "Total execution time"


def test_get_graph_image(web, graph_test_config):
    result = web.post("graph_image.py",
                      data={
                          "request": json.dumps({
                              "specification": [
                                  "template", {
                                      "service_description": "Check_MK",
                                      "site": web.site.id,
                                      "graph_index": 0,
                                      "host_name": "test-host-get-graph",
                                  }
                              ],
                          }),
                      })

    content = result.content

    assert content.startswith(b'\x89PNG')

    try:
        Image.open(BytesIO(content))
    except IOError:
        raise Exception("Failed to open image: %r" % content)


def test_get_graph_notification_image(web, graph_test_config):
    result = web.get("ajax_graph_images.py?host=test-host-get-graph&service=Check_MK")

    # Provides a json list containing base64 encoded PNG images of the current 24h graphs
    encoded_graph_list = json.loads(result.text)
    assert isinstance(encoded_graph_list, list)
    assert len(encoded_graph_list) > 0

    for encoded_graph_image in encoded_graph_list:
        graph_image = base64.b64decode(encoded_graph_image)

        assert graph_image.startswith(b'\x89PNG')

        try:
            Image.open(BytesIO(graph_image))
        except IOError:
            raise Exception("Failed to open image: %r" % graph_image)


def test_get_graph_hover(web, graph_test_config):
    graph_context = {
        u'definition': {
            u'explicit_vertical_range': [None, None],
            u'title': u'Time usage by phase',
            u'horizontal_rules': [],
            u'specification': [
                u'template', {
                    u'service_description': u'Check_MK',
                    u'site': web.site.id,
                    u'graph_index': 0,
                    u'host_name': u'test-host-get-graph'
                }
            ],
            u'consolidation_function': u'max',
            u'metrics': [{
                u'color': u'#87f058',
                u'line_type': u'stack',
                u'expression': [
                    u'operator', u'+',
                    [[
                        u'rrd', u'test-host-get-graph', u'test-host-get-graph', u'Check_MK',
                        u'user_time', None, 1
                    ],
                     [
                         u'rrd', u'test-host-get-graph', u'test-host-get-graph', u'Check_MK',
                         u'children_user_time', None, 1
                     ]]
                ],
                u'unit': u's',
                u'title': u'CPU time in user space'
            }, {
                u'color': u'#ff8840',
                u'line_type': u'stack',
                u'expression': [
                    u'operator', u'+',
                    [[
                        u'rrd', u'test-host-get-graph', u'test-host-get-graph', u'Check_MK',
                        u'system_time', None, 1
                    ],
                     [
                         u'rrd', u'test-host-get-graph', u'test-host-get-graph', u'Check_MK',
                         u'children_system_time', None, 1
                     ]]
                ],
                u'unit': u's',
                u'title': u'CPU time in operating system'
            }, {
                u'color': u'#00b2ff',
                u'line_type': u'stack',
                u'expression': [
                    u'rrd', u'test-host-get-graph', u'test-host-get-graph', u'Check_MK',
                    u'cmk_time_agent', None, 1
                ],
                u'unit': u's',
                u'title': u'Time spent waiting for Check_MK agent'
            }, {
                u'color': u'#d080af',
                u'line_type': u'line',
                u'expression': [
                    u'rrd', u'test-host-get-graph', u'test-host-get-graph', u'Check_MK',
                    u'execution_time', None, 1
                ],
                u'unit': u's',
                u'title': u'Total execution time'
            }],
            u'omit_zero_metrics': False,
            u'unit': u's'
        },
        u'graph_id': u'graph_0',
        u'data_range': {
            u'step': 20,
            u"time_range": [time.time() - 3600, time.time()]
        },
        u'render_options': {
            u'preview': False,
            u'editing': False,
            u'font_size': 8,
            u'show_graph_time': True,
            u'resizable': True,
            u'show_time_axis': True,
            u'fixed_timerange': False,
            u'foreground_color': u'#000000',
            u'title_format': u'plain',
            u'canvas_color': u'#ffffff',
            u'show_legend': True,
            u'interaction': True,
            u'show_time_range_previews': True,
            u'show_title': True,
            u'show_margin': True,
            u'vertical_axis_width': u'fixed',
            u'show_controls': True,
            u'show_pin': True,
            u'background_color': u'#f8f4f0',
            u'show_vertical_axis': True,
            u'size': [70, 16]
        }
    }

    result = web.post("ajax_graph_hover.py",
                      data={
                          "context": json.dumps(graph_context),
                          "hover_time": int(time.time() - 300),
                      })

    data = result.json()

    assert "rendered_hover_time" in data
    assert len(data["curve_values"]) == 4

    for index, metric in enumerate(graph_context["definition"]["metrics"][::-1]):
        curve_value = data["curve_values"][index]

        assert curve_value["color"] == metric["color"]
        assert curve_value["title"] == metric["title"]

        # TODO: Wait for first values?
        assert curve_value["rendered_value"][0] is None
        assert curve_value["rendered_value"][1] == "n/a"
        #assert isinstance(curve_value["rendered_value"][0], (int, float))
        #assert curve_value["rendered_value"][1] != ""


def test_get_inventory(web):
    host_name = "test-host"
    inventory_dir = "var/check_mk/inventory"
    try:
        web.add_host(host_name, attributes={"ipaddress": "127.0.0.1"})
        # NOTE: Deleting the host deletes the file, too.
        web.site.makedirs(inventory_dir)
        web.site.write_file(os.path.join(inventory_dir, host_name),
                            "{'hardware': {'memory': {'ram': 10000, 'foo': 1}, 'blubb': 42}}")

        inv = web.get_inventory([host_name])
        assert inv[host_name] == {
            u'hardware': {
                u'memory': {
                    u'foo': 1,
                    u'ram': 10000
                },
                u'blubb': 42
            }
        }

        inv = web.get_inventory([host_name], paths=['.hardware.memory.'])
        assert inv[host_name] == {u'hardware': {u'memory': {u'foo': 1, u'ram': 10000}}}

        inv = web.get_inventory([host_name], paths=['.hardware.mumpf.'])
        assert inv[host_name] == {}
    finally:
        web.delete_host(host_name)


def test_get_user_sites(web, graph_test_config):
    assert web.get_user_sites()[0][0] == web.site.id


def test_get_host_names(web, graph_test_config):
    assert "test-host-get-graph" in web.get_host_names(request={})


@pytest.mark.skip("the test is too strict, the indices are a random permutation of 0..2")
def test_get_metrics_of_host(web, graph_test_config):
    # Do not validate the whole response, just a sample entry
    response = web.get_metrics_of_host(request={"hostname": "test-host-get-graph"})
    assert response["CPU load"] == {
        u'check_command': u'check_mk-cpu.loads',
        u'metrics': {
            u'load1': {
                u'index': 1,
                u'name': u'load1',
                u'title': u'CPU load average of last minute'
            },
            u'load15': {
                u'index': 0,
                u'name': u'load15',
                u'title': u'CPU load average of last 15 minutes'
            },
            u'load5': {
                u'index': 2,
                u'name': u'load5',
                u'title': u'CPU load average of last 5 minutes'
            }
        },
    }


def test_get_graph_recipes(web, graph_test_config):
    assert web.get_graph_recipes(
        request={
            "specification": [
                "template", {
                    "service_description": "Check_MK",
                    "site": web.site.id,
                    "graph_index": 0,
                    "host_name": "test-host-get-graph",
                }
            ],
        }) == [
            {
                u'consolidation_function': u'max',
                u'explicit_vertical_range': [None, None],
                u'horizontal_rules': [],
                u'metrics': [{
                    u'color': u'#87f058',
                    u'expression': [
                        u'operator', u'+',
                        [[
                            u'rrd', web.site.id, u'test-host-get-graph', u'Check_MK', u'user_time',
                            None, 1.0
                        ],
                         [
                             u'rrd', web.site.id, u'test-host-get-graph', u'Check_MK',
                             u'children_user_time', None, 1.0
                         ]]
                    ],
                    u'line_type': u'stack',
                    u'title': u'CPU time in user space',
                    u'unit': u's'
                }, {
                    u'color': u'#ff8840',
                    u'expression': [
                        u'operator', u'+',
                        [[
                            u'rrd', web.site.id, u'test-host-get-graph', u'Check_MK',
                            u'system_time', None, 1.0
                        ],
                         [
                             u'rrd', web.site.id, u'test-host-get-graph', u'Check_MK',
                             u'children_system_time', None, 1.0
                         ]]
                    ],
                    u'line_type': u'stack',
                    u'title': u'CPU time in operating system',
                    u'unit': u's'
                }, {
                    u'color': u'#0093ff',
                    u'expression': [
                        u'rrd', web.site.id, u'test-host-get-graph', u'Check_MK', u'cmk_time_agent',
                        None, 1.0
                    ],
                    u'line_type': u'stack',
                    u'title': u'Time spent waiting for Check_MK agent',
                    u'unit': u's'
                }, {
                    u'color': u'#00d1ff',
                    u'expression': [
                        u'rrd', web.site.id, u'test-host-get-graph', u'Check_MK', u'cmk_time_ds',
                        None, 1.0
                    ],
                    u'line_type': u'stack',
                    u'title': u'Time spent waiting for special agent',
                    u'unit': u's'
                }, {
                    u'color': u'#d080af',
                    u'expression': [
                        u'rrd', web.site.id, u'test-host-get-graph', u'Check_MK', u'execution_time',
                        None, 1.0
                    ],
                    u'line_type': u'line',
                    u'title': u'Total execution time',
                    u'unit': u's'
                }],
                u'omit_zero_metrics': False,
                u'specification': [
                    u'template', {
                        u'graph_index': 0,
                        u'host_name': u'test-host-get-graph',
                        u'service_description': u'Check_MK',
                        u'site': web.site.id
                    }
                ],
                u'title': u'Time usage by phase',
                u'unit': u's'
            },
        ]


def test_get_combined_graph_identifications(web, graph_test_config):
    result = web.get_combined_graph_identifications(
        request={
            "single_infos": ["host"],
            "datasource": "services",
            "context": {
                "service": {
                    "service": "CPU load"
                },
                "site": {
                    "site": web.site.id
                },
                "host_name": "test-host-get-graph",
            },
        })

    assert result == [
        {
            u'identification': [
                u'combined', {
                    u'context': {
                        u'host_name': u'test-host-get-graph',
                        u'service': {
                            u'service': u'CPU load'
                        },
                        u'site': {
                            u'site': web.site.id,
                        }
                    },
                    u'datasource': u'services',
                    u'graph_template': u'cpu_load',
                    u'presentation': u'sum',
                    u'single_infos': [u'host']
                }
            ],
            u'title': u'CPU Load - %(load1:max@count) CPU Cores'
        },
    ]


def test_get_graph_annotations(web, graph_test_config):
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
                "host_name": "test-host-get-graph",
            },
            "start_time": start_time,
            "end_time": end_time,
        })

    assert len(result["availability_timelines"]) == 1
    assert result["availability_timelines"][0]["display_name"] == "CPU load"


def test_get_hosttags(web):
    host_tags = web.get_hosttags()
    assert isinstance(host_tags["configuration_hash"], str)
    assert host_tags["aux_tags"] == []

    assert isinstance(host_tags["tag_groups"], list)
    assert host_tags["tag_groups"][0]["id"] == "criticality"


def test_set_hosttags(web):
    original_host_tags = web.get_hosttags()

    location_tag_group = {
        'id': 'location',
        'tags': [{
            'aux_tags': [],
            'id': 'munich',
            'title': 'Munich'
        }, {
            'aux_tags': [],
            'id': 'essen',
            'title': 'Essen'
        }, {
            'aux_tags': [],
            'id': 'berlin',
            'title': 'Berlin'
        }],
        'title': 'Location',
    }
    host_tags = copy.deepcopy(original_host_tags)
    host_tags["tag_groups"].append(location_tag_group)

    try:
        web.set_hosttags(
            request={
                "aux_tags": host_tags["aux_tags"],
                "tag_groups": host_tags["tag_groups"],
                "configuration_hash": host_tags["configuration_hash"],
            })

        new_host_tags = web.get_hosttags()
        assert location_tag_group in new_host_tags["tag_groups"]
    finally:
        web.set_hosttags(request={
            "aux_tags": original_host_tags["aux_tags"],
            "tag_groups": original_host_tags["tag_groups"],
        })
