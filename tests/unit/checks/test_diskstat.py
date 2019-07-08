import pytest

from checktestlib import CheckResult, assertCheckResultsEqual

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("item, params, disks, expected", [
    ("sda", {
        'average': 0.0,
        'read_ios': (200.0, 300.0),
        'write_ios': (400.0, 500.0),
        'latency': 0.0,
        'latency_perfdata': 0.0,
        'read_ql': 0.0,
        'write_ql': 0.0,
        'ql_perfdata': 0.0,
    }, {
        "sda": {
            'node': 'node_name',
            'read_ios': 201.0,
            'write_ios': 401.0,
            'read_throughput': 0.0,
            'write_throughput': 0.0,
            'utilization': 0.0,
            'latency': 0.0,
            'average_request_size': 0.0,
            'average_wait': 0.0,
            'average_read_wait': 0.0,
            'average_read_request_size': 0.0,
            'average_write_wait': 0.0,
            'average_write_request_size': 0.0,
            'queue_length': 0.0,
        }
    }, [(0, 'Utilization: 0%', [('disk_utilization', 0.0)]),
        (0, 'Read: 0.00 B/s', [('disk_read_throughput', 0.0)]),
        (0, 'Write: 0.00 B/s', [('disk_write_throughput', 0.0)]),
        (0, 'Average Wait: 0.00 ms', [('disk_average_wait', 0.0)]),
        (0, 'Average Read Wait: 0.00 ms', [('disk_average_read_wait', 0.0)]),
        (0, 'Average Write Wait: 0.00 ms', [('disk_average_write_wait', 0.0)]),
        (0, 'Latency: 0.00 ms', [('disk_latency', 0.0)]),
        (0, 'Average Queue Length: 0.00', [('disk_queue_length', 0.0)]),
        (1, 'Read operations: 201.00 1/s (warn/crit at 200.00 1/s/300.00 1/s)', [
            ('disk_read_ios', 201.0, 200.0, 300.0)
        ]),
        (1, 'Write operations: 401.00 1/s (warn/crit at 400.00 1/s/500.00 1/s)', [
            ('disk_write_ios', 401.0, 400.0, 500.0)
        ]),
        (0, '', [('disk_average_read_request_size', 0.0), ('disk_average_request_size', 0.0),
                 ('disk_average_write_request_size', 0.0)])]),
    ("sda", {
        'average': 0.0,
        'read_ios': (200.0, 300.0),
        'write_ios': (400.0, 500.0),
        'latency': 0.0,
        'latency_perfdata': 0.0,
        'read_ql': 0.0,
        'write_ql': 0.0,
        'ql_perfdata': 0.0,
    }, {
        "sda": {
            'node': 'node_name',
            'read_ios': 301.0,
            'write_ios': 501.0,
            'read_throughput': 0.0,
            'write_throughput': 0.0,
            'utilization': 0.0,
            'latency': 0.0,
            'average_request_size': 0.0,
            'average_wait': 0.0,
            'average_read_wait': 0.0,
            'average_read_request_size': 0.0,
            'average_write_wait': 0.0,
            'average_write_request_size': 0.0,
            'queue_length': 0.0,
        }
    }, [(0, 'Utilization: 0%', [('disk_utilization', 0.0)]),
        (0, 'Read: 0.00 B/s', [('disk_read_throughput', 0.0)]),
        (0, 'Write: 0.00 B/s', [('disk_write_throughput', 0.0)]),
        (0, 'Average Wait: 0.00 ms', [('disk_average_wait', 0.0)]),
        (0, 'Average Read Wait: 0.00 ms', [('disk_average_read_wait', 0.0)]),
        (0, 'Average Write Wait: 0.00 ms', [('disk_average_write_wait', 0.0)]),
        (0, 'Latency: 0.00 ms', [('disk_latency', 0.0)]),
        (0, 'Average Queue Length: 0.00', [('disk_queue_length', 0.0)]),
        (2, 'Read operations: 301.00 1/s (warn/crit at 200.00 1/s/300.00 1/s)', [
            ('disk_read_ios', 301.0, 200.0, 300.0)
        ]),
        (2, 'Write operations: 501.00 1/s (warn/crit at 400.00 1/s/500.00 1/s)', [
            ('disk_write_ios', 501.0, 400.0, 500.0)
        ]),
        (0, '', [('disk_average_read_request_size', 0.0), ('disk_average_request_size', 0.0),
                 ('disk_average_write_request_size', 0.0)])])
])
def test_diskstat_dict_warns_and_crits_about_read_and_write_ios(check_manager, item, params, disks,
                                                                expected, monkeypatch):
    check = check_manager.get_check("diskstat")
    check_diskstat_dict = check.context["check_diskstat_dict"]
    with monkeypatch.context() as m:
        m.setattr('time.time', lambda: 0.0)
        actual_result = CheckResult(check_diskstat_dict(item, params, disks))
    expected_result = CheckResult(expected)
    assertCheckResultsEqual(actual_result, expected_result)
