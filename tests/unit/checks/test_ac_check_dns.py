import pytest


@pytest.mark.parametrize('params, result', [
    (("DESCR", {}), "-H 'DESCR' -s '$HOSTADDRESS$'"),
    (("DESCR", {
        "expected_address": "1.2.3.4,5.6.7.8",
    }), "-H 'DESCR' -s '$HOSTADDRESS$' -a '1.2.3.4,5.6.7.8'"),
    (("DESCR", {
        "expected_address": "5.6.7.8,1.2.3.4",
    }), "-H 'DESCR' -s '$HOSTADDRESS$' -a '1.2.3.4,5.6.7.8'"),
    (("DESCR", {
        "expected_address": ["1.2.3.4,5.6.7.8"],
    }), "-H 'DESCR' -s '$HOSTADDRESS$' -a '1.2.3.4,5.6.7.8'"),
    (("DESCR", {
        "expected_address": ["5.6.7.8,1.2.3.4"],
    }), "-H 'DESCR' -s '$HOSTADDRESS$' -a '1.2.3.4,5.6.7.8'"),
    (("DESCR", {
        "expected_address": ["1.2.3.4", "5.6.7.8,4.3.2.1"],
    }), "-H 'DESCR' -s '$HOSTADDRESS$' -a '1.2.3.4' -a '4.3.2.1,5.6.7.8'"),
])
def test_ac_check_dns_expected_addresses(check_manager, params, result):
    active_check = check_manager.get_active_check("check_dns")
    assert active_check.run_argument_function(params) == result
