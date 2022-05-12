#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2022 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Any, Mapping, Sequence, Tuple, Type

import pytest

from cmk.special_agents.agent_azure import (
    Args,
    AzureResource,
    AzureSection,
    get_group_labels,
    get_vm_labels_section,
    GroupLabels,
    LabelsSection,
    MgmtApiClient,
    process_resource,
    process_vm,
    Section,
    write_group_info,
)

pytestmark = pytest.mark.checks


class MockMgmtApiClient:
    def __init__(
        self,
        resource_groups: Sequence[Mapping[str, Any]],
        vmviews: Mapping[str, Mapping[str, Mapping[str, Sequence[Mapping[str, str]]]]],
        ratelimit: float,
    ) -> None:
        self.resource_groups = resource_groups
        self.vmviews = vmviews
        self.rate_limit = ratelimit

    def resourcegroups(self) -> Sequence[Mapping[str, Any]]:
        return self.resource_groups

    def vmview(self, group_name: str, vm_name: str) -> Mapping[str, Sequence[Mapping[str, str]]]:
        return self.vmviews[group_name][vm_name]

    @property
    def ratelimit(self) -> float:
        return self.rate_limit


@pytest.mark.parametrize(
    "mgmt_client, vmach_info, args, expected_info, expected_tags, expected_piggyback_targets",
    [
        (
            MockMgmtApiClient(
                [],
                {
                    "BurningMan": {
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
            Args(piggyback_vms="self"),
            {
                "group": "BurningMan",
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
            ["MyVM"],
        ),
        (
            MockMgmtApiClient(
                [],
                {
                    "BurningMan": {
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
            Args(piggyback_vms="grouphost"),
            {
                "group": "BurningMan",
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
            ["BurningMan"],
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
):
    vmach = AzureResource(vmach_info)
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
                }
            ),
            {
                "BurningMan": {
                    "my-resource-tag": "my-resource-value",
                    "resource_group": "BurningMan",
                }
            },
            (
                [
                    '{"my-unique-tag": "unique", "tag4all": "True", "my-resource-tag": "my-resource-value", "resource_group": "BurningMan"}\n'
                ],
                ["MyVM"],
            ),
        )
    ],
)
def test_get_vm_labels_section(
    vm: AzureResource, group_tags: GroupLabels, expected_result: Tuple[Sequence[str], Sequence[str]]
):
    labels_section = get_vm_labels_section(vm, group_tags)

    assert labels_section
    assert labels_section._cont == expected_result[0]
    assert labels_section._piggytargets == expected_result[1]


@pytest.mark.parametrize(
    "mgmt_client, resource_info, group_tags, args, expected_result",
    [
        (
            MockMgmtApiClient(
                [],
                {
                    "BurningMan": {
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
                    "resource_group": "BurningMan",
                }
            },
            Args(piggyback_vms="self", debug=False),
            [
                (
                    LabelsSection,
                    ["MyVM"],
                    [
                        '{"my-unique-tag": "unique", "tag4all": "True", "my-resource-tag": "my-resource-value", "resource_group": "BurningMan"}\n'
                    ],
                ),
                (AzureSection, [""], ["remaining-reads|2.0\n"]),
                (
                    AzureSection,
                    ["MyVM"],
                    [
                        "Resource\n",
                        '{"id": "myid", "name": "MyVM", "type": "Microsoft.Compute/virtualMachines", "location": "westeurope", "tags": {"my-unique-tag": "unique", "tag4all": "True"}, "group": "BurningMan", "specific_info": {"statuses": [{"code": "ProvisioningState/succeeded", "level": "Info", "displayStatus": "Provisioning succeeded", "time": "2019-11-25T07:38:14.6999403+00:00"}]}}\n',
                    ],
                ),
            ],
        ),
        (
            MockMgmtApiClient(
                [],
                {
                    "BurningMan": {
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
                    "resource_group": "BurningMan",
                }
            },
            Args(piggyback_vms="grouphost", debug=False),
            [
                (AzureSection, [""], ["remaining-reads|2.0\n"]),
                (
                    AzureSection,
                    ["BurningMan"],
                    [
                        "Resource\n",
                        '{"id": "myid", "name": "MyVM", "type": "Microsoft.Compute/virtualMachines", "location": "westeurope", "tags": {"my-unique-tag": "unique", "tag4all": "True"}, "group": "BurningMan", "specific_info": {"statuses": [{"code": "ProvisioningState/succeeded", "level": "Info", "displayStatus": "Provisioning succeeded", "time": "2019-11-25T07:38:14.6999403+00:00"}]}}\n',
                    ],
                ),
            ],
        ),
    ],
)
def test_process_resource(
    mgmt_client: MgmtApiClient,
    resource_info: Mapping[str, Any],
    group_tags: GroupLabels,
    args: Args,
    expected_result: Sequence[Tuple[Type[Section], Sequence[str], Sequence[str]]],
):
    resource = AzureResource(resource_info)
    function_args = (mgmt_client, resource, group_tags, args)
    sections = process_resource(function_args)
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
            ["BurningMan"],
            {
                "BurningMan": {
                    "my-resource-tag": "my-resource-value",
                    "resource_group": "BurningMan",
                }
            },
        )
    ],
)
def test_get_group_labels(
    mgmt_client: MgmtApiClient, monitored_groups: Sequence[str], expected_result: GroupLabels
):
    group_tags = get_group_labels(mgmt_client, monitored_groups)
    assert group_tags == expected_result


@pytest.mark.parametrize(
    "monitored_groups, monitored_resources, group_tags, expected_result",
    [
        (
            ["BurningMan"],
            [
                AzureResource(
                    {
                        "id": "myid",
                        "name": "MyVM",
                        "type": "Microsoft.Compute/virtualMachines",
                        "location": "westeurope",
                        "tags": {"my-unique-tag": "unique", "tag4all": "True"},
                        "group": "BurningMan",
                    }
                ),
            ],
            {
                "BurningMan": {
                    "my-resource-tag": "my-resource-value",
                    "resource_group": "BurningMan",
                }
            },
            "<<<<BurningMan>>>>\n"
            "<<<labels:sep(0)>>>\n"
            '{"my-resource-tag": "my-resource-value", "resource_group": "BurningMan"}\n'
            "<<<<>>>>\n"
            "<<<<>>>>\n"
            "<<<azure_agent_info:sep(124)>>>\n"
            'monitored-groups|["BurningMan"]\n'
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
    capsys,
):
    write_group_info(monitored_groups, monitored_resources, group_tags)
    captured = capsys.readouterr()
    assert captured.out == expected_result
