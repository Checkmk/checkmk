#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import Namespace
from types import ModuleType
from typing import Final, Mapping

import pytest

from tests.testlib.repo import repo_path

from cmk.plugins.gcp.special_agents import agent_gcp, agent_gcp_status
from cmk.special_agents import (
    agent_activemq,
    agent_alertmanager,
    agent_allnet_ip_sensoric,
    agent_aws,
    agent_aws_status,
    agent_azure,
    agent_azure_status,
    agent_cisco_meraki,
    agent_cisco_prime,
    agent_couchbase,
    agent_datadog,
    agent_elasticsearch,
    agent_fritzbox,
    agent_graylog,
    agent_hivemanager_ng,
    agent_innovaphone,
    agent_jenkins,
    agent_jira,
    agent_kube,
    agent_mobileiron,
    agent_mqtt,
    agent_netapp,
    agent_netapp_ontap,
    agent_prometheus,
    agent_proxmox_ve,
    agent_pure_storage_fa,
    agent_rabbitmq,
    agent_smb_share,
    agent_splunk,
    agent_storeonce4x,
    agent_vsphere,
)

TESTED_SA_MODULES: Final[Mapping[str, ModuleType | None]] = {
    "activemq": agent_activemq,
    "acme_sbc": None,  # not even python.
    "alertmanager": agent_alertmanager,
    "allnet_ip_sensoric": agent_allnet_ip_sensoric,
    "appdynamics": None,
    "aws": agent_aws,
    "aws_status": agent_aws_status,
    "azure": agent_azure,
    "azure_status": agent_azure_status,
    "bi": None,
    "cisco_meraki": agent_cisco_meraki,
    "cisco_prime": agent_cisco_prime,
    "couchbase": agent_couchbase,
    "datadog": agent_datadog,
    "ddn_s2a": None,
    "elasticsearch": agent_elasticsearch,
    "emcvnx": None,
    "fritzbox": agent_fritzbox,
    "gcp": agent_gcp,
    "gcp_status": agent_gcp_status,
    "graylog": agent_graylog,
    "hivemanager": None,
    "hivemanager_ng": agent_hivemanager_ng,
    "hp_msa": None,
    "ibmsvc": None,
    "innovaphone": agent_innovaphone,
    "ipmi_sensors": None,
    "jenkins": agent_jenkins,
    "jira": agent_jira,
    "jolokia": None,
    "kube": agent_kube,
    "mobileiron": agent_mobileiron,
    "mqtt": agent_mqtt,
    "netapp": agent_netapp,
    "netapp_ontap": agent_netapp_ontap,
    "prism": None,
    "prometheus": agent_prometheus,
    "proxmox_ve": agent_proxmox_ve,
    "pure_storage_fa": agent_pure_storage_fa,
    "rabbitmq": agent_rabbitmq,
    "random": None,
    "ruckus_spot": None,
    "salesforce": None,
    "siemens_plc": None,
    "smb_share": agent_smb_share,
    "splunk": agent_splunk,
    "storeonce4x": agent_storeonce4x,
    "storeonce": None,
    "tinkerforge": None,
    "ucs_bladecenter": None,
    "vnx_quotas": None,
    "vsphere": agent_vsphere,
    "zerto": None,
}

REQUIRED_ARGUMENTS: Final[Mapping[str, list[str]]] = {
    "alertmanager": [],
    "allnet_ip_sensoric": ["HOSTNAME"],
    "aws": [
        "--access-key-id",
        "ACCESS_KEY_ID",
        "--secret-access-key",
        "SECRET_ACCESS_KEY",
        "--hostname",
        "HOSTNAME",
        "--piggyback-naming-convention",
        "ip_region_instance",
    ],
    "azure": [
        "--authority",
        "global",
        "--subscription",
        "SUBSCRIPTION",
        "--client",
        "CLIENT",
        "--tenant",
        "TENANT",
        "--secret",
        "SECRET",
        "--cache-id",
        "HOSTNAME",
    ],
    "couchbase": ["HOSTNAME"],
    "elasticsearch": ["HOSTNAME"],
    "fritzbox": ["HOSTNAME"],
    "graylog": ["HOSTNAME"],
    "hivemanager": ["IP", "USER", "PASSWORD"],
    "hivemanager_ng": [
        "URL",
        "VHM_ID",
        "API_TOKEN",
        "CLIENT_ID",
        "CLIENT_SECRET",
        "REDIRECT_URL",
    ],
    "ibmsvc": ["HOSTNAME"],
    "jenkins": ["HOSTNAME"],
    "jira": [
        "-P",
        "PROTOCOL",
        "-u",
        "USER",
        "-s",
        "PASSWORD",
        "--hostname",
        "HOSTNAME",
    ],
    "kube": [
        "--cluster",
        "CLUSTER",
        "--token",
        "TOKEN",
        "--api-server-endpoint",
        "ENDPOINT",
        "--cluster-collector-endpoint",
        "ENDPOINT",
        "--kubernetes-cluster-hostname",
        "host",
    ],
    "prometheus": [],
    "rabbitmq": [
        "-P",
        "PROTOCOL",
        "-m",
        "SECTIONS",
        "-u",
        "USER",
        "-s",
        "PASSWORD",
        "--hostname",
        "HOSTNAME",
    ],
    "splunk": ["HOSTNAME"],
    "vsphere": ["HOSTNAME"],
    "proxmox_ve": ["HOSTNAME"],
    "mobileiron": ["--hostname", "HOSTNAME"],
    "storeonce4x": ["USER", "PASSWORD", "HOST"],
    "cisco_prime": ["--hostname", "HOSTNAME"],
    "innovaphone": [
        "User",
        "MyPass",
        "Hostname",
    ],
    "netapp": ["address", "user", "password"],
    "netapp_ontap": [
        "--hostname",
        "HOSTNAME",
        "--username",
        "USERNAME",
        "--password",
        "PASSWORD",
    ],
    "activemq": ["server", "1234"],
    "datadog": [
        "HOSTNAME",
        "API_KEY",
        "APP_KEY",
        "ADDRESS",
    ],
    "mqtt": ["SERVER"],
    "smb_share": [
        "REMOTE_NAME",
        "ADDRESS",
    ],
    "gcp": [
        "--project",
        "a",
        "--credentials",
        "foo",
        "--services",
        "gcs",
        "--piggy-back-prefix",
        "a",
    ],
    "cisco_meraki": ["HOSTNAME", "API_KEY"],
    "azure_status": ["REGION1 REGION2"],
    "aws_status": [],
    "gcp_status": [],
    "pure_storage_fa": ["--api-token", "API-TOKEN", "SERVER"],
}


def test_all_agents_tested() -> None:
    assert set(TESTED_SA_MODULES) == {
        agent_file.name.split("agent_")[-1]
        for agent_file in (repo_path() / "agents" / "special").glob("agent_*")
    }


@pytest.mark.parametrize(
    "name, module", [(n, m) for n, m in TESTED_SA_MODULES.items() if m is not None]
)
def test_parse_arguments(name: str, module: ModuleType) -> None:
    minimal_args_list = REQUIRED_ARGUMENTS[name]

    # Special agents should process their arguments in a function called parse_arguments
    parsed = module.parse_arguments(minimal_args_list)
    assert isinstance(parsed, Namespace)

    # Special agents should support the argument '--debug'
    assert parsed.debug is False
    # This also ensures that the parse_arguments function indeed expects
    # sys.argv[1:], and does not strip the first element of the input argument.
    assert module.parse_arguments(["--debug", *minimal_args_list]).debug is True
