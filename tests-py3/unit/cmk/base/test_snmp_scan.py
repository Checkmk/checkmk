# pylint: disable=protected-access
import pytest  # type: ignore[import]

import cmk.base.config as config
import cmk.base.check_api as check_api
import cmk.base.snmp_scan as snmp_scan

from cmk.base.api.agent_based.register.section_plugins_legacy_scan_function import (
    create_detect_spec,)

config.load_all_checks(check_api.get_check_api_context)

SNMP_SCAN_FUNCTIONS = config.snmp_scan_functions.copy()


@pytest.mark.parametrize(
    "name, oids_data, expected_result",
    [
        (
            "quanta_fan",
            {
                '.1.3.6.1.2.1.1.2.0': '.1.3.6.1.4.1.8072.3.2.10'
            },
            False,
        ),
        (
            "quanta_fan",
            {
                '.1.3.6.1.2.1.1.2.0': '.1.3.6.1.4.1.8072.3.2.10',
                '.1.3.6.1.4.1.7244.1.2.1.1.1.0': "exists"
            },
            True,
        ),
        # make sure casing is ignored
        (
            "hwg_temp",
            {
                ".1.3.6.1.2.1.1.1.0": "contains lower HWG"
            },
            True,
        ),
        (
            "aironet_clients",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.5251"
            },
            False,
        ),
        (
            "aironet_clients",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.9.1.525"
            },
            True,
        ),
        # for one example do all 6 permutations:
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.1588.Moo",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None"
            },
            True,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.4.1.1588.Moo",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None
            },
            False,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.24.1.1588.2.1.1.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None"
            },
            True,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": ".1.3.6.1.24.1.1588.2.1.1.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None
            },
            False,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": "Moo.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": "Not None"
            },
            False,
        ),
        (
            "brocade_info",
            {
                ".1.3.6.1.2.1.1.2.0": "Moo.Quack",
                ".1.3.6.1.4.1.1588.2.1.1.1.1.6.0": None
            },
            False,
        ),
    ])
def test_snmp_can_functions(name, oids_data, expected_result):
    def oid_function(oid, default=None):
        return oids_data.get(oid, default)

    scan_function = SNMP_SCAN_FUNCTIONS[name]

    assert bool(scan_function(oid_function)) is expected_result

    converted_detect_spec = create_detect_spec(name, scan_function, [])
    actual_result = snmp_scan._evaluate_snmp_detection(oid_function, converted_detect_spec)
    assert actual_result is expected_result
