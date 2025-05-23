#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from argparse import Namespace
from collections.abc import Mapping
from types import ModuleType
from typing import Final

import pytest

from cmk.ccc import version as checkmk_version

from cmk.utils import password_store

from cmk.discover_plugins import family_libexec_dir
from cmk.plugins.activemq.special_agent import agent_activemq
from cmk.plugins.alertmanager.special_agents import agent_alertmanager
from cmk.plugins.allnet_ip_sensoric.special_agent import agent_allnet_ip_sensoric
from cmk.plugins.aws.special_agent import agent_aws, agent_aws_status
from cmk.plugins.azure.special_agent import agent_azure, agent_azure_status
from cmk.plugins.bazel.lib import agent as agent_bazel
from cmk.plugins.checkmk.special_agents import agent_bi
from cmk.plugins.cisco.special_agent import agent_cisco_prime
from cmk.plugins.cisco_meraki.special_agent import agent_cisco_meraki
from cmk.plugins.couchbase.special_agent import agent_couchbase
from cmk.plugins.datadog.special_agent import agent_datadog
from cmk.plugins.elasticsearch.special_agent import agent_elasticsearch
from cmk.plugins.fritzbox.lib import agent as agent_fritzbox
from cmk.plugins.gcp.special_agents import agent_gcp, agent_gcp_status
from cmk.plugins.gerrit.lib import agent as agent_gerrit
from cmk.plugins.graylog.special_agent import agent_graylog
from cmk.plugins.hivemanager_ng.special_agent import agent_hivemanager_ng
from cmk.plugins.innovaphone.special_agent import agent_innovaphone
from cmk.plugins.jenkins.lib import jenkins as agent_jenkins
from cmk.plugins.jira.special_agent import agent_jira
from cmk.plugins.kube.special_agents import agent_kube
from cmk.plugins.mobileiron.special_agent import agent_mobileiron
from cmk.plugins.mqtt.special_agent import agent_mqtt
from cmk.plugins.netapp.special_agent import agent_netapp_ontap
from cmk.plugins.prometheus.special_agents import agent_prometheus
from cmk.plugins.proxmox_ve.special_agent import agent_proxmox_ve
from cmk.plugins.pure_storage_fa.special_agent import agent_pure_storage_fa
from cmk.plugins.rabbitmq.special_agent import agent_rabbitmq
from cmk.plugins.redfish.special_agents import agent_redfish, agent_redfish_power
from cmk.plugins.smb.special_agent import agent_smb_share
from cmk.plugins.splunk.special_agent import agent_splunk
from cmk.plugins.storeonce4x.special_agent import agent_storeonce4x
from cmk.server_side_calls_backend import load_special_agents

agent_otel: ModuleType | None = None
try:
    from cmk.plugins.otel.special_agents.cce import (  # type: ignore[import-untyped,no-redef,unused-ignore]
        agent_otel,
    )
except ImportError:
    pass


TESTED_SA_MODULES: Final[Mapping[str, ModuleType | None]] = {
    "three_par": None,
    "activemq": agent_activemq,
    "acme_sbc": None,  # not even python.
    "alertmanager": agent_alertmanager,
    "allnet_ip_sensoric": agent_allnet_ip_sensoric,
    "appdynamics": None,
    "aws": agent_aws,
    "aws_status": agent_aws_status,
    "azure": agent_azure,
    "azure_status": agent_azure_status,
    "bazel_cache": agent_bazel,
    "bi": agent_bi,
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
    "gerrit": agent_gerrit,
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
    "mobileiron": agent_mobileiron,
    "mqtt": agent_mqtt,
    "netapp_ontap": agent_netapp_ontap,
    **({} if agent_otel is None else {"otel": agent_otel}),
    "prism": None,
    "proxmox_ve": agent_proxmox_ve,
    "pure_storage_fa": agent_pure_storage_fa,
    "rabbitmq": agent_rabbitmq,
    "random": None,
    "redfish": agent_redfish,
    "redfish_power": agent_redfish_power,
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
    "zerto": None,
    "prometheus": agent_prometheus,
    "vsphere": None,
    "kube": agent_kube,
}


REQUIRED_ARGUMENTS: Final[Mapping[str, list[str]]] = {
    "alertmanager": ["--config", "{}"],
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
    "bi": [],
    "couchbase": ["HOSTNAME"],
    "elasticsearch": ["HOSTNAME"],
    "fritzbox": ["HOSTNAME"],
    "gerrit": ["--user", "USER", "--password", "PASSWORD", "HOSTNAME"],
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
    "jira": ["-P", "PROTOCOL", "-u", "USER", "-s", "PASSWORD", "--hostname", "HOSTNAME"],
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
    "prometheus": ["--config", "{}"],
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
    "redfish": ["--user", "USER", "--password", "sw0rdfis4", "HOSTNAME"],
    "redfish_power": ["--user", "USER", "--password", "sw0rdfis4", "HOSTNAME"],
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
    "netapp_ontap": ["--hostname", "HOSTNAME", "--username", "USERNAME", "--password", "PASSWORD"],
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
    "cisco_meraki": ["HOSTNAME", "--apikey-reference", "API_KEY"],
    "azure_status": ["REGION1 REGION2"],
    "aws_status": [],
    "gcp_status": [],
    "pure_storage_fa": ["--api-token", "API-TOKEN", "SERVER"],
    "bazel_cache": ["--host", "SERVER"],
    "otel": ["HOSTNAME"],
}


def test_all_agents_considered() -> None:
    """Make sure our test cases are up to date

    Compare the hard coded agent map `TESTED_SA_MODULES` to the
    set of agent configurable via WATO, and make sure we cover them.
    """
    configurable_special_agents = {
        plugin.name for plugin in load_special_agents(raise_errors=True).values()
    }
    assert set(TESTED_SA_MODULES) == configurable_special_agents


def test_all_agents_versions() -> None:
    """Ensure the agents `__version__` is up to date, if present."""
    version_mismatch = {
        module.__name__
        for module in TESTED_SA_MODULES.values()
        # not having the __version__ is ok, but if present it must match
        if module
        and hasattr(module, "__version__")
        and module.__version__ != checkmk_version.__version__
    }
    assert not version_mismatch


@pytest.mark.parametrize(
    "name, module", [(n, m) for n, m in TESTED_SA_MODULES.items() if m is not None]
)
def test_parse_arguments(monkeypatch: pytest.MonkeyPatch, name: str, module: ModuleType) -> None:
    monkeypatch.setattr(password_store, "lookup", lambda x: x)
    minimal_args_list = REQUIRED_ARGUMENTS[name]

    # Special agents should process their arguments in a function called parse_arguments
    parsed = module.parse_arguments(minimal_args_list)
    assert isinstance(parsed, Namespace)

    # Special agents should support the argument '--debug'
    assert parsed.debug is False
    # This also ensures that the parse_arguments function indeed expects
    # sys.argv[1:], and does not strip the first element of the input argument.
    assert module.parse_arguments(["--debug", *minimal_args_list]).debug is True


def test_special_agents_location() -> None:
    """Make sure all executables are where we expect them"""
    assert all(
        (family_libexec_dir(location.module) / f"agent_{plugin.name}").exists()
        for location, plugin in load_special_agents(raise_errors=True).items()
    )


@pytest.mark.parametrize(
    "module",
    [m for m in TESTED_SA_MODULES.values() if m is not None],
)
def test_user_agent_string(module: ModuleType) -> None:
    try:
        user_agent = module.USER_AGENT
    except AttributeError:
        return
    assert user_agent.startswith("checkmk-special-")
    assert user_agent.endswith(f"-{checkmk_version.__version__}")
