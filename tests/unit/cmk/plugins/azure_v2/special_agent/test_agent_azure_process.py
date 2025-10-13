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

from cmk.plugins.azure_v2.special_agent.agent_azure_v2 import (
    _collect_resources,
    _get_resource_health_sections,
    AzureResource,
    AzureSubscription,
    filter_tags,
    get_group_labels,
    get_resource_host_labels_section,
    GroupLabels,
    process_app_registrations,
    process_organization,
    process_redis,
    process_users,
    ResourceHealth,
    Selector,
    TagsImportPatternOption,
    TagsOption,
    write_group_info,
    write_remaining_reads,
)

from .lib import fake_azure_subscription, MockAzureSection

Args = argparse.Namespace


@pytest.mark.parametrize(
    "resource, group_tags, expected_result",
    [
        (
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
            ),
            {
                "burningman": {
                    "my-resource-tag": "my-resource-value",
                    "resource_group": "burningman",
                }
            },
            (
                [
                    '{"resource_group": "burningman", "entity": "virtualmachines", "subscription_name": "mock_subscription_name",'
                    ' "subscription_id": "mock_subscription_id", "vm_instance": true}\n',
                    '{"my-unique-tag": "unique", "tag4all": "True", "my-resource-tag": "my-resource-value", "resource_group": "burningman"}\n',
                ],
                ["MyVM"],
            ),
        ),
        (
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
                subscription=AzureSubscription(
                    id="mock_subscription_id",
                    name="mock_subscription_name",
                    tags={},
                    safe_hostnames=False,
                    tenant_id="tenant_id",
                ),
            ),
            {
                "resource_group_name": {
                    "resource_group": "resource_group_name",
                    "another_group_tag": "another_value",
                }
            },
            (
                [
                    '{"resource_group": "resource_group_name", "entity": "loadbalancers", "subscription_name": "mock_subscription_name",'
                    ' "subscription_id": "mock_subscription_id"}\n',
                    '{"my-unique-tag": "unique", "tag4all": "True", "resource_group": "resource_group_name", "another_group_tag": "another_value"}\n',
                ],
                ["my_resource"],
            ),
        ),
        (
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
                subscription=AzureSubscription(
                    id="mock_subscription_id",
                    name="mock_subscription_name",
                    tags={},
                    safe_hostnames=False,
                    tenant_id="tenant_id",
                ),
            ),
            {"resource_group_name": {}},
            (
                [
                    '{"resource_group": "resource_group_name", "entity": "loadbalancers", "subscription_name": "mock_subscription_name",'
                    ' "subscription_id": "mock_subscription_id"}\n',
                    "{}\n",
                ],
                ["my_resource"],
            ),
        ),
    ],
)
def test_get_resource_host_labels_section(
    resource: AzureResource,
    group_tags: GroupLabels,
    expected_result: tuple[Sequence[str], Sequence[str]],
) -> None:
    labels_section = get_resource_host_labels_section(resource, group_tags)

    assert labels_section._cont == expected_result[0]
    assert labels_section._piggytargets == expected_result[1]


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
    "monitored_groups, tag_key_pattern, expected_result",
    [
        pytest.param(
            ["resource_group_non_existent"],
            TagsImportPatternOption.import_all,
            {},
            id="No labels monitored",
        ),
        pytest.param(
            ["resource_group_1"],
            TagsImportPatternOption.import_all,
            {"resource_group_1": {"group_tag_key_1": "group_tag_value_1"}},
            id="Labels monitored, import all tags",
        ),
        pytest.param(
            ["resource_group_1", "resource_group_2"],
            TagsImportPatternOption.ignore_all,
            {"resource_group_1": {}, "resource_group_2": {}},
            id="Labels monitored, ignore tags",
        ),
        pytest.param(
            ["resource_group_1", "resource_group_2"],
            "group_tag",
            {
                "resource_group_1": {"group_tag_key_1": "group_tag_value_1"},
                "resource_group_2": {"group_tag_key_2": "group_tag_value_2"},
            },
            id="Labels monitored with pattern for tags",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_group_labels(
    monitored_groups: Sequence[str],
    tag_key_pattern: TagsOption,
    expected_result: GroupLabels,
    mock_api_client: AsyncMock,
) -> None:
    mock_api_client.get_async.return_value = RESOURCE_GROUPS_RESPONSE

    group_tags = await get_group_labels(mock_api_client, monitored_groups, tag_key_pattern)
    assert group_tags == expected_result


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
    "monitored_groups, monitored_resources, group_tags, expected_result",
    [
        (
            ["burningman"],
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
                ),
            ],
            {"burningman": {"my-resource-tag": "my-resource-value"}},
            "<<<<burningman>>>>\n"
            "<<<azure_v2_labels:sep(0)>>>\n"
            '{"resource_group": "burningman", "subscription_name": "mock_subscription_name", "subscription_id": "mock_subscription_id", "entity": "resource_group"}\n'
            '{"my-resource-tag": "my-resource-value"}\n'
            "<<<<>>>>\n"
            "<<<<mock_subscription_name>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\n"
            'monitored-groups|["burningman"]\n'
            'monitored-resources|["MyVM"]\n'
            "<<<<>>>>\n",
        ),
        (
            ["burningman", "resource_group_name"],
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
                ),
            ],
            {"resource_group_name": {"my-resource-tag": "my-resource-value"}},
            "<<<<resource_group_name>>>>\n"
            "<<<azure_v2_labels:sep(0)>>>\n"
            '{"resource_group": "resource_group_name", "subscription_name": "mock_subscription_name", "subscription_id": "mock_subscription_id", "entity": "resource_group"}\n'
            '{"my-resource-tag": "my-resource-value"}\n'
            "<<<<>>>>\n"
            "<<<<mock_subscription_name>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\n"
            'monitored-groups|["burningman", "resource_group_name"]\n'
            'monitored-resources|["my_resource"]\n'
            "<<<<>>>>\n",
        ),
    ],
)
def test_write_group_info(
    monitored_groups: Sequence[str],
    monitored_resources: Sequence[AzureResource],
    group_tags: GroupLabels,
    expected_result: Sequence[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_group_info(
        monitored_groups,
        monitored_resources,
        fake_azure_subscription(),
        group_tags,
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
            safe_hostnames=False,
            tenant_id="c8d03e63-0d65-41a7-81fd-0ccc184bdd1a",
        ),
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


@pytest.mark.parametrize(
    "monitored_resources, resource_health, expected_sections",
    [
        pytest.param(
            _monitored_vm_resource(TagsImportPatternOption.ignore_all),
            [RESOURCE_HEALTH_ENTRY, RESOURCE_HEALTH_ENTRY],
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
                )
            ],
            id="virtual machine with 2 entries in resource health",
        ),
        pytest.param(
            _monitored_vm_resource(TagsImportPatternOption.import_all),
            [RESOURCE_HEALTH_ENTRY],
            [
                MockAzureSection(
                    name="resource_health",
                    piggytargets=["resource_group_1"],
                    content=[
                        '{"id": "/subscriptions/subscription_id/resourcegroups/resource_group_1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current", \
"name": "virtualmachines/vm-test-1", "availabilityState": "Available", "summary": "There aren\'t any known Azure platform problems affecting this virtual machine.", \
"reasonType": "", "occuredTime": "2023-02-09T16: 19: 01Z", "tags": {"tag1": "value1"}}\n',
                    ],
                )
            ],
            id="virtual machine import tags",
        ),
        pytest.param(
            _monitored_vm_resource(TagsImportPatternOption.import_all),
            [],
            [],
            id="empty resource health entries",
        ),
    ],
)
@pytest.mark.asyncio
async def test_get_resource_health_sections(
    monitored_resources: Mapping[str, AzureResource],
    resource_health: Sequence[ResourceHealth],
    expected_sections: Sequence[MockAzureSection],
    mock_azure_subscription: AzureSubscription,
) -> None:
    sections = list(
        _get_resource_health_sections(resource_health, monitored_resources, mock_azure_subscription)
    )

    assert sections == expected_sections, "Sections not as expected"


@pytest.mark.parametrize(
    "rate_limit,expected_output",
    [
        (
            10000,
            "<<<<mock_subscription_name>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\nremaining-reads|10000\n<<<<>>>>\n",
        ),
        (
            None,
            "<<<<mock_subscription_name>>>>\n"
            "<<<azure_v2_agent_info:sep(124)>>>\nremaining-reads|None\n<<<<>>>>\n",
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
                },
            ],
            MockAzureSection(
                "app_registration",
                content=[
                    '{"appId": "app_id_1", "displayName": "test_app_1", "id": "id_1", \
"passwordCredentials": [{"customKeyIdentifier": null, "hint": "B4j", "secretText": null}]}\n',
                    '{"appId": "app_id_2", "displayName": "test_app_2", "id": "id_2", \
"passwordCredentials": [{"customKeyIdentifier": null}]}\n',
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
                },
            ],
            MockAzureSection(
                "app_registration",
                content=[
                    '{"appId": "app_id_2", "displayName": "test_app_2", "id": "id_2", \
"passwordCredentials": [{"customKeyIdentifier": null}]}\n',
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


@pytest.mark.asyncio
@pytest.mark.skip(reason="Probably make sense to just test _gather_sections_from_resources?")
async def test_process_redis(mock_azure_subscription: AzureSubscription) -> None:
    resource = AzureResource(
        {
            "id": "/subscriptions/ba9f74ff-6a4c-41e0-ab55-15c7fe79632f/resourceGroups/gemdev/providers/Microsoft.Cache/Redis/rickcmktest",
            "name": "rickcmktest",
            "type": "Microsoft.Cache/Redis",
            "location": "centralus",
            "tags": {},
            "subscription": "ba9f74ff-6a4c-41e0-ab55-15c7fe79632f",
            "group": "gemdev",
            "provider": "Microsoft.Cache",
        },
        TagsImportPatternOption.import_all,
        mock_azure_subscription,
    )

    result_section = await process_redis(resource)

    expected_section = MockAzureSection(
        "redis",
        content=[
            "Resource\n",
            '{"id": "/subscriptions/ba9f74ff-6a4c-41e0-ab55-15c7fe79632f/resourceGroups/gemdev/providers/Microsoft.Cache/Redis/rickcmktest", "name": "rickcmktest", "type": "Microsoft.Cache/Redis", "location": "centralus", "tags": {}, "subscription": "ba9f74ff-6a4c-41e0-ab55-15c7fe79632f", "group": "gemdev", "provider": "Microsoft.Cache"}\n',
        ],
        piggytargets=["rickcmktest"],
    )

    assert result_section == expected_section, "Section not as expected"


@dataclass
class AzureResourceInfo:
    section: str
    info_group: str
    piggytargets: Sequence[str]
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
            ),
            [
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
                    tags={},
                ),
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_2",
                    piggytargets=["resource_group_2"],
                    tags={},
                ),
                AzureResourceInfo(
                    section="virtualmachines",
                    info_group="resource_group_3",
                    piggytargets=["resource_group_3"],
                    tags={},
                ),
                AzureResourceInfo(
                    section="storageaccounts",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
                    tags={"ms-resource-usage": "azure-cloud-shell"},
                ),
                AzureResourceInfo(
                    section="redis",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
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
            ),
            [
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
                    tags={},
                ),
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_2",
                    piggytargets=["resource_group_2"],
                    tags={},
                ),
                AzureResourceInfo(
                    section="virtualmachines",
                    info_group="resource_group_3",
                    piggytargets=["resource_group_3"],
                    tags={},
                ),
                AzureResourceInfo(
                    section="storageaccounts",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
                    tags={},
                ),
                AzureResourceInfo(
                    section="redis",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
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
            ),
            [
                AzureResourceInfo(
                    section="virtualnetworks",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
                    tags={},
                ),
                AzureResourceInfo(
                    section="storageaccounts",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
                    tags={"ms-resource-usage": "azure-cloud-shell"},
                ),
                AzureResourceInfo(
                    section="redis",
                    info_group="resource_group_1",
                    piggytargets=["resource_group_1"],
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
        assert resource.piggytargets == expected.piggytargets, "Piggy targets mismatch"
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


@pytest.mark.parametrize(
    "resource_data, tags_pattern, expected_resource",
    [
        pytest.param(
            RESOURCE_DATA,
            TagsImportPatternOption.import_all,
            AzureResourceInfo(
                section="storageaccounts",
                info_group="resource_group_1",
                piggytargets=["resource_group_1"],
                tags={"tag_key_1": "tag_value_1", "tag_key_2": "tag_value_2"},
            ),
            id="Resource with imported tags",
        ),
        pytest.param(
            RESOURCE_DATA,
            TagsImportPatternOption.ignore_all,
            AzureResourceInfo(
                section="storageaccounts",
                info_group="resource_group_1",
                piggytargets=["resource_group_1"],
                tags={},
            ),
            id="Resource without imported tags",
        ),
        pytest.param(
            RESOURCE_DATA,
            "key_2",
            AzureResourceInfo(
                section="storageaccounts",
                info_group="resource_group_1",
                piggytargets=["resource_group_1"],
                tags={"tag_key_2": "tag_value_2"},
            ),
            id="Resource with filtered tags",
        ),
    ],
)
def test_azure_resource(
    resource_data: Mapping,
    expected_resource: AzureResourceInfo,
    tags_pattern: TagsOption,
    mock_azure_subscription: AzureSubscription,
) -> None:
    resource = AzureResource(resource_data, tags_pattern, mock_azure_subscription)

    assert resource.section == expected_resource.section, "Section mismatch"
    assert resource.info["group"] == expected_resource.info_group, "Info group mismatch"
    assert resource.piggytargets == expected_resource.piggytargets, "Piggy targets mismatch"
    assert resource.tags == expected_resource.tags, "Tags mismatch"
