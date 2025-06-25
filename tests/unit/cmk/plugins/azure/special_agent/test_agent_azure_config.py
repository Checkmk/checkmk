#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import logging
from collections.abc import Sequence

import pytest

from cmk.plugins.azure.special_agent.agent_azure import (
    Args,
    AzureResource,
    ExplicitConfig,
    parse_arguments,
    Selector,
    TagBasedConfig,
    TagsImportPatternOption,
)

ARGV = [
    "--authority",
    "global",
    "--tenant",
    "tenant-id",
    "--client",
    "client-id",
    "--secret",
    "secret",
    "--subscription",
    "subscription-id",
    "--piggyback_vms",
    "grouphost",
    "--services",
    "Microsoft.Compute/virtualMachines",
    "Microsoft.Storage/storageAccounts",
    "--explicit-config",
    "group=test-group",
    "resources=Resource1,Resource2",
    "--require-tag",
    "tag1",
    "--require-tag-value",
    "tag2",
    "value2",
    "--cache-id",
    "testhost",
]

ARGS = Args(
    debug=False,
    verbose=0,
    vcrtrace=False,
    dump_config=False,
    timeout=10,
    piggyback_vms="grouphost",
    authority="global",
    subscriptions=["subscription-id"],
    all_subscriptions=False,
    client="client-id",
    tenant="tenant-id",
    secret="secret",
    cache_id="testhost",
    proxy=None,
    require_tag=["tag1"],
    require_tag_value=[["tag2", "value2"]],
    explicit_config=["group=test-group", "resources=Resource1,Resource2"],
    services=["Microsoft.Compute/virtualMachines", "Microsoft.Storage/storageAccounts"],
    tag_key_pattern=TagsImportPatternOption.import_all,
    connection_test=False,
)


@pytest.mark.parametrize(
    "argv,args,expected_log",
    [
        (
            ARGV,
            ARGS,
            [
                "argparse: debug = False",
                "argparse: verbose = 0",
                "argparse: vcrtrace = False",
                "argparse: dump_config = False",
                "argparse: timeout = 10",
                "argparse: piggyback_vms = 'grouphost'",
                "argparse: subscriptions = ['subscription-id']",
                "argparse: all_subscriptions = False",
                "argparse: client = 'client-id'",
                "argparse: tenant = 'tenant-id'",
                "argparse: secret = '****'",
                "argparse: cache_id = 'testhost'",
                "argparse: proxy = None",
                "argparse: require_tag = ['tag1']",
                "argparse: require_tag_value = [['tag2', 'value2']]",
                "argparse: explicit_config = ['group=test-group', 'resources=Resource1,Resource2']",
                "argparse: services = ['Microsoft.Compute/virtualMachines', 'Microsoft.Storage/storageAccounts']",
                "argparse: authority = 'global'",
                "argparse: tag_key_pattern = <TagsImportPatternOption.import_all: 'IMPORT_ALL'>",
                "argparse: connection_test = False",
            ],
        ),
    ],
)
def test_parse_arguments(
    argv: Sequence[str],
    args: Args,
    expected_log: Sequence[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.DEBUG)
    assert parse_arguments(argv) == args
    assert caplog.messages == expected_log


@pytest.mark.parametrize(
    "config,error_type,error_message",
    [
        pytest.param(
            ["group"],
            ValueError,
            "must be in <key>=<value> format: 'group'",
            id="incorrect explicit config format",
        ),
        pytest.param(["group="], ValueError, "falsey group name: ''", id="incorrect group name"),
        pytest.param(
            ["group=test-group", "unknown=Resource1,Resource2"],
            ValueError,
            "unknown config key: unknown",
            id="incorrect config key",
        ),
        pytest.param(
            ["resources=Resource1,Resource2"],
            RuntimeError,
            "missing arg: group=<name>",
            id="missing group key",
        ),
    ],
)
def test_explicit_config_incorrect_config(
    config: Sequence[str], error_type: type[Exception], error_message: str
) -> None:
    with pytest.raises(error_type, match=error_message):
        ExplicitConfig(config)


@pytest.mark.parametrize(
    "config,config_string",
    [([], "[<fetchall>]"), (["group=test-group"], "[test-group]\n  <fetchall>")],
)
def test_explicit_config(config: Sequence[str], config_string: str) -> None:
    explicit_config = ExplicitConfig(config)
    assert str(explicit_config) == config_string


@pytest.mark.parametrize(
    "config,resource,is_monitored",
    [
        pytest.param(
            ["group=test-group", "resources=Resource1,Resource2"],
            AzureResource(
                {
                    "id": "id3",
                    "name": "Resource3",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {},
                    "group": "my-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            False,
            id="resource not in config",
        ),
        pytest.param(
            [],
            AzureResource(
                {
                    "id": "id",
                    "name": "Resource",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {},
                    "group": "my-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            True,
            id="no explicit config",
        ),
        pytest.param(
            ["group=test-group"],
            AzureResource(
                {
                    "id": "id",
                    "name": "Resource",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {},
                    "group": "test-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            True,
            id="no resources in explicit config",
        ),
    ],
)
def test_explicit_config_is_configured(
    config: Sequence[str], resource: AzureResource, is_monitored: bool
) -> None:
    explicit_config = ExplicitConfig(config)
    assert explicit_config.is_configured(resource) == is_monitored


@pytest.mark.parametrize(
    "required_tags,required_tag_values,resource,is_monitored",
    [
        pytest.param(
            ["tag1"],
            [],
            AzureResource(
                {
                    "id": "id",
                    "name": "Resource",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {},
                    "group": "my-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            False,
            id="no required tag",
        ),
        pytest.param(
            ["tag1"],
            [["tag2", "value2"]],
            AzureResource(
                {
                    "id": "id",
                    "name": "Resource",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {"tag1": "value56", "tag2": "value57"},
                    "group": "my-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            False,
            id="tag value doesn't match",
        ),
    ],
)
def test_tag_based_config_is_configured(
    required_tags: Sequence[str],
    required_tag_values: Sequence[Sequence[str]],
    resource: AzureResource,
    is_monitored: bool,
) -> None:
    tag_config = TagBasedConfig(required_tags, required_tag_values)
    assert tag_config.is_configured(resource) == is_monitored


def test_selector() -> None:
    selector = Selector(ARGS)
    assert str(selector) == (
        "Explicit configuration:\n"
        "  [test-group]\n"
        "  resource: Resource1\n"
        "  resource: Resource2\n"
        "Tag based configuration:\n"
        "  required tags: tag1\n"
        "  required value for 'tag2': 'value2'"
    )


@pytest.mark.parametrize(
    "args,resource,is_monitored",
    [
        pytest.param(
            ARGS,
            AzureResource(
                {
                    "id": "id1",
                    "name": "Resource1",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {"tag1": "value1", "tag2": "value2", "mytag": "True"},
                    "group": "test-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            True,
            id="both explicit config and tag match",
        ),
        pytest.param(
            ARGS,
            AzureResource(
                {
                    "id": "id2",
                    "name": "Resource2",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {"tag3": "value3"},
                    "group": "test-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            False,
            id="tag doesn't match",
        ),
        pytest.param(
            ARGS,
            AzureResource(
                {
                    "id": "id3",
                    "name": "Resource3",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {"tag1": "value1", "tag2": "value2"},
                    "group": "test-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            False,
            id="explicit config doesn't match, unknown resource",
        ),
        pytest.param(
            ARGS,
            AzureResource(
                {
                    "id": "id1",
                    "name": "Resource1",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {"tag1": "value1", "tag2": "value2", "mytag": "True"},
                    "group": "test-group",
                },
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            True,
            id="group name in different case",
        ),
    ],
)
def test_selector_do_monitor(args: Args, resource: AzureResource, is_monitored: bool) -> None:
    selector = Selector(args)
    assert selector.do_monitor(resource) == is_monitored
