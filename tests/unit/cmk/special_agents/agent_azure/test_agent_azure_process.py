#!/usr/bin/env python3
# Copyright (C) 2022 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from concurrent.futures import Executor, Future
from typing import Any, TypeVar
from unittest.mock import MagicMock, patch

import pytest

from cmk.utils.http_proxy_config import NoProxyConfig

from cmk.special_agents.agent_azure import (
    _AuthorityURLs,
    ApiError,
    Args,
    AzureResource,
    AzureSection,
    get_group_labels,
    get_vm_labels_section,
    GroupLabels,
    LabelsSection,
    MgmtApiClient,
    process_resource,
    process_resource_health,
    process_vm,
    Section,
    TagsImportPatternOption,
    usage_details,
    write_group_info,
    write_remaining_reads,
    write_section_ad,
)

pytestmark = pytest.mark.checks


T = TypeVar("T")


class FakeExecutor(Executor):
    """Fake executor that runs synchronously for testing."""

    def submit(self, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> Future[T]:
        raise NotImplementedError("not implemented in FakeExecutor")

    def map(
        self,
        fn: Callable[..., T],
        *iterables: Iterable[Any],
        timeout: float | None = None,
        chunksize: int = 1,
    ) -> Iterator[T]:
        # use synchronous map
        return map(fn, *iterables)


class MockMgmtApiClient(MgmtApiClient):
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
            "mock_subscription",
        )

    def resourcegroups(self) -> Sequence[Mapping[str, Any]]:
        return self.resource_groups

    def vmview(self, group: str, name: str) -> Mapping[str, Sequence[Mapping[str, str]]]:
        return self.vmviews[group][name]

    @property
    def ratelimit(self) -> float:
        return self.rate_limit

    def usagedetails(self) -> Sequence[object]:
        if self.usage_details_exception is not None:
            raise self.usage_details_exception

        return self.usage_data

    def resource_health_view(self, resource_group: str) -> object:
        if self.resource_health_exception is not None:
            raise self.resource_health_exception

        return self.resource_health


@pytest.mark.parametrize(
    "mgmt_client, vmach_info, args, expected_info, expected_tags, expected_piggyback_targets",
    [
        (
            MockMgmtApiClient(
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
            MockMgmtApiClient(
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
def test_process_vm(
    mgmt_client: MgmtApiClient,
    vmach_info: Mapping[str, Any],
    args: Args,
    expected_info: Mapping[str, Any],
    expected_tags: Mapping[str, str],
    expected_piggyback_targets: Sequence[str],
) -> None:
    vmach = AzureResource(vmach_info, TagsImportPatternOption.import_all)
    process_vm(mgmt_client, vmach, args)

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


@pytest.mark.parametrize(
    "mgmt_client, resource_info, group_tags, args, expected_result",
    [
        pytest.param(
            MockMgmtApiClient(
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
                "group": "BurningMan",
            },
            {
                "burningman": {
                    "my-resource-tag": "my-resource-value",
                    "resource_group": "burningman",
                }
            },
            Args(
                piggyback_vms="self",
                debug=False,
                services=["Microsoft.Compute/virtualMachines"],
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            [
                (
                    LabelsSection,
                    ["MyVM"],
                    [
                        '{"group_name": "burningman", "vm_instance": true}\n',
                        '{"my-unique-tag": "unique", "tag4all": "True", "my-resource-tag": "my-resource-value", "resource_group": "burningman"}\n',
                    ],
                ),
                (
                    AzureSection,
                    ["MyVM"],
                    [
                        "Resource\n",
                        '{"id": "myid", "name": "MyVM", "type": "Microsoft.Compute/virtualMachines", "location": "westeurope", "tags": {"my-unique-tag": "unique", "tag4all": "True"}, "group": "burningman", "specific_info": {"statuses": [{"code": "ProvisioningState/succeeded", "level": "Info", "displayStatus": "Provisioning succeeded", "time": "2019-11-25T07:38:14.6999403+00:00"}]}}\n',
                    ],
                ),
            ],
            id="vm_with_labels",
        ),
        pytest.param(
            MockMgmtApiClient(
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
                "group": "BurningMan",
            },
            {
                "BurningMan": {
                    "my-resource-tag": "my-resource-value",
                    "cmk/azure/resource_group": "BurningMan",
                }
            },
            Args(
                piggyback_vms="grouphost",
                debug=False,
                services=["Microsoft.Compute/virtualMachines"],
                tag_key_pattern=TagsImportPatternOption.import_all,
            ),
            [
                (
                    AzureSection,
                    ["burningman"],
                    [
                        "Resource\n",
                        '{"id": "myid", "name": "MyVM", "type": "Microsoft.Compute/virtualMachines", "location": "westeurope", "tags": {"my-unique-tag": "unique", "tag4all": "True"}, "group": "burningman", "specific_info": {"statuses": [{"code": "ProvisioningState/succeeded", "level": "Info", "displayStatus": "Provisioning succeeded", "time": "2019-11-25T07:38:14.6999403+00:00"}]}}\n',
                    ],
                ),
            ],
            id="vm",
        ),
        pytest.param(
            MockMgmtApiClient(
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
                "name": "MyVM",
                "type": "Microsoft.Compute/virtualMachines",
                "location": "westeurope",
                "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                "group": "BurningMan",
            },
            {
                "BurningMan": {
                    "my-resource-tag": "my-resource-value",
                    "cmk/azure/resource_group": "BurningMan",
                }
            },
            Args(
                piggyback_vms="grouphost",
                debug=False,
                services=[""],
                tag_key_pattern=TagsImportPatternOption.ignore_all,
            ),
            [],
            id="vm_disabled_service",
        ),
    ],
)
@patch("cmk.special_agents.agent_azure.gather_metrics", return_value=None)
def test_process_resource(
    mock_gather_metrics: MagicMock,
    mgmt_client: MgmtApiClient,
    resource_info: Mapping[str, Any],
    group_tags: GroupLabels,
    args: Args,
    expected_result: Sequence[tuple[type[Section], Sequence[str], Sequence[str]]],
) -> None:
    resource = AzureResource(resource_info, args.tag_key_pattern)
    sections = process_resource(mgmt_client, resource, group_tags, args)
    assert len(sections) == len(expected_result)
    for section, expected_section in zip(sections, expected_result):
        assert isinstance(section, expected_section[0])
        assert section._piggytargets == expected_section[1]
        assert section._cont == expected_section[2]


@pytest.mark.parametrize(
    "mgmt_client, monitored_groups, expected_result",
    [
        (
            MockMgmtApiClient(
                [{"name": "BurningMan", "tags": {"my-resource-tag": "my-resource-value"}}], {}, 2.0
            ),
            ["burningman"],
            {"burningman": {"my-resource-tag": "my-resource-value"}},
        )
    ],
)
def test_get_group_labels(
    mgmt_client: MgmtApiClient, monitored_groups: Sequence[str], expected_result: GroupLabels
) -> None:
    group_tags = get_group_labels(mgmt_client, monitored_groups, TagsImportPatternOption.import_all)
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
    "enabled_services",
    [
        [],
        ["users_count"],
        ["users_count", "ad_connect", "non_existing_service"],
    ],
)
def test_write_section_ad(enabled_services: list[str]) -> None:
    graph_client = MagicMock()
    graph_client.users.return_value = {"key": "users_data"}
    graph_client.organization.return_value = {"key": "organization_data"}
    azure_section = MagicMock()
    write_section_ad(graph_client, azure_section, Args(services=enabled_services))

    if "users_count" in enabled_services:
        graph_client.users.assert_called()
    else:
        graph_client.users.assert_not_called()

    if "ad_connect" in enabled_services:
        graph_client.organization.assert_called()
    else:
        graph_client.organization.assert_not_called()


@pytest.mark.parametrize(
    "args, usage_data, exception, expected_result",
    [
        pytest.param(
            Args(debug=False, services=[], tag_key_pattern=TagsImportPatternOption.import_all),
            None,
            None,
            "",
            id="usage section not enabled",
        ),
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
def test_usage_details(
    args: Args,
    usage_data: Sequence[object],
    exception: Exception,
    expected_result: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    mgmt_client = MockMgmtApiClient(
        [], {}, 0, usage_data=usage_data, usage_details_exception=exception
    )
    monitored_groups = ["test1", "test2"]

    usage_details(mgmt_client, monitored_groups, args)

    captured = capsys.readouterr()
    assert captured.out == expected_result


@pytest.mark.parametrize(
    "monitored_resources,resource_health,expected_output",
    [
        pytest.param(
            [
                AzureResource(
                    {
                        "id": "/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test1/providers/Microsoft.Compute/virtualMachines/VM-test-1",
                        "name": "VM-test-1",
                        "type": "Microsoft.Compute/virtualMachines",
                        "location": "uksouth",
                        "zones": ["1"],
                        "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa",
                        "group": "test1",
                        "provider": "Microsoft.Compute",
                    },
                    TagsImportPatternOption.import_all,
                )
            ],
            [
                {
                    "id": "/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourcegroups/test1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current",
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
            ],
            "<<<<test1>>>>\n"
            "<<<azure_resource_health:sep(0)>>>\n"
            '{"id": "/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourcegroups/test1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current", "name": "virtualmachines/vm-test-1", "availabilityState": "Available", "summary": "There aren\'t any known Azure platform problems affecting this virtual machine.", "reasonType": "", "occuredTime": "2023-02-09T16: 19: 01Z", "tags": {}}\n'
            "<<<<>>>>\n",
            id="virtual_machine",
        ),
        pytest.param(
            [
                AzureResource(
                    {
                        "id": "/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test1/providers/Microsoft.Compute/virtualMachines/VM-test-1",
                        "name": "VM-test-1",
                        "type": "Microsoft.Compute/virtualMachines",
                        "location": "uksouth",
                        "zones": ["1"],
                        "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa",
                        "group": "test1",
                        "provider": "Microsoft.Compute",
                        "tags": {"tag1": "value1"},
                    },
                    TagsImportPatternOption.import_all,
                )
            ],
            [
                {
                    "id": "/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourcegroups/test1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current",
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
            ],
            "<<<<test1>>>>\n"
            "<<<azure_resource_health:sep(0)>>>\n"
            '{"id": "/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourcegroups/test1/providers/microsoft.compute/virtualmachines/vm-test-1/providers/Microsoft.ResourceHealth/availabilityStatuses/current", "name": "virtualmachines/vm-test-1", "availabilityState": "Available", "summary": "There aren\'t any known Azure platform problems affecting this virtual machine.", "reasonType": "", "occuredTime": "2023-02-09T16: 19: 01Z", "tags": {"tag1": "value1"}}\n'
            "<<<<>>>>\n",
            id="virtual_machine_import_tags",
        ),
        pytest.param(
            [],
            [],
            "",
            id="no_resource",
        ),
    ],
)
def test_process_resource_health(
    capsys: pytest.CaptureFixture[str],
    monitored_resources: Sequence[AzureResource],
    resource_health: object,
    expected_output: str,
) -> None:
    mgmt_client = MockMgmtApiClient([], {}, 0, resource_health=resource_health)

    sections = list(
        process_resource_health(
            mgmt_client,
            monitored_resources,
            Args(debug=True, services=["Microsoft.Compute/virtualMachines"]),
            FakeExecutor(),
        )
    )

    for section in sections:
        section.write()

    captured = capsys.readouterr()
    assert captured.out == expected_output


def test_process_resource_health_request_error(capsys: pytest.CaptureFixture[str]) -> None:
    mgmt_client = MockMgmtApiClient(
        [], {}, 0, resource_health_exception=Exception("Request failed")
    )

    list(
        process_resource_health(
            mgmt_client,
            [
                AzureResource(
                    {
                        "id": "/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test1/providers/Microsoft.Compute/virtualMachines/VM-test-1",
                        "name": "VM-test-1",
                        "type": "Microsoft.Compute/virtualMachines",
                        "location": "uksouth",
                        "zones": ["1"],
                        "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa",
                        "group": "test1",
                        "provider": "Microsoft.Compute",
                        "tags": {"tag1": "value1"},
                    },
                    TagsImportPatternOption.import_all,
                )
            ],
            Args(debug=False),
            FakeExecutor(),
        )
    )

    captured = capsys.readouterr()
    assert captured.out == (
        "<<<<>>>>\n"
        "<<<azure_agent_info:sep(124)>>>\n"
        'agent-bailout|[2, "Management client: Request failed"]\n'
        "<<<<>>>>\n"
    )


def test_process_resource_health_request_error_debug(capsys: pytest.CaptureFixture[str]) -> None:
    mgmt_client = MockMgmtApiClient(
        [], {}, 0, resource_health_exception=Exception("Request failed")
    )

    with pytest.raises(Exception, match="Request failed"):
        list(
            process_resource_health(
                mgmt_client,
                [
                    AzureResource(
                        {
                            "id": "/subscriptions/4db89361-bcd9-4353-8edb-33f49608d4fa/resourceGroups/test1/providers/Microsoft.Compute/virtualMachines/VM-test-1",
                            "name": "VM-test-1",
                            "type": "Microsoft.Compute/virtualMachines",
                            "location": "uksouth",
                            "zones": ["1"],
                            "subscription": "4db89361-bcd9-4353-8edb-33f49608d4fa",
                            "group": "test1",
                            "provider": "Microsoft.Compute",
                            "tags": {"tag1": "value1"},
                        },
                        TagsImportPatternOption.import_all,
                    )
                ],
                Args(debug=True),
                FakeExecutor(),
            )
        )


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
