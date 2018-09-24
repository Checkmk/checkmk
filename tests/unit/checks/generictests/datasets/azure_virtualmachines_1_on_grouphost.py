checkname = "azure_virtualmachines"

info = [
    ['Resource'],
    [
        '{"group": "non-existent-testhost", "name": "provfailedserv", "tags": {"monitoring-vm": "true",'
        '"monitoring-all": "true"}, "specific_info": {"statuses": [{"display_status": "Provisioning'
        'failed", "message": "This VM has been stopped as a warning to non-paying subscription.",'
        '"code": "ProvisioningState/failed/VMStoppedToWarnSubscription", "level": "Error", "time":'
        '"2018-10-17T12:51:48.649071Z"}, {"display_status": "VM stopped", "code": "PowerState/stopped",'
        '"level": "Info"}]}, "location": "westeurope", "provider": "Microsoft.Compute", "type":'
        '"Microsoft.Compute/virtualMachines", "id": "/subscriptions/2fac104f-cb9c-461d-be57-03703966'
        '2426/resourceGroups/non-existent-testhost/providers/Microsoft.Compute/virtualMachines/provfailedserv",'
        '"subscription": "2fac104f-cb9c-461d-be57-037039662426"}'
    ],
    ['Resource'],
    [
        '{"provider": "Microsoft.Compute", "group": "non-existent-testhost", "location":'
        ' "westeurope", "tags": {}, "specific_info": {"statuses":'
        ' [{"display_status": "Provisioning succeeded", "level": "Info", "code":'
        ' "ProvisioningState/succeeded", "time": "2018-09-24T09:27:03.635689Z"},'
        ' {"display_status": "VM deallocated", "code": "PowerState/deallocated",'
        ' "level": "Info"}]}, "subscription": "2fac104f-cb9c-461d-be57-037039662426",'
        ' "type": "Microsoft.Compute/virtualMachines", "id":'
        ' "/subscriptions/2fac104f-cb9c-461d-be57-037039662426/resourceGroups/'
        'non-existent-testhost/providers/Microsoft.Compute/virtualMachines/NotRunningUbuntu",'
        ' "identity": {"tenant_id": "93176ea2-ff16-46e0-b84e-862fba579335",'
        ' "principal_id": "eab14ee4-9bd3-4771-889f-7b94c401fe63", "type":'
        ' "SystemAssigned"}, "name": "NotRunningUbuntu"}'
    ],
    ['Resource'],
    [
        '{"group": "non-existent-testhost", "name": "winserv2016", "tags": {"monitoring-vm":'
        ' "true", "monitoring-all": "true"}, "specific_info": {"statuses":'
        ' [{"display_status": "Provisioning succeeded", "level": "Info", "code":'
        ' "ProvisioningState/succeeded", "time": "2018-09-19T12:20:22.400788Z"},'
        ' {"display_status": "VM running", "code": "PowerState/running", "level":'
        ' "Info"}]}, "location": "westeurope", "provider": "Microsoft.Compute",'
        ' "type": "Microsoft.Compute/virtualMachines", "id":'
        ' "/subscriptions/2fac104f-cb9c-461d-be57-037039662426/resourceGroups/'
        'non-existent-testhost/providers/Microsoft.Compute/virtualMachines/winserv2016",'
        ' "subscription": "2fac104f-cb9c-461d-be57-037039662426"}'
    ],
    ['metrics following', '9'],
    ['name', 'aggregation', 'value', 'unit', 'timestamp', 'timegrain', 'filters'],
    ['Percentage CPU', 'average', '0.66', 'percent', '1537797300', 'PT1M', 'None'],
    ['Network In', 'average', '5459.12765957', 'bytes', '1537797300', 'PT1M', 'None'],
    ['Network Out', 'average', '8545.80851064', 'bytes', '1537797300', 'PT1M', 'None'],
    ['Disk Read Bytes', 'average', '0.0', 'bytes', '1537797300', 'PT1M', 'None'],
    ['Disk Write Bytes', 'average', '852331.78', 'bytes', '1537797300', 'PT1M', 'None'],
    [
        'Disk Read Operations/Sec', 'average', '0.0', 'count_per_second', '1537797300',
        'PT1M', 'None'
    ],
    [
        'Disk Write Operations/Sec', 'average', '2.41', 'count_per_second', '1537797300',
        'PT1M', 'None'
    ],
    ['Inbound Flows', 'average', '36.0', 'count', '1537797360', 'PT1M', 'None'],
    ['Outbound Flows', 'average', '36.0', 'count', '1537797360', 'PT1M', 'None'],
]

discovery = {
    'summary': [(None, {})],
    '': [
        ("provfailedserv", {}),
        ("NotRunningUbuntu", {}),
        ("winserv2016", {}),
    ],
}

checks = {
    'summary': [(None, "default", [
        (2, "Provisioning: 1 failed (warn/crit at 1/1) / 2 succeeded", []),
        (0, "Power states: 1 deallocated / 1 running / 1 stopped", []),
        (0, "provfailedserv: Provisioning failed, VM stopped, Resource group: non-existent-testhost\n", []),
        (0, "NotRunningUbuntu: Provisioning succeeded, VM deallocated, Resource group: non-existent-testhost\n", []),
        (0, "winserv2016: Provisioning succeeded, VM running, Resource group: non-existent-testhost\n", []),
    ]),],
    '': [
        ("provfailedserv", "default", [
            (2,
             "Provisioning failed (This VM has been stopped as a warning to non-paying subscription.)",
             []),
            (1, "VM stopped", []),
            (0, u'Location: westeurope', []),
            (0, u'Monitoring-vm: true', []),
            (0, u'Monitoring-all: true', []),
        ]),
        ("NotRunningUbuntu", "default", [
            (0, "Provisioning succeeded", []),
            (0, "VM deallocated", []),
            (0, u'Location: westeurope', []),
        ]),
        ("winserv2016", "default", [
            (0, "Provisioning succeeded", []),
            (0, "VM running", []),
            (0, u'Location: westeurope', []),
            (0, u'Monitoring-vm: true', []),
            (0, u'Monitoring-all: true', []),
        ]),
    ],
}
