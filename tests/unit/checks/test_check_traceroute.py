import pytest

pytestmark = pytest.mark.checks


@pytest.mark.parametrize("params,expected_args", [
    ({
        "dns": False,
        "routers": [],
        "method": "",
        "address_family": "ipv4",
    }, ["-n", "-4", "$HOSTADDRESS$"]),
    ({
        "dns": True,
        "routers": [],
        "method": "",
        "address_family": "ipv4",
    }, ["-4", "$HOSTADDRESS$"]),
    ({
        "dns": True,
        "routers": [("127.0.0.1", "WARN")],
        "method": "icmp",
        "address_family": "ipv4",
    }, ["-I", "-WARN", "127.0.0.1", "-4", "$HOSTADDRESS$"]),
    ({
        "dns": False,
        "routers": [],
        "method": "",
        "address_family": "ipv4",
    }, ["-n", "-4", "$HOSTADDRESS$"]),
    ({
        "dns": False,
        "routers": [],
        "method": "",
        "address_family": "ipv6",
    }, ["-n", "-6", "$HOSTADDRESS$"]),
])
def test_check_traceroute_argument_parsing(check_manager, params, expected_args):
    """Tests if all required arguments are present."""
    active_check = check_manager.get_active_check("check_traceroute")
    assert active_check.run_argument_function(params) == expected_args
