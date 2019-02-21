# yapf: disable
checkname = "azure_virtualmachines"

info = [
    ['Resource'],
    [
        '{"group": "Glastonbury", "name": "non-existent-testhost", "tags": {"monitoring-vm":'
        ' "true", "monitoring-all": "true"}, "specific_info": {"statuses": [{"display_status":'
        ' "Provisioning failed", "message": "This VM has been stopped as a warning to'
        ' non-paying subscription.", "code": "ProvisioningState/failed/VMStoppedToWarn'
        'Subscription", "level": "Error", "time": "2018-10-17T12:51:48.649071Z"},'
        ' {"display_status": "VM stopped", "code": "PowerState/stopped", "level": "Info"}]},'
        ' "location": "westeurope", "provider": "Microsoft.Compute", "type":'
        ' "Microsoft.Compute/virtualMachines", "id": "/subscriptions/2fac104f-cb9c-461d'
        '-be57-037039662426/resourceGroups/Glastonbury/providers/Microsoft.Compute'
        '/virtualMachines/non-existent-testhost",'
        ' "subscription": "2fac104f-cb9c-461d-be57-037039662426"}',
    ],
]

discovery = {
    '': [("non-existent-testhost", {}),],
}

checks = {
    '': [("non-existent-testhost", {
        'map_provisioning_states': {
            'failed': 2,
            'succeeded': 0
        },
        'map_power_states': {
            'deallocating': 0,
            'unknown': 3,
            'running': 0,
            'stopped': 1,
            'stopping': 1,
            'starting': 0,
            'deallocated': 0
        }
    }, [
        (2,
         "Provisioning failed (This VM has been stopped as a warning to non-paying subscription.)",
         []),
        (1, "VM stopped", []),
        (0, "Resource group: Glastonbury", []),
        (0, u'Location: westeurope', []),
        (0, u'Monitoring-all: true', []),
        (0, u'Monitoring-vm: true', []),
    ]),],
}
