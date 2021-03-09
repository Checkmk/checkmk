#!/usr/bin/env python3


def test_fortigate_sslvpn_old_params(check_manager):
    check = check_manager.get_check("fortigate_sslvpn")
    parsed = {
        "domain": {
            "state": "1",
            "users": 0,
            "web_sessions": 0,
            "tunnels": 0,
            "tunnels_max": 0,
        },
    }
    check.run_check("no-item", None, parsed)
