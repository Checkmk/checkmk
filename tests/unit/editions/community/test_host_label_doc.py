#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Test the documentation of the host label functions."""

from typing import Final

from tests.unit.editions.lib.extract_shipped_host_labels import extract_shipped_host_labels

DOCUMENTED_BUILTIN_HOST_LABELS: Final = {
    "cmk/site",
    "cmk/customer",
    "cmk/aws/tag/{key}:{value}",
    "cmk/azure/entity:<entity_type>",
    "cmk/azure/entity:resource_group",
    "cmk/azure/entity:subscription",
    "cmk/azure/entity:tenant",
    "cmk/azure/name",
    "cmk/azure/region:<region>",
    "cmk/azure/resource_group",
    "cmk/azure/subscription_id",
    "cmk/azure/subscription_name",
    "cmk/azure/tag/{key}:{value}",  # deprecated azure plugin
    "cmk/azure/tag/{label}:{value}",
    "cmk/azure/vm:instance",
    "cmk/ceph/mon",
    "cmk/ceph/osd",
    "cmk/check_mk_server",
    "cmk/cloud:azure",
    "cmk/device_model",
    "cmk/device_type",
    "cmk/docker_image",
    "cmk/docker_image_name",
    "cmk/docker_image_version",
    "cmk/docker_object:container",
    "cmk/docker_object:node",
    "cmk/has_cdp_neighbors",
    "cmk/has_lldp_neighbors",
    "cmk/kubernetes",
    "cmk/kubernetes/annotation/{key}:{value}",
    "cmk/kubernetes/cluster",
    "cmk/kubernetes/cluster-host",
    "cmk/kubernetes/cronjob",
    "cmk/kubernetes/daemonset",
    "cmk/kubernetes/deployment",
    "cmk/kubernetes/namespace",
    "cmk/kubernetes/node",
    "cmk/kubernetes/object",
    "cmk/kubernetes/statefulset",
    "cmk/l3v4_topology",
    "cmk/l3v6_topology",
    "cmk/meraki",
    "cmk/meraki/device_type",
    "cmk/meraki/has_lldp_neighbors",
    "cmk/meraki/net_id",
    "cmk/meraki/net_name",
    "cmk/meraki/org_id",
    "cmk/meraki/org_name",
    "cmk/nutanix/object",
    "cmk/os_family",
    "cmk/os_name",
    "cmk/os_platform",
    "cmk/os_type",
    "cmk/os_version",
    "cmk/podman/host",
    "cmk/podman/object:container",
    "cmk/podman/object:node",
    "cmk/podman/pod:{pod}",
    "cmk/podman/user:{user}",
    "cmk/pve/cluster:<cluster_name>",
    "cmk/pve/entity:<entity_type>",
    "cmk/pve/entity:node",
    "cmk/pve/tag/<tag>:yes",
    "cmk/systemd/unit/{name}:yes",
    "cmk/veeam_vbr/edition",
    "cmk/veeam_vbr/platform",
    "cmk/vsphere_object",
    "cmk/vsphere_vcenter",
}


def test_all_sections_have_host_labels_documented() -> None:
    """Test that all sections have documented their host labels"""
    assert set(extract_shipped_host_labels()) == DOCUMENTED_BUILTIN_HOST_LABELS


def test_builtin_labels_start_with_cmk() -> None:
    assert all(l.startswith("cmk/") for l in DOCUMENTED_BUILTIN_HOST_LABELS)
