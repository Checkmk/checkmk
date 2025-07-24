#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock

import pytest

from cmk.plugins.azure.special_agent.agent_azure import (
    _collect_resources,
    _get_resource_health_sections,
    Args,
    AzureResource,
    AzureSection,
    get_group_labels,
    get_vm_labels_section,
    GroupLabels,
    process_app_registrations,
    process_organization,
    process_usage_details,
    process_users,
    ResourceHealth,
    Selector,
    TagsImportPatternOption,
    TagsOption,
    write_group_info,
    write_remaining_reads,
)
from cmk.plugins.azure.special_agent.azure_api_client import (
    _AuthorityURLs,
    ApiError,
    BaseAsyncApiClient,
)
from cmk.utils.http_proxy_config import NoProxyConfig


class MockBaseAsyncApiClient(BaseAsyncApiClient):
    def __init__(
        self,
        resource_groups: Sequence[Mapping[str, Any]],
        vmviews: Mapping[str, Mapping[str, Mapping[str, Sequence[Mapping[str, str]]]]],
        ratelimit: float,
        usage_data: Sequence[object] | None = None,
        usage_details_exception: Exception | None = None,
        resource_health: object | None = None,
        resource_health_exception: Exception | None = None,
    ) -> None:
        self.resource_groups = resource_groups
        self.vmviews = vmviews
        self.rate_limit = ratelimit
        self.usage_data = usage_data if usage_data else []
        self.usage_details_exception = usage_details_exception
        self.resource_health = resource_health
        self.resource_health_exception = resource_health_exception

        super().__init__(
            _AuthorityURLs("login-url", "resource-url", "base-url"),
            NoProxyConfig(),
            "tenant",
            "client",
            "secret",
        )

    async def resourcegroups(self) -> Sequence[Mapping[str, Any]]:
        return self.resource_groups

    async def vmview(self, group: str, name: str) -> Mapping[str, Sequence[Mapping[str, str]]]:
        return self.vmviews[group][name]

    @property
    def ratelimit(self) -> float:
        return self.rate_limit

    async def usagedetails(self) -> Sequence[object]:
        if self.usage_details_exception is not None:
            raise self.usage_details_exception

        return self.usage_data

    def resource_health_view(self) -> object:
        if self.resource_health_exception is not None:
            raise self.resource_health_exception

        return self.resource_health


@pytest.fixture
def mock_api_client() -> AsyncMock:
    return AsyncMock(spec=BaseAsyncApiClient)


class MockAzureSection(AzureSection):
    def __init__(
        self,
        name: str,
        content: list[Any] = [],
        piggytargets: Iterable[str] = ("",),
        separator: int = 124,
    ) -> None:
        super().__init__(name, piggytargets, separator)
        self._cont = content


@pytest.mark.parametrize(
    "mgmt_client, vmach_info, args, expected_info, expected_tags, expected_piggyback_targets",
    [
        (
            MockBaseAsyncApiClient(
                [],
                {
                    "burningman": {
                        "myvm": {
                            "statuses": [
                                {
                                    "code": "ProvisioningState/succeeded",
                                    "level": "Info",
                                    "displayStatus": "Provisioning succeeded",
                                    "time": "2019-11-25T07:38:14.6999403+00:00",
                                }
                            ]
                        }
                    }
                },
                2.0,
            ),
            {
                "id": "myid",
                "name": "myvm",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "westeurope",
                "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                "group": "burningman",
            },
            Args(piggyback_vms="self"),
            {
                "group": "burningman",
                "id": "myid",
                "location": "westeurope",
                "name": "myvm",
                "specific_info": {
                    "statuses": [
                        {
                            "code": "ProvisioningState/succeeded",
                            "displayStatus": "Provisioning succeeded",
                            "level": "Info",
                            "time": "2019-11-25T07:38:14.6999403+00:00",
                        }
                    ]
                },
                "tags": {
                    "my-unique-tag": "unique",
                    "tag4all": "True",
                },
                "type": "Microsoft.Compute/virtualMachines",
            },
            {
                "my-unique-tag": "unique",
                "tag4all": "True",
            },
            ["myvm"],
        ),
        (
            MockBaseAsyncApiClient(
                [],
                {
                    "burningman": {
                        "MyVM": {
                            "statuses": [
                                {
                                    "code": "ProvisioningState/succeeded",
                                    "level": "Info",
                                    "displayStatus": "Provisioning succeeded",
                                    "time": "2019-11-25T07:38:14.6999403+00:00",
                                }
                            ]
                        }
                    }
                },
                2.0,
            ),
            {
                "id": "myid",
                "name": "MyVM",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "westeurope",
                "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                "group": "burningman",
            },
            Args(piggyback_vms="grouphost"),
            {
                "group": "burningman",
                "id": "myid",
                "location": "westeurope",
                "name": "MyVM",
                "specific_info": {
                    "statuses": [
                        {
                            "code": "ProvisioningState/succeeded",
                            "displayStatus": "Provisioning succeeded",
                            "level": "Info",
                            "time": "2019-11-25T07:38:14.6999403+00:00",
                        }
                    ]
                },
                "tags": {
                    "my-unique-tag": "unique",
                    "tag4all": "True",
                },
                "type": "Microsoft.Compute/virtualMachines",
            },
            {
                "my-unique-tag": "unique",
                "tag4all": "True",
            },
            ["burningman"],
        ),
    ],
)
@pytest.mark.asyncio
@pytest.mark.skip("Used different API to fetch VMs info")
async def test_process_vm(
    mgmt_client: BaseAsyncApiClient,
    vmach_info: Mapping[str, Any],
    args: Args,
    expected_info: Mapping[str, Any],
    expected_tags: Mapping[str, str],
    expected_piggyback_targets: Sequence[str],
) -> None:
    vmach = AzureResource(vmach_info, TagsImportPatternOption.import_all)
    # await process_vm(mgmt_client, vmach, args)

    assert vmach.info == expected_info
    assert vmach.tags == expected_tags
    assert vmach.piggytargets == expected_piggyback_targets


@pytest.mark.parametrize(
    "vm, group_tags, expected_result",
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
            ),
            {
                "burningman": {
                    "my-resource-tag": "my-resource-value",
                    "resource_group": "burningman",
                }
            },
            (
                [
                    '{"group_name": "burningman", "vm_instance": true}\n',
                    '{"my-unique-tag": "unique", "tag4all": "True", "my-resource-tag": "my-resource-value", "resource_group": "burningman"}\n',
                ],
                ["MyVM"],
            ),
        )
    ],
)
def test_get_vm_labels_section(
    vm: AzureResource, group_tags: GroupLabels, expected_result: tuple[Sequence[str], Sequence[str]]
) -> None:
    labels_section = get_vm_labels_section(vm, group_tags)

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
                ),
            ],
            {
                "burningman": {
                    "my-resource-tag": "my-resource-value",
                    "cmk/azure/resource_group": "BurningMan",
                }
            },
            "<<<<burningman>>>>\n"
            "<<<azure_labels:sep(0)>>>\n"
            '{"group_name": "burningman"}\n'
            '{"my-resource-tag": "my-resource-value", "cmk/azure/resource_group": "BurningMan"}\n'
            "<<<<>>>>\n"
            "<<<<>>>>\n"
            "<<<azure_agent_info:sep(124)>>>\n"
            'monitored-groups|["burningman"]\n'
            'monitored-resources|["MyVM"]\n'
            "<<<<>>>>\n",
        )
    ],
)
def test_write_group_info(
    monitored_groups: Sequence[str],
    monitored_resources: Sequence[AzureResource],
    group_tags: GroupLabels,
    expected_result: Sequence[str],
    capsys: pytest.CaptureFixture[str],
) -> None:
    write_group_info(monitored_groups, monitored_resources, group_tags)
    captured = capsys.readouterr()
    assert captured.out == expected_result


@pytest.mark.parametrize(
    "args, usage_data, exception, expected_result",
    [
        pytest.param(
            Args(
                debug=False,
                services=["usage_details"],
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            None,
            ApiError("offer MS-AZR-0145P"),
            "",
            id="api error no consumption offer",
        ),
        pytest.param(
            Args(
                debug=False,
                services=["usage_details"],
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            None,
            ApiError("Customer does not have the privilege to see the cost (Request ID: xxxx)"),
            "",
            id="api error customer not privileged",
        ),
        pytest.param(
            Args(
                debug=False,
                services=["usage_details"],
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            None,
            ApiError("unknown offer"),
            "<<<<>>>>\n"
            "<<<azure_agent_info:sep(124)>>>\n"
            'agent-bailout|[2, "Usage client: unknown offer"]\n'
            "<<<<>>>>\n"
            "<<<<test1>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "<<<<test2>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "<<<<>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "<<<<>>>>\n",
            id="api error unknown offer",
        ),
        pytest.param(
            Args(
                debug=False,
                services=["usage_details"],
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            None,
            Exception(),
            "<<<<>>>>\n"
            "<<<azure_agent_info:sep(124)>>>\n"
            'agent-bailout|[2, "Usage client: "]\n'
            "<<<<>>>>\n"
            "<<<<test1>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "<<<<test2>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "<<<<>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "<<<<>>>>\n",
            id="exception in the api call",
        ),
        pytest.param(
            Args(
                debug=False,
                services=["usage_details"],
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            [],
            None,
            "<<<<>>>>\n"
            "<<<azure_agent_info:sep(124)>>>\n"
            'agent-bailout|[0, "Usage client: Azure API did not return any usage details"]\n'
            "<<<<>>>>\n",
            id="empty usage data",
        ),
        pytest.param(
            Args(
                debug=False,
                services=["usage_details"],
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            [
                {
                    "id": "subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071",
                    "name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-6",
                    "type": "Microsoft.CostManagement/query",
                    "location": None,
                    "sku": None,
                    "eTag": None,
                    "properties": {
                        "Cost": 7.349267385987696,
                        "CostUSD": 7.97158038308434,
                        "ResourceType": "microsoft.network/applicationgateways",
                        "ResourceGroupName": "test1",
                        "Tags": [],
                        "Currency": "EUR",
                    },
                },
                {
                    "id": "subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071",
                    "name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-8",
                    "type": "Microsoft.CostManagement/query",
                    "location": None,
                    "sku": None,
                    "eTag": None,
                    "properties": {
                        "Cost": 0.5107556132017598,
                        "CostUSD": 0.5539016353215431,
                        "ResourceType": "microsoft.network/loadbalancers",
                        "ResourceGroupName": "test1",
                        "Tags": [],
                        "Currency": "EUR",
                    },
                },
                {
                    "id": "subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071",
                    "name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-13",
                    "type": "Microsoft.CostManagement/query",
                    "location": None,
                    "sku": None,
                    "eTag": None,
                    "properties": {
                        "Cost": 0.12006320596267346,
                        "CostUSD": 0.1315116481025144,
                        "ResourceType": "microsoft.recoveryservices/vaults",
                        "ResourceGroupName": "test1",
                        "Tags": [],
                        "Currency": "EUR",
                    },
                },
            ],
            None,
            "<<<<test1>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "Resource\n"
            '{"id": "subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071", '
            '"name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-6", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": '
            'null, "properties": {"Cost": 7.349267385987696, "CostUSD": 7.97158038308434, "ResourceType": "microsoft.network/applicationgateways", '
            '"ResourceGroupName": "test1", "Tags": [], "Currency": "EUR"}, "group": "test1", "tags": {}, "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa", "provider": "Microsoft.CostManagement"}\n'
            "<<<<>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "Resource\n"
            '{"id": '
            '"subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071", '
            '"name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-6", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": '
            'null, "properties": {"Cost": 7.349267385987696, "CostUSD": 7.97158038308434, "ResourceType": "microsoft.network/applicationgateways", '
            '"ResourceGroupName": "test1", "Tags": [], "Currency": "EUR"}, "group": "test1", "tags": {}, "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa", "provider": "Microsoft.CostManagement"}\n'
            "<<<<>>>>\n"
            "<<<<test1>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "Resource\n"
            '{"id": "subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071", '
            '"name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-8", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": '
            'null, "properties": {"Cost": 0.5107556132017598, "CostUSD": 0.5539016353215431, "ResourceType": "microsoft.network/loadbalancers", '
            '"ResourceGroupName": "test1", "Tags": [], "Currency": "EUR"}, "group": "test1", "tags": {}, "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa", "provider": "Microsoft.CostManagement"}\n'
            "<<<<>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "Resource\n"
            '{"id": "subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071", '
            '"name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-8", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": '
            'null, "properties": {"Cost": 0.5107556132017598, "CostUSD": 0.5539016353215431, "ResourceType": "microsoft.network/loadbalancers", '
            '"ResourceGroupName": "test1", "Tags": [], "Currency": "EUR"}, "group": "test1", "tags": {}, "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa", "provider": "Microsoft.CostManagement"}\n'
            "<<<<>>>>\n"
            "<<<<test1>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "Resource\n"
            '{"id": "subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071", '
            '"name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-13", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": '
            'null, "properties": {"Cost": 0.12006320596267346, "CostUSD": 0.1315116481025144, "ResourceType": "microsoft.recoveryservices/vaults", '
            '"ResourceGroupName": "test1", "Tags": [], "Currency": "EUR"}, "group": "test1", "tags": {}, "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa", "provider": "Microsoft.CostManagement"}\n'
            "<<<<>>>>\n"
            "<<<azure_usagedetails:sep(124)>>>\n"
            "Resource\n"
            '{"id": "subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/providers/Microsoft.CostManagement/query/b2ce4915-8c0d-4af7-8979-c561d83a1071", '
            '"name": "b2ce4915-8c0d-4af7-8979-c561d83a1071-13", "type": "Microsoft.Consumption/usageDetails", "location": null, "sku": null, "eTag": '
            'null, "properties": {"Cost": 0.12006320596267346, "CostUSD": 0.1315116481025144, "ResourceType": "microsoft.recoveryservices/vaults", '
            '"ResourceGroupName": "test1", "Tags": [], "Currency": "EUR"}, "group": "test1", "tags": {}, "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa", "provider": "Microsoft.CostManagement"}\n'
            "<<<<>>>>\n",
            id="no errors, usage data exists",
        ),
    ],
)
@pytest.mark.asyncio
@pytest.mark.skip("To be rewritten")
async def test_usage_details(
    args: Args,
    usage_data: Sequence[object],
    exception: Exception,
    expected_result: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # TODO: use new Mocked api client async
    mgmt_client = MockBaseAsyncApiClient(
        [], {}, 0, usage_data=usage_data, usage_details_exception=exception
    )
    monitored_groups = ["test1", "test2"]

    await process_usage_details(mgmt_client, monitored_groups, args)

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
) -> None:
    sections = list(
        _get_resource_health_sections(
            resource_health,
            monitored_resources,
        )
    )

    assert sections == expected_sections, "Sections not as expected"


@pytest.mark.parametrize(
    "rate_limit,expected_output",
    [
        (
            10000,
            "<<<<>>>>\n<<<azure_agent_info:sep(124)>>>\nremaining-reads|10000\n<<<<>>>>\n",
        ),
        (
            None,
            "<<<<>>>>\n<<<azure_agent_info:sep(124)>>>\nremaining-reads|None\n<<<<>>>>\n",
        ),
    ],
)
def test_write_remaining_reads(
    capsys: pytest.CaptureFixture[str], rate_limit: int | None, expected_output: str
) -> None:
    write_remaining_reads(rate_limit)

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
) -> None:
    mock_api_client.get_async.return_value = api_client_mock_return

    selector = Selector(args)
    result_resources, result_groups = await _collect_resources(mock_api_client, args, selector)

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
) -> None:
    resource = AzureResource(
        resource_data,
        tags_pattern,
    )

    assert resource.section == expected_resource.section, "Section mismatch"
    assert resource.info["group"] == expected_resource.info_group, "Info group mismatch"
    assert resource.piggytargets == expected_resource.piggytargets, "Piggy targets mismatch"
    assert resource.tags == expected_resource.tags, "Tags mismatch"
