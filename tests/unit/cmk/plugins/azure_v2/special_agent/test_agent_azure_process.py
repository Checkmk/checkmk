#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="misc"
# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="type-arg"


import argparse
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import (
    _collect_resources,
    _get_resource_health_sections,
    _parse_metrics_metadata,
    AzureResource,
    AzureResourceGroup,
    AzureSubscription,
    filter_tags,
    get_resource_groups,
    get_resource_host_labels_section,
    process_app_registrations,
    process_organization,
    process_users,
    ResourceHealth,
    Selector,
    TagsImportPatternOption,
    TagsOption,
    write_group_info,
    write_remaining_reads,
    write_resource_groups_sections,
    write_subscription_section,
)

from .lib import fake_azure_subscription, MockAzureSection

Args = argparse.Namespace


@pytest.mark.parametrize(
    "resource, group_tags, expected_result",
    [
        pytest.param(
            AzureResource(
                {
                    "id": "myid",
                    "name": "MyVM",
                    "type": "Microsoft.Compute/virtualMachines",
                    "location": "westeurope",
                    "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                    "group": "BurningMan",
                },
                TagsImportPatternOption.import_all,
                subscription=fake_azure_subscription(),
                use_safe_names=False,
            ),
            {
                "burningman": AzureResourceGroup(
                    info={
                        "tags": {
                            "my-resource-tag": "my-resource-value",
                            "resource_group": "burningman",
                        },
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "burningman",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                )
            },
            (
                [
                    '{"cloud": "azure", "resource_group": "burningman", "resource": "virtualmachines", "entity": "resource", "subscription_name": "mock_subscription_name",'
                    ' "subscription": "mock_subscription_id", "region": "westeurope"}\n',
                    '{"my-unique-tag": "unique", "tag4all": "True", "my-resource-tag": "my-resource-value", "resource_group": "burningman"}\n',
                ],
                ["MyVM"],
            ),
            id="Virtual machine with resource group tags",
        ),
        pytest.param(
            AzureResource(
                {
                    "id": "resource_id",
                    "name": "my_resource",
                    "type": "Microsoft.Network/loadBalancers",
                    "location": "westeurope",
                    "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                    "group": "resource_group_name",
                },
                TagsImportPatternOption.import_all,
                subscription=fake_azure_subscription(),
                use_safe_names=False,
            ),
            {
                "resource_group_name": AzureResourceGroup(
                    info={
                        "tags": {
                            "resource_group": "resource_group_name",
                            "another_group_tag": "another_value",
                        },
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "resource_group_name",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                )
            },
            (
                [
                    '{"cloud": "azure", "resource_group": "resource_group_name", "resource": "loadbalancers", "entity": "resource", "subscription_name": "mock_subscription_name",'
                    ' "subscription": "mock_subscription_id", "region": "westeurope"}\n',
                    '{"my-unique-tag": "unique", "tag4all": "True", "resource_group": "resource_group_name", "another_group_tag": "another_value"}\n',
                ],
                ["my_resource"],
            ),
            id="Load balancer with resource and group tags",
        ),
        pytest.param(
            AzureResource(
                {
                    "id": "resource_id",
                    "name": "my_resource",
                    "type": "Microsoft.Network/loadBalancers",
                    "location": "westeurope",
                    "tags": {},
                    "group": "resource_group_name",
                },
                TagsImportPatternOption.import_all,
                subscription=fake_azure_subscription(),
                use_safe_names=False,
            ),
            {
                "resource_group_name": AzureResourceGroup(
                    info={
                        "tags": {},
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "resource_group_name",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                )
            },
            (
                [
                    '{"cloud": "azure", "resource_group": "resource_group_name", "resource": "loadbalancers", "entity": "resource", "subscription_name": "mock_subscription_name",'
                    ' "subscription": "mock_subscription_id", "region": "westeurope"}\n',
                    "{}\n",
                ],
                ["my_resource"],
            ),
            id="Load balancer with empty tags",
        ),
        pytest.param(
            AzureResource(
                {
                    "id": "resource_id",
                    "name": "my_resource",
                    "type": "Microsoft.Network/loadBalancers",
                    "location": "westeurope",
                    "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                    "group": "resource_group_name",
                },
                TagsImportPatternOption.import_all,
                subscription=fake_azure_subscription(use_safe_names=True),
                use_safe_names=True,
            ),
            {
                "resource_group_name": AzureResourceGroup(
                    info={
                        "tags": {
                            "resource_group": "resource_group_name",
                            "another_group_tag": "another_value",
                        },
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "resource_group_name",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(use_safe_names=True),
                    use_safe_names=True,
                )
            },
            (
                [
                    '{"cloud": "azure", "resource_group": "resource_group_name", "resource": "loadbalancers", "entity": "resource", "subscription_name": "mock_subscription_name",'
                    ' "subscription": "mock_subscription_id", "region": "westeurope"}\n',
                    '{"my-unique-tag": "unique", "tag4all": "True", "resource_group": "resource_group_name", "another_group_tag": "another_value"}\n',
                ],
                ["my_resource_6c554708"],
            ),
            id="Load balancer with safe hostnames",
        ),
    ],
)
def test_get_resource_host_labels_section(
    resource: AzureResource,
    group_tags: Mapping[str, AzureResourceGroup],
    expected_result: tuple[Sequence[str], Sequence[str]],
) -> None:
    labels_section = get_resource_host_labels_section(resource, group_tags)

    assert labels_section._cont == expected_result[0]
    assert labels_section._piggytargets == expected_result[1]


@pytest.mark.parametrize(
    "resource_info, custom_labels, group_tags, expected_labels_line",
    [
        pytest.param(
            {
                "id": "cosmos_id",
                "name": "my_cosmos_db",
                "type": "Microsoft.DocumentDB/databaseAccounts",
                "location": "eastus",
                "tags": {},
                "group": "cosmos_group",
            },
            {"cosmosdb_account": "my_cosmos_db"},
            {
                "cosmos_group": AzureResourceGroup(
                    info={
                        "tags": {},
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "cosmos_group",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                )
            },
            '{"cloud": "azure", "resource_group": "cosmos_group", "resource": "databaseaccounts", "entity": "resource", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "region": "eastus", "cosmosdb_account": "my_cosmos_db"}\n',
            id="CosmosDB account with cosmosdb_account label",
        ),
        pytest.param(
            {
                "id": "vm_id",
                "name": "my_vm",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "westeurope",
                "tags": {},
                "group": "vm_group",
            },
            {"vm_instance": True},
            {
                "vm_group": AzureResourceGroup(
                    info={
                        "tags": {},
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "vm_group",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                )
            },
            '{"cloud": "azure", "resource_group": "vm_group", "resource": "virtualmachines", "entity": "resource", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "region": "westeurope", "vm_instance": true}\n',
            id="Virtual machine with vm_instance label",
        ),
    ],
)
def test_resource_with_custom_labels(
    resource_info: Mapping[str, str],
    custom_labels: Mapping[str, str | bool],
    group_tags: Mapping[str, AzureResourceGroup],
    expected_labels_line: str,
) -> None:
    resource = AzureResource(
        dict(resource_info),
        TagsImportPatternOption.import_all,
        subscription=fake_azure_subscription(),
        use_safe_names=False,
    )
    resource.labels.update(custom_labels)

    labels_section = get_resource_host_labels_section(resource, group_tags)
    assert labels_section._cont[0] == expected_labels_line
    assert labels_section._piggytargets == [resource.piggytarget]


RESOURCE_GROUPS_RESPONSE = [
    {
        "id": "/subscriptions/subscripion_id/resourceGroups/resource_group_1",
        "name": "resource_group_1",
        "type": "Microsoft.Resources/resourceGroups",
        "location": "eastus",
        "managedBy": "subscriptions/subscripion_id/providers/Microsoft.RecoveryServices/",
        "properties": {"provisioningState": "Succeeded"},
        "tags": {"group_tag_key_1": "group_tag_value_1"},
    },
    {
        "id": "/subscriptions/subscripion_id/resourceGroups/resource_group_2",
        "name": "resource_group_2",
        "type": "Microsoft.Resources/resourceGroups",
        "location": "westeurope",
        "properties": {"provisioningState": "Succeeded"},
        "tags": {"group_tag_key_2": "group_tag_value_2"},
    },
]


@pytest.mark.parametrize(
    "monitored_groups, args, expected_result",
    [
        pytest.param(
            ["resource_group_non_existent"],
            Args(
                tag_key_pattern=TagsImportPatternOption.import_all,
                safe_hostnames=False,
            ),
            {},
            id="No labels monitored",
        ),
        pytest.param(
            ["resource_group_1"],
            Args(
                tag_key_pattern=TagsImportPatternOption.import_all,
                safe_hostnames=False,
            ),
            {"resource_group_1": {"group_tag_key_1": "group_tag_value_1"}},
            id="Labels monitored, import all tags",
        ),
        pytest.param(
            ["resource_group_1", "resource_group_2"],
            Args(
                tag_key_pattern=TagsImportPatternOption.ignore_all,
                safe_hostnames=False,
            ),
            {"resource_group_1": {}, "resource_group_2": {}},
            id="Labels monitored, ignore tags",
        ),
        pytest.param(
            ["resource_group_1", "resource_group_2"],
            Args(
                tag_key_pattern="group_tag",
                safe_hostnames=False,
            ),
            {
                "resource_group_1": {"group_tag_key_1": "group_tag_value_1"},
                "resource_group_2": {"group_tag_key_2": "group_tag_value_2"},
            },
            id="Labels monitored with pattern for tags",
        ),
        pytest.param(
            ["resource_group_1", "resource_group_2"],
            Args(
                tag_key_pattern="groups_tag",
                safe_hostnames=False,
            ),
            {"resource_group_1": {}, "resource_group_2": {}},
            id="Labels monitored with not matching pattern for tags",
        ),
        pytest.param(
            ["resource_group_1"],
            Args(
                tag_key_pattern=TagsImportPatternOption.import_all,
                safe_hostnames=True,
            ),
            {"resource_group_1": {"group_tag_key_1": "group_tag_value_1"}},
            id="Labels monitored, import all tags, safe names",
        ),
    ],
)
@pytest.mark.asyncio
async def test_group_labels(
    monitored_groups: Sequence[str],
    args: Args,
    expected_result: Mapping[str, Mapping[str, str]],
    mock_api_client: AsyncMock,
) -> None:
    mock_api_client.get_async.return_value = RESOURCE_GROUPS_RESPONSE

    groups = await get_resource_groups(
        mock_api_client, monitored_groups, fake_azure_subscription(), args
    )

    len(groups) == len(expected_result)
    for group_name, group in groups.items():
        assert group_name in expected_result
        assert group.tags == expected_result[group_name]


@pytest.mark.parametrize(
    "monitored_groups, expected_result",
    [
        pytest.param(
            ["resource_group_non_existent"],
            {},
            id="No groups monitored",
        ),
        pytest.param(
            ["resource_group_1"],
            {
                "resource_group_1": AzureResourceGroup(
                    info={
                        "id": "/subscriptions/subscripion_id/resourceGroups/resource_group_1",
                        "location": "eastus",
                        "managedBy": "subscriptions/subscripion_id/providers/Microsoft.RecoveryServices/",
                        "name": "resource_group_1",
                        "properties": {
                            "provisioningState": "Succeeded",
                        },
                        "tags": {
                            "group_tag_key_1": "group_tag_value_1",
                        },
                        "type": "Microsoft.Resources/resourceGroups",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                ),
            },
            id="One group monitored",
        ),
        pytest.param(
            ["resource_group_1", "resource_group_2"],
            {
                "resource_group_1": AzureResourceGroup(
                    info={
                        "id": "/subscriptions/subscripion_id/resourceGroups/resource_group_1",
                        "location": "eastus",
                        "managedBy": "subscriptions/subscripion_id/providers/Microsoft.RecoveryServices/",
                        "name": "resource_group_1",
                        "properties": {
                            "provisioningState": "Succeeded",
                        },
                        "tags": {
                            "group_tag_key_1": "group_tag_value_1",
                        },
                        "type": "Microsoft.Resources/resourceGroups",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                ),
                "resource_group_2": AzureResourceGroup(
                    info={
                        "id": "/subscriptions/subscripion_id/resourceGroups/resource_group_2",
                        "location": "westeurope",
                        "name": "resource_group_2",
                        "properties": {
                            "provisioningState": "Succeeded",
                        },
                        "tags": {
                            "group_tag_key_2": "group_tag_value_2",
                        },
                        "type": "Microsoft.Resources/resourceGroups",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                ),
            },
            id="Multiple groups monitored",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_resource_groups(
    mock_api_client: AsyncMock,
    monitored_groups: Sequence[str],
    expected_result: Mapping[str, AzureResourceGroup],
) -> None:
    mock_api_client.get_async.return_value = RESOURCE_GROUPS_RESPONSE

    groups = await get_resource_groups(
        mock_api_client,
        monitored_groups,
        fake_azure_subscription(),
        Args(
            tag_key_pattern=TagsImportPatternOption.import_all,
            safe_hostnames=False,
        ),
    )
    assert len(groups) == len(expected_result)
    for group_name, group in groups.items():
        assert group_name in expected_result
        assert group.info == expected_result[group_name].info
        assert group.tags == expected_result[group_name].tags


@pytest.mark.asyncio
async def test_write_resource_groups_sections(
    mock_api_client: AsyncMock,
    mock_azure_subscription: AzureSubscription,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mock_api_client.get_async.return_value = RESOURCE_GROUPS_RESPONSE

    groups = await get_resource_groups(
        mock_api_client,
        ["resource_group_1", "resource_group_2"],
        mock_azure_subscription,
        Args(
            tag_key_pattern=TagsImportPatternOption.import_all,
            safe_hostnames=False,
        ),
    )
    write_resource_groups_sections(groups)
    captured = capsys.readouterr()
    assert (
        captured.out
        == """<<<<resource_group_1>>>>
<<<azure_v2_resourcegroups:sep(124)>>>
Resource
{"id": "/subscriptions/subscripion_id/resourceGroups/resource_group_1", "name": "resource_group_1", "type": "Microsoft.Resources/resourceGroups", "location": "eastus", "managedBy": "subscriptions/subscripion_id/providers/Microsoft.RecoveryServices/", "properties": {"provisioningState": "Succeeded"}, "tags": {"group_tag_key_1": "group_tag_value_1"}, "tenant_id": "c8d03e63-0d65-41a7-81fd-0ccc184bdd1a", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "group": "resource_group_1"}
<<<<>>>>
<<<<resource_group_2>>>>
<<<azure_v2_resourcegroups:sep(124)>>>
Resource
{"id": "/subscriptions/subscripion_id/resourceGroups/resource_group_2", "name": "resource_group_2", "type": "Microsoft.Resources/resourceGroups", "location": "westeurope", "properties": {"provisioningState": "Succeeded"}, "tags": {"group_tag_key_2": "group_tag_value_2"}, "tenant_id": "c8d03e63-0d65-41a7-81fd-0ccc184bdd1a", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "group": "resource_group_2"}
<<<<>>>>
"""
    )


TAGS = {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"}


@pytest.mark.parametrize(
    "tags, tag_key_pattern, expected_tags",
    [
        pytest.param(
            TAGS,
            TagsImportPatternOption.import_all,
            {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
            id="Import all tags",
        ),
        pytest.param(
            TAGS,
            TagsImportPatternOption.ignore_all,
            {},
            id="Ignore all tags",
        ),
        pytest.param(
            TAGS,
            "key_1",
            {"tag_key_1": "tag_value_1"},
            id="Regex pattern tags 1",
        ),
        pytest.param(
            TAGS,
            "tag_",
            {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
            id="Regex pattern tags 2",
        ),
    ],
)
@pytest.mark.asyncio
async def test_filter_tags(
    tags: Mapping[str, str],
    tag_key_pattern: TagsOption,
    expected_tags: Mapping[str, str],
) -> None:
    assert filter_tags(tags, tag_key_pattern) == expected_tags


@pytest.mark.parametrize(
    "use_safe_names, monitored_groups, monitored_resources, expected_result",
    [
        pytest.param(
            False,
            {
                "burningman": AzureResourceGroup(
                    info={
                        "tags": {"my-resource-tag": "my-resource-value"},
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "burningman",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                )
            },
            [
                AzureResource(
                    {
                        "id": "myid",
                        "name": "MyVM",
                        "type": "Microsoft.Compute/virtualMachines",
                        "location": "westeurope",
                        "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                        "group": "BurningMan",
                    },
                    TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                ),
            ],
            "<<<<burningman>>>>\n"
            "<<<azure_v2_labels:sep(0)>>>\n"
            '{"cloud": "azure", "resource_group": "burningman", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "entity": "resource_group"}\n'
            '{"my-resource-tag": "my-resource-value"}\n'
            "<<<<>>>>\n"
            "<<<<mock_subscription_name>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\n"
            'monitored-groups|["burningman"]\n'
            'monitored-resources|["MyVM"]\n'
            "<<<<>>>>\n",
            id="Single group with virtual machine resource",
        ),
        pytest.param(
            False,
            {
                "burningman": AzureResourceGroup(
                    info={
                        "tags": {"my-resource-tag": "my-resource-value"},
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "burningman",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                ),
                "resource_group_name": AzureResourceGroup(
                    info={
                        "tags": {"my-resource-tag": "my-resource-value"},
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "resource_group_name",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                ),
            },
            [
                AzureResource(
                    {
                        "id": "resource_id",
                        "name": "my_resource",
                        "type": "Microsoft.Network/loadBalancers",
                        "location": "westeurope",
                        "tags": {},
                        "group": "resource_group_name",
                    },
                    TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(),
                    use_safe_names=False,
                ),
            ],
            "<<<<burningman>>>>\n"
            "<<<azure_v2_labels:sep(0)>>>\n"
            '{"cloud": "azure", "resource_group": "burningman", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "entity": "resource_group"}\n'
            '{"my-resource-tag": "my-resource-value"}\n'
            "<<<<>>>>\n"
            "<<<<resource_group_name>>>>\n"
            "<<<azure_v2_labels:sep(0)>>>\n"
            '{"cloud": "azure", "resource_group": "resource_group_name", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "entity": "resource_group"}\n'
            '{"my-resource-tag": "my-resource-value"}\n'
            "<<<<>>>>\n"
            "<<<<mock_subscription_name>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\n"
            'monitored-groups|["burningman", "resource_group_name"]\n'
            'monitored-resources|["my_resource"]\n'
            "<<<<>>>>\n",
            id="Multiple groups with load balancer resource",
        ),
        pytest.param(
            True,
            {
                "burningman": AzureResourceGroup(
                    info={
                        "tags": {"my-resource-tag": "my-resource-value"},
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "burningman",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(use_safe_names=True),
                    use_safe_names=True,
                )
            },
            [
                AzureResource(
                    {
                        "id": "myid",
                        "name": "MyVM",
                        "type": "Microsoft.Compute/virtualMachines",
                        "location": "westeurope",
                        "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                        "group": "BurningMan",
                    },
                    TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(use_safe_names=True),
                    use_safe_names=True,
                ),
            ],
            "<<<<burningman_cb8bc18c>>>>\n"
            "<<<azure_v2_labels:sep(0)>>>\n"
            '{"cloud": "azure", "resource_group": "burningman", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "entity": "resource_group"}\n'
            '{"my-resource-tag": "my-resource-value"}\n'
            "<<<<>>>>\n"
            "<<<<mock_subscription_name_9bb22fdd>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\n"
            'monitored-groups|["burningman"]\n'
            'monitored-resources|["MyVM"]\n'
            "<<<<>>>>\n",
            id="Safe hostnames with virtual machine",
        ),
        pytest.param(
            True,
            {
                "burningman": AzureResourceGroup(
                    info={
                        "tags": {},
                        "type": "Microsoft.Resources/resourceGroups",
                        "name": "burningman",
                    },
                    tag_key_pattern=TagsImportPatternOption.import_all,
                    subscription=fake_azure_subscription(use_safe_names=True),
                    use_safe_names=True,
                )
            },
            [],
            "<<<<burningman_cb8bc18c>>>>\n"
            "<<<azure_v2_labels:sep(0)>>>\n"
            '{"cloud": "azure", "resource_group": "burningman", "subscription_name": "mock_subscription_name", "subscription": "mock_subscription_id", "entity": "resource_group"}\n'
            "{}\n"
            "<<<<>>>>\n"
            "<<<<mock_subscription_name_9bb22fdd>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\n"
            'monitored-groups|["burningman"]\n'
            "monitored-resources|[]\n"
            "<<<<>>>>\n",
            id="Empty tags and resources with safe hostnames",
        ),
    ],
)
def test_write_group_info(
    use_safe_names: bool,
    monitored_groups: Mapping[str, AzureResourceGroup],
    monitored_resources: Sequence[AzureResource],
    expected_result: Sequence[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_group_info(
        monitored_groups,
        monitored_resources,
        fake_azure_subscription(use_safe_names=use_safe_names),
    )
    captured = capsys.readouterr()
    assert captured.out == expected_result


_monitored_vm_resource = lambda tag_pattern_option: {
    "/subscriptions/subscription_id/resourcegroups/resource_group_1/providers/microsoft.compute/virtualmachines/vm-test-1": AzureResource(
        {
            "id": "/subscriptions/subscription_id/resourceGroups/resource_group_1/providers/Microsoft.Compute/virtualMachines/VM-test-1",
            "name": "VM-test-1",
            "type": "Microsoft.Compute/virtualMachines",
            "location": "uksouth",
            "zones": ["1"],
            "subscription": "subscription_id",
            "group": "resource_group_1",
            "provider": "Microsoft.Compute",
            "tags": {"tag1": "value1"},
        },
        tag_pattern_option,
        subscription=AzureSubscription(
            id="mock_subscription_id",
            name="mock_subscription_name",
            tags={},
            use_safe_names=False,
            tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
        ),
        use_safe_names=False,
    )
}

RESOURCE_HEALTH_ENTRY = {
    "id": "/subscriptions/subscription_id/resourcegroups/resource_group_1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current",
    "name": "current",
    "type": "Microsoft.ResourceHealth/AvailabilityStatuses",
    "location": "uksouth",
    "properties": {
        "availabilityState": "Available",
        "title": "Available",
        "summary": "There aren't any known Azure platform problems affecting this virtual machine.",
        "reasonType": "",
        "category": "Not Applicable",
        "context": "Not Applicable",
        "occuredTime": "2023-02-09T16: 19: 01Z",
        "reasonChronicity": "Persistent",
        "reportedTime": "2023-02-22T15: 21: 41.7883795Z",
    },
}

RESOURCE_GROUPS = {
    "resource_group_1": AzureResourceGroup(
        info={
            "tags": {},
            "type": "Microsoft.Resources/resourceGroups",
            "name": "resource_group_1",
        },
        tag_key_pattern=TagsImportPatternOption.import_all,
        subscription=fake_azure_subscription(use_safe_names=False),
        use_safe_names=False,
    )
}


@pytest.mark.parametrize(
    "monitored_resources, resource_health, resource_groups, expected_sections",
    [
        pytest.param(
            _monitored_vm_resource(TagsImportPatternOption.ignore_all),
            [RESOURCE_HEALTH_ENTRY, RESOURCE_HEALTH_ENTRY],
            RESOURCE_GROUPS,
            [
                MockAzureSection(
                    name="resource_health",
                    piggytargets=["resource_group_1"],
                    content=[
                        '{"id": "/subscriptions/subscription_id/resourcegroups/resource_group_1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current", \
"name": "virtualmachines/vm-test-1", "availabilityState": "Available", "summary": "There aren\'t any known Azure platform problems affecting this virtual machine.", \
"reasonType": "", "occuredTime": "2023-02-09T16: 19: 01Z", "tags": {}}\n',
                        '{"id": "/subscriptions/subscription_id/resourcegroups/resource_group_1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current", \
"name": "virtualmachines/vm-test-1", "availabilityState": "Available", "summary": "There aren\'t any known Azure platform problems affecting this virtual machine.", \
"reasonType": "", "occuredTime": "2023-02-09T16: 19: 01Z", "tags": {}}\n',
                    ],
                    separator=0,
                )
            ],
            id="Virtual machine with 2 entries in resource health",
        ),
        pytest.param(
            _monitored_vm_resource(TagsImportPatternOption.import_all),
            [RESOURCE_HEALTH_ENTRY],
            RESOURCE_GROUPS,
            [
                MockAzureSection(
                    name="resource_health",
                    piggytargets=["resource_group_1"],
                    content=[
                        '{"id": "/subscriptions/subscription_id/resourcegroups/resource_group_1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current", \
"name": "virtualmachines/vm-test-1", "availabilityState": "Available", "summary": "There aren\'t any known Azure platform problems affecting this virtual machine.", \
"reasonType": "", "occuredTime": "2023-02-09T16: 19: 01Z", "tags": {"tag1": "value1"}}\n',
                    ],
                    separator=0,
                )
            ],
            id="Virtual machine import tags",
        ),
        pytest.param(
            _monitored_vm_resource(TagsImportPatternOption.import_all),
            [],
            RESOURCE_GROUPS,
            [],
            id="Empty resource health entries",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_resource_health_sections(
    monitored_resources: Mapping[str, AzureResource],
    resource_health: Sequence[ResourceHealth],
    expected_sections: Sequence[MockAzureSection],
    resource_groups: Mapping[str, AzureResourceGroup],
) -> None:
    sections = list(
        _get_resource_health_sections(resource_health, monitored_resources, resource_groups)
    )

    assert sections == expected_sections, "Sections not as expected"


@pytest.mark.parametrize(
    "rate_limit,expected_output",
    [
        pytest.param(
            10000,
            "<<<<mock_subscription_name>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\nremaining-reads|10000\n<<<<>>>>\n",
            id="Rate limit with specific value",
        ),
        pytest.param(
            None,
            "<<<<mock_subscription_name>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\nremaining-reads|None\n<<<<>>>>\n",
            id="No rate limit specified",
        ),
    ],
)
def test_write_remaining_reads(
    capsys: pytest.CaptureFixture[str],
    rate_limit: int | None,
    expected_output: str,
    mock_azure_subscription: AzureSubscription,
) -> None:
    write_remaining_reads(rate_limit, mock_azure_subscription)

    captured = capsys.readouterr()
    assert captured.out == expected_output


@pytest.mark.parametrize(
    "api_client_mock_return, expected_section",
    [
        pytest.param(
            # content of "value" field of the response
            [
                {
                    "not_used_field_1": "not_used_value_1",
                    "not_used_field_2": "not_used_value_2",
                    "appId": "app_id_1",
                    "id": "id_1",
                    "displayName": "test_app_1",
                    "passwordCredentials": [
                        {
                            "customKeyIdentifier": None,
                            "hint": "B4j",
                            "secretText": None,
                        }
                    ],
                    "keyCredentials": [],
                },
                {
                    "not_used_field_1": "not_used_value_1",
                    "not_used_field_2": "not_used_value_2",
                    "appId": "app_id_2",
                    "id": "id_2",
                    "displayName": "test_app_2",
                    "passwordCredentials": [
                        {
                            "customKeyIdentifier": None,
                        }
                    ],
                    "keyCredentials": [],
                },
            ],
            MockAzureSection(
                "app_registration",
                content=[
                    '{"appId": "app_id_1", "displayName": "test_app_1", "id": "id_1", \
"keyCredentials": [], "passwordCredentials": [{"customKeyIdentifier": null, "hint": "B4j", "secretText": null}]}\n',
                    '{"appId": "app_id_2", "displayName": "test_app_2", "id": "id_2", \
"keyCredentials": [], "passwordCredentials": [{"customKeyIdentifier": null}]}\n',
                ],
                separator=0,
            ),
            id="2 apps registered",
        ),
        pytest.param(
            # content of "value" field of the response
            [
                {
                    "not_used_field_1": "not_used_value_1",
                    "not_used_field_2": "not_used_value_2",
                    "appId": "app_id_1",
                    "id": "id_1",
                    "displayName": "test_app_1",
                    "passwordCredentials": [],
                    "keyCredentials": [],
                },
                {
                    "not_used_field_1": "not_used_value_1",
                    "not_used_field_2": "not_used_value_2",
                    "appId": "app_id_2",
                    "id": "id_2",
                    "displayName": "test_app_2",
                    "passwordCredentials": [
                        {
                            "customKeyIdentifier": None,
                        }
                    ],
                    "keyCredentials": [],
                },
            ],
            MockAzureSection(
                "app_registration",
                content=[
                    '{"appId": "app_id_2", "displayName": "test_app_2", "id": "id_2", \
"keyCredentials": [], "passwordCredentials": [{"customKeyIdentifier": null}]}\n',
                ],
                separator=0,
            ),
            id="2 apps registered, only 1 with filled password credentials",
        ),
    ],
)
@pytest.mark.asyncio
async def test_process_app_registrations_ok(
    api_client_mock_return: Sequence[Mapping],
    expected_section: MockAzureSection,
    mock_api_client: AsyncMock,
) -> None:
    mock_api_client.get_async.return_value = api_client_mock_return

    result_section = await process_app_registrations(mock_api_client)

    assert result_section == expected_section, "Section not as expected"


@pytest.mark.asyncio
async def test_process_app_registrations_missing_fields(
    mock_api_client: AsyncMock,
) -> None:
    mock_api_client.get_async.return_value = [  # content of "value" field of the response
        {
            "appId": "app_id",
            "id": "id",
            "displayName": "testsecret",
            # "passwordCredentials" missing field
        },
    ]

    with pytest.raises(KeyError):
        await process_app_registrations(mock_api_client)


@pytest.mark.asyncio
async def test_process_users(
    mock_api_client: AsyncMock,
) -> None:
    mock_api_client.request_async.return_value = 100

    result_section = await process_users(mock_api_client)

    expected_section = MockAzureSection(
        "ad",
        content=["users_count|100\n"],
    )

    assert result_section == expected_section, "Section not as expected"


@pytest.mark.asyncio
async def test_process_organization(
    mock_api_client: AsyncMock,
) -> None:
    mock_api_client.get_async.return_value = [
        {
            "id": "id",
            "deletedDateTime": None,
            "assignedPlans": [
                {
                    "capabilityStatus": "Deleted",
                    "service": "SCO",
                    "servicePlanId": "plan_id",
                }
            ],
            "onPremisesSyncStatus": [],
        }
    ]

    result_section = await process_organization(mock_api_client)

    expected_section = MockAzureSection(
        "ad",
        content=[
            'ad_connect|[{"assignedPlans": [{"capabilityStatus": "Deleted", \
"service": "SCO", "servicePlanId": "plan_id"}], "deletedDateTime": null, "id": "id", "onPremisesSyncStatus": []}]\n'
        ],
    )

    assert result_section == expected_section, "Section not as expected"


@dataclass
class AzureResourceInfo:
    section: str
    info_group: str
    piggytarget: str
    tags: dict[str, str]


RESOURCES_API_RESPONSE = [
    {
        "id": "/subscriptions/subscription_id/resourceGroups/resource_group_1/providers/Microsoft.Network/virtualNetworks/virtual_network_1",
        "name": "virtual_network_1",
        "type": "Microsoft.Network/virtualNetworks",
        "location": "region_name",
    },
    {
        "id": "/subscriptions/subscription_id/resourceGroups/resource_group_2/providers/Microsoft.Network/virtualNetworks/virtual_network_2",
        "name": "virtual_network_2",
        "type": "Microsoft.Network/virtualNetworks",
        "location": "region_name",
        "tags": {},
    },
    {
        "id": "/subscriptions/subscription_id/resourceGroups/resource_group_3/providers/Microsoft.Compute/virtualMachines/virtual_machine_1",
        "name": "virtual_machine_1",
        "type": "Microsoft.Compute/virtualMachines",
        "location": "region_name",
        "zones": ["1"],
        "plan": {
            "name": "checkmk_cloud_edition_22",
            "product": "checkmk003-preview",
            "publisher": "tribe29gmbh1665582614827",
        },
    },
    {
        "id": "/subscriptions/subscription_id/resourceGroups/resource_group_1/providers/Microsoft.Storage/storageAccounts/storage_account_1",
        "name": "storage_account_1",
        "type": "Microsoft.Storage/storageAccounts",
        "sku": {"name": "Standard_LRS", "tier": "Standard"},
        "kind": "StorageV2",
        "location": "westeurope",
        "tags": {"ms-resource-usage": "azure-cloud-shell"},
    },
    {
        "id": "/subscriptions/subscription_id/resourceGroups/resource_group_1/providers/Microsoft.Cache/Redis/redis_cache_1",
        "name": "redis_cache_1",
        "type": "Microsoft.Cache/Redis",
        "location": "centralus",
        "tags": {},
        "subscription": "subscription_id",
        "group": "somegroup",
        "provider": "Microsoft.Cache",
    },
]


@pytest.mark.parametrize(
    "api_client_mock_return, args, expected_resources, expected_monitored_groups",
    [
        pytest.param(
            RESOURCES_API_RESPONSE,
            Args(
                explicit_config=[],
                require_tag=[],
                require_tag_value=[],
                debug=False,
                tag_key_pattern=TagsImportPatternOption.import_all,
                safe_hostnames=False,
            ),
            [
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_1",
                    piggytarget="virtual_network_1",
                    tags={},
                ),
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_2",
                    piggytarget="virtual_network_2",
                    tags={},
                ),
                AzureResourceInfo(
                    section="virtualmachines",
                    info_group="resource_group_3",
                    piggytarget="virtual_machine_1",
                    tags={},
                ),
                AzureResourceInfo(
                    section="storageaccounts",
                    info_group="resource_group_1",
                    piggytarget="storage_account_1",
                    tags={"ms-resource-usage": "azure-cloud-shell"},
                ),
                AzureResourceInfo(
                    section="redis",
                    info_group="resource_group_1",
                    piggytarget="redis_cache_1",
                    tags={},
                ),
            ],
            [
                "resource_group_1",
                "resource_group_2",
                "resource_group_3",
            ],
            id="Multiple Resources and groups all tags",
        ),
        pytest.param(
            RESOURCES_API_RESPONSE,
            Args(
                explicit_config=[],
                require_tag=[],
                require_tag_value=[],
                debug=False,
                tag_key_pattern=TagsImportPatternOption.ignore_all,
                safe_hostnames=False,
            ),
            [
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_1",
                    piggytarget="virtual_network_1",
                    tags={},
                ),
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_2",
                    piggytarget="virtual_network_2",
                    tags={},
                ),
                AzureResourceInfo(
                    section="virtualmachines",
                    info_group="resource_group_3",
                    piggytarget="virtual_machine_1",
                    tags={},
                ),
                AzureResourceInfo(
                    section="storageaccounts",
                    info_group="resource_group_1",
                    piggytarget="storage_account_1",
                    tags={},
                ),
                AzureResourceInfo(
                    section="redis",
                    info_group="resource_group_1",
                    piggytarget="redis_cache_1",
                    tags={},
                ),
            ],
            [
                "resource_group_1",
                "resource_group_2",
                "resource_group_3",
            ],
            id="Multiple Resources and groups ignore tags",
        ),
        pytest.param(
            RESOURCES_API_RESPONSE,
            Args(
                explicit_config=["group=resource_group_1"],
                require_tag=[],
                require_tag_value=[],
                debug=False,
                tag_key_pattern=TagsImportPatternOption.import_all,
                safe_hostnames=False,
            ),
            [
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_1",
                    piggytarget="virtual_network_1",
                    tags={},
                ),
                AzureResourceInfo(
                    section="storageaccounts",
                    info_group="resource_group_1",
                    piggytarget="storage_account_1",
                    tags={"ms-resource-usage": "azure-cloud-shell"},
                ),
                AzureResourceInfo(
                    section="redis",
                    info_group="resource_group_1",
                    piggytarget="redis_cache_1",
                    tags={},
                ),
            ],
            ["resource_group_1"],
            id="Resources selected on explicit config group",
        ),
    ],
)
@pytest.mark.asyncio
async def test_collect_resources(
    api_client_mock_return: Sequence[Mapping],
    args: Args,
    expected_resources: Sequence[AzureResourceInfo],
    expected_monitored_groups: set[str],
    mock_api_client: AsyncMock,
    mock_azure_subscription: AzureSubscription,
) -> None:
    mock_api_client.get_async.return_value = api_client_mock_return

    selector = Selector(args)
    result_resources, result_groups = await _collect_resources(
        mock_api_client, mock_azure_subscription, args, selector
    )

    assert len(result_resources) == len(expected_resources), "Resource count mismatch"
    for resource, expected in zip(result_resources, expected_resources):
        assert resource.section == expected.section, "Section mismatch"
        assert resource.info["group"] == expected.info_group, "Info group mismatch"
        assert resource.piggytarget == expected.piggytarget, "Piggy targets mismatch"
        assert resource.tags == expected.tags, "Tags mismatch"

    assert set(result_groups) == set(expected_monitored_groups), "Monitored groups mismatch"


RESOURCE_DATA = {
    "id": "/subscriptions/subscription_id/resourceGroups/resource_group_1/...normal_data_has_something_here...",
    "name": "storage_account_1",
    "type": "Microsoft.Storage/storageAccounts",
    "sku": {"name": "Standard_LRS", "tier": "Standard"},
    "kind": "StorageV2",
    "location": "westeurope",
    "tags": {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
}

RESOURCE_DATA_DIFFERENT_GROUP = {
    "id": "/subscriptions/subscription_id/resourceGroups/resource_group_2/...normal_data_has_something_here...",
    "name": "storage_account_1",
    "type": "Microsoft.Storage/storageAccounts",
    "sku": {"name": "Standard_LRS", "tier": "Standard"},
    "kind": "StorageV2",
    "location": "westeurope",
    "tags": {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
}

RESOURCE_DATA_DIFFERENT_TYPE = {
    "id": "/subscriptions/subscription_id/resourceGroups/resource_group_1/...normal_data_has_something_here...",
    "name": "storage_account_1",
    "type": "Microsoft.Compute/virtualMachines",
    "location": "westeurope",
    "tags": {"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
}


@pytest.mark.parametrize(
    "resource_data, tags_pattern, safe_hostname, expected_resource",
    [
        pytest.param(
            RESOURCE_DATA,
            TagsImportPatternOption.import_all,
            False,
            AzureResourceInfo(
                section="storageaccounts",
                info_group="resource_group_1",
                piggytarget="storage_account_1",
                tags={"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
            ),
            id="Resource with imported tags",
        ),
        pytest.param(
            RESOURCE_DATA,
            TagsImportPatternOption.ignore_all,
            False,
            AzureResourceInfo(
                section="storageaccounts",
                info_group="resource_group_1",
                piggytarget="storage_account_1",
                tags={},
            ),
            id="Resource without imported tags",
        ),
        pytest.param(
            RESOURCE_DATA,
            "key_2",
            False,
            AzureResourceInfo(
                section="storageaccounts",
                info_group="resource_group_1",
                piggytarget="storage_account_1",
                tags={"tag_key_2": "tag_value_2"},
            ),
            id="Resource with filtered tags",
        ),
        pytest.param(
            RESOURCE_DATA,
            TagsImportPatternOption.import_all,
            True,
            AzureResourceInfo(
                section="storageaccounts",
                info_group="resource_group_1",
                piggytarget="storage_account_1_01b48bd7",
                tags={"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
            ),
            id="Resource with imported tags, safe hostname",
        ),
        pytest.param(
            RESOURCE_DATA_DIFFERENT_GROUP,
            TagsImportPatternOption.import_all,
            True,
            AzureResourceInfo(
                section="storageaccounts",
                info_group="resource_group_2",
                piggytarget="storage_account_1_cc6ac70f",
                tags={"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
            ),
            id="Resource with safe hostname, ensures resource group uniqueness",
        ),
        pytest.param(
            RESOURCE_DATA_DIFFERENT_TYPE,
            TagsImportPatternOption.import_all,
            True,
            AzureResourceInfo(
                section="virtualmachines",
                info_group="resource_group_1",
                piggytarget="storage_account_1_6bba70d5",
                tags={"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
            ),
            id="Resource with safe hostname, ensures resource type uniqueness 2",
        ),
    ],
)
def test_azure_resource(
    resource_data: Mapping,
    expected_resource: AzureResourceInfo,
    safe_hostname: bool,
    tags_pattern: TagsOption,
    mock_azure_subscription: AzureSubscription,
) -> None:
    resource = AzureResource(
        dict(resource_data), tags_pattern, mock_azure_subscription, safe_hostname
    )

    assert resource.section == expected_resource.section, "Section mismatch"
    assert resource.info["group"] == expected_resource.info_group, "Info group mismatch"
    assert resource.piggytarget == expected_resource.piggytarget, "Piggy targets mismatch"
    assert resource.tags == expected_resource.tags, "Tags mismatch"


@pytest.mark.asyncio
async def test_write_subscription_section(
    mock_azure_subscription: AzureSubscription,
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_subscription_section(mock_azure_subscription)
    captured = capsys.readouterr()
    assert (
        captured.out
        == """<<<<mock_subscription_name>>>>
<<<azure_v2_subscription:sep(124)>>>
Resource
{"name": "mock_subscription_name", "tags": {}, "id": "mock_subscription_id", "type": "subscription", "group": "", "tenant_id": "c8d03e63-0d65-41a7-81fd-0ccc184bdd1a", "subscription_name": "mock_subscription_name"}
<<<<>>>>
"""
    )


@pytest.mark.asyncio
async def test_write_subscription_section_safe_hostname(capsys: pytest.CaptureFixture[str]) -> None:
    subscription = fake_azure_subscription(use_safe_names=True)
    write_subscription_section(subscription)
    captured = capsys.readouterr()
    assert (
        captured.out
        == """<<<<mock_subscription_name_9bb22fdd>>>>
<<<azure_v2_subscription:sep(124)>>>
Resource
{"name": "mock_subscription_name", "tags": {}, "id": "mock_subscription_id", "type": "subscription", "group": "", "tenant_id": "c8d03e63-0d65-41a7-81fd-0ccc184bdd1a", "subscription_name": "mock_subscription_name"}
<<<<>>>>
"""
    )


@pytest.mark.parametrize(
    "metadata, expected_result",
    [
        pytest.param(
            [
                {
                    "name": {
                        "value": "databasename",
                        "localizedValue": "databasename",
                        "something": "else",
                    },
                    "value": "SampleDB",
                },
                {
                    "name": {
                        "value": "servername",
                        "localizedValue": "servername",
                        "something": "else",
                    },
                    "value": "my-server",
                },
            ],
            {
                "databasename": "SampleDB",
                "servername": "my-server",
            },
            id="Valid metadata with multiple items and data",
        ),
        pytest.param(
            [],
            {},
            id="Empty metadata list",
        ),
        pytest.param(
            [
                {
                    "name": {
                        "value": "key1",
                    },
                    "value": "value1",
                },
            ],
            {
                "key1": "value1",
            },
            id="Metadata with only value field in name",
        ),
    ],
)
def test_parse_metrics_metadata(
    metadata: Sequence[Mapping[str, str | object]], expected_result: Mapping[str, str]
) -> None:
    assert _parse_metrics_metadata(metadata) == expected_result


def test_parse_metrics_invalid_metadata() -> None:
    invalid_metadata: Sequence[Mapping[str, str | object]] = [
        {
            "invalid_field": "invalid_value",
        },
        {
            "name": {
                "localizedValue": "missing_value_field",
            },
        },
    ]
    with pytest.raises(ValidationError):
        assert _parse_metrics_metadata(invalid_metadata) == {}
