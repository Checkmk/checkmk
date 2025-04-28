#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping, Sequence

import pytest

from cmk.plugins.vsphere.special_agent import agent_vsphere

DEFAULT_AGRS = {
    "debug": False,
    "direct": False,
    "timeout": 60,
    "port": 443,
    "hostname": None,
    "skip_placeholder_vm": False,
    "host_pwr_display": "host",
    "vm_pwr_display": "host",
    "snapshots_on_host": False,
    "vm_piggyname": "alias",
    "spaces": "underscore",
    "no_cert_check": False,
    "modules": ["hostsystem", "virtualmachine", "datastore", "counters", "licenses"],
    "host_address": "test_host",
    "user": None,
    "secret": None,
}


@pytest.mark.parametrize(
    "argv, expected_non_default_args",
    [
        ([], {}),
        (["--debug"], {"debug": True}),
        (["--direct"], {"direct": True}),
        (["-D"], {"direct": True}),
        (["--timeout", "23"], {"timeout": 23}),
        (["-t", "23"], {"timeout": 23}),
        (["--port", "80"], {"port": 80}),
        (["-p", "80"], {"port": 80}),
        (["--hostname", "myHost"], {"hostname": "myHost"}),
        (["-H", "myHost"], {"hostname": "myHost"}),
        (["-P"], {"skip_placeholder_vm": True}),
        (["--host_pwr_display", "vm"], {"host_pwr_display": "vm"}),
        (["--vm_pwr_display", "esxhost"], {"vm_pwr_display": "esxhost"}),
        (["--snapshots-on-host"], {"snapshots_on_host": True}),
        (["--vm_piggyname", "hostname"], {"vm_piggyname": "hostname"}),
        (["--spaces", "underscore"], {"spaces": "underscore"}),
        (["-S", "cut"], {"spaces": "cut"}),
        (["--no-cert-check"], {"no_cert_check": True}),
        (["--modules", "are,not,vectorspaces"], {"modules": ["are", "not", "vectorspaces"]}),
        (["-i", "are,not,vectorspaces"], {"modules": ["are", "not", "vectorspaces"]}),
        (["--user", "hi-its-me"], {"user": "hi-its-me"}),
        (["-u", "hi-its-me"], {"user": "hi-its-me"}),
        (
            ["--secret", "I like listening to Folk music"],
            {"secret": "I like listening to Folk music"},
        ),
        (["-s", "I like listening to Folk music"], {"secret": "I like listening to Folk music"}),
    ],
)
def test_parse_arguments(
    argv: Sequence[str], expected_non_default_args: Mapping[str, object]
) -> None:
    args = agent_vsphere.parse_arguments([*argv, "test_host"])
    for attr, value in DEFAULT_AGRS.items():
        expected = expected_non_default_args.get(attr, value)
        actual = getattr(args, attr)
        assert actual == expected


@pytest.mark.parametrize(
    "invalid_argv",
    [
        [],
        ["--tracefile", "wrongly_interpreted_as_host_address"],
        ["--spaces", "safe"],
        ["--host_pwr_display", "whoopdeedoo"],
        ["--vm_pwr_display", "whoopdeedoo"],
        ["--vm_piggyname", "MissPiggy"],
    ],
)
def test_parse_arguments_invalid(
    invalid_argv: Sequence[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        "cmk.special_agents.v0_unstable.misc.vcrtrace", lambda **vcr_init_kwargs: None
    )
    with pytest.raises(SystemExit):
        agent_vsphere.parse_arguments(invalid_argv)
