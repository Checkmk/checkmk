# yapf: disable
checkname = 'azure_sites'

info = [
    ['Resource'],
    [
        '{"kind": "functionapp", "group": "cldazspo-solutions-rg", "name": "spo-solutions-fa1", "tags": {"OpLevel": "Operation", "OpHours": "7x24", "CostCenter": "0000252980", "ITProduct": "C89 Collaboration Platform"}, "provider": "Microsoft.Web", "subscription": "e95edb66-81e8-4acd-9ae8-68623f1bf7e6", "type": "Microsoft.Web/sites", "id": "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazspo-solutions-rg/providers/Microsoft.Web/sites/spo-solutions-fa1", "identity": {"tenant_id": "e7b94e3c-1ad5-477d-be83-17106c6c8301", "principal_id": "15c0b993-4efa-4cc1-9880-d68c0f59ed42", "type": "SystemAssigned"}, "location": "westeurope"}'
    ], ['metrics following', '24'],
    ['{"name": "TotalAppDomainsUnloaded", "timestamp": "1536073080", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Gen0Collections", "timestamp": "1536073080", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Gen1Collections", "timestamp": "1536073080", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Gen2Collections", "timestamp": "1536073080", "aggregation": "average", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "BytesReceived", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "BytesSent", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "Http5xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "MemoryWorkingSet", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "AverageMemoryWorkingSet", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "FunctionExecutionUnits", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "FunctionExecutionCount", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "AppConnections", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Handles", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Threads", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "PrivateBytes", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "IoReadBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoWriteBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoOtherBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoReadOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoWriteOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoOtherOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "RequestsInApplicationQueue", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "CurrentAssemblies", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "TotalAppDomains", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['Resource'],
    [
        '{"kind": "app", "group": "cldazpaaswebapp06-rg", "location": "southeastasia", "tags": {"OpLevel": "Operation", "OpHours": "7x24", "CostCenter": "0000252980", "ITProduct": "CUV130_MS_IIS (Internet Information Server) Standard"}, "provider": "Microsoft.Web", "subscription": "e95edb66-81e8-4acd-9ae8-68623f1bf7e6", "type": "Microsoft.Web/sites", "id": "/subscriptions/e95edb66-81e8-4acd-9ae8-68623f1bf7e6/resourceGroups/cldazpaaswebapp06-rg/providers/Microsoft.Web/sites/zcldazwamonseas-as", "name": "zcldazwamonseas-as"}'
    ], ['metrics following', '33'],
    ['{"name": "IoReadBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoWriteBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoOtherBytesPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoReadOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoWriteOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "IoOtherOperationsPerSecond", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes_per_second"}'],
    ['{"name": "RequestsInApplicationQueue", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "CurrentAssemblies", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "TotalAppDomains", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "TotalAppDomainsUnloaded", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Gen0Collections", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Gen1Collections", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Gen2Collections", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "CpuTime", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "seconds"}'],
    ['{"name": "Requests", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "BytesReceived", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "BytesSent", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "Http101", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Http2xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Http3xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Http401", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Http403", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Http404", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Http406", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Http4xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Http5xx", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "MemoryWorkingSet", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "AverageMemoryWorkingSet", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
    ['{"name": "AverageResponseTime", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "seconds"}'],
    ['{"name": "AppConnections", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Handles", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "Threads", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "count"}'],
    ['{"name": "PrivateBytes", "timestamp": "1536073080", "aggregation": "total", "interval_id": "PT1M", "filter": "None", "value": 0.0, "unit": "bytes"}'],
]

discovery = {'': [(u'spo-solutions-fa1', {}), (u'zcldazwamonseas-as', {})]}

checks = {
    '': [(u'spo-solutions-fa1', {
        'cpu_time_percent_levels': (85.0, 95.0),
        'avg_response_time_levels': (1.0, 10.0),
        'error_rate_levels': (0.01, 0.04)
    }, [
        (0, 'Rate of server errors: 0.0', [('error_rate', 0.0, 0.01, 0.04, 0, None)]),
        (0, u'Location: westeurope', []),
        (0, u'CostCenter: 0000252980', []),
        (0, u'ITProduct: C89 Collaboration Platform', []),
        (0, u'OpHours: 7x24', []),
        (0, u'OpLevel: Operation', []),
    ]),
         (u'zcldazwamonseas-as', {
             'cpu_time_percent_levels': (85.0, 95.0),
             'avg_response_time_levels': (1.0, 10.0),
             'error_rate_levels': (0.01, 0.04)
         }, [
             (0, 'CPU time: 0%', [('cpu_time_percent', 0.0, 85.0, 95.0, 0, None)]),
             (0, 'Average response time: 0.00 s', [('avg_response_time', 0.0, 1.0, 10.0, 0, None)]),
             (0, 'Rate of server errors: 0.0', [('error_rate', 0.0, 0.01, 0.04, 0, None)]),
             (0, u'Location: southeastasia', []),
             (0, u'CostCenter: 0000252980', []),
             (0, u'ITProduct: CUV130_MS_IIS (Internet Information Server) Standard', []),
             (0, u'OpHours: 7x24', []),
             (0, u'OpLevel: Operation', []),
         ])]
}
