#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

import cmk.utils.password_store

from cmk.notification_plugins.pagerduty import _notification_source_from_context, _pagerduty_msg


@pytest.mark.parametrize(
    "context, result",
    [
        pytest.param(
            {
                "HOSTNAME": "site1",
                "HOSTADDRESS": "127.0.0.1",
            },
            "127.0.0.1",
            id="address_and_name_set",
        ),
        pytest.param(
            {
                "HOSTNAME": "site1",
                "HOSTADDRESS": "",
            },
            "site1",
            id="only_name_set",
        ),
        pytest.param(
            {
                "HOSTNAME": "",
                "HOSTADDRESS": "",
            },
            "Undeclared Host identifier",
            id="no_address_and_name_set",
        ),
        pytest.param(
            {},
            "Undeclared Host identifier",
            id="empty_context",
        ),
    ],
)
def test_notification_source_from_context(context: dict[str, str], result: str) -> None:
    msg = _notification_source_from_context(context)
    assert msg == result


_HOST_CONTEXT = {
    "WHAT": "HOST",
    "NOTIFICATIONTYPE": "PROBLEM",
    "HOSTNAME": "myhost",
    "HOSTADDRESS": "10.0.0.1",
    "HOSTSTATE": "DOWN",
    "HOSTOUTPUT": "Host unreachable",
}


@pytest.mark.parametrize(
    "context, result",
    [
        pytest.param(
            {
                "PARAMETER_URL_PREFIX_1": "automatic_http",
                "PARAMETER_ROUTING_KEY_1": "cmk_postprocessed",
                "PARAMETER_ROUTING_KEY_2": "explicit_password",
                "PARAMETER_ROUTING_KEY_3": "uuidcdd72f8e-1b70-473e-9a5e-8abdb2c42580\tmypassword",
                "PARAMETER_ROUTING_KEY_3_1": "uuidcdd72f8e-1b70-473e-9a5e-8abdb2c42580",
                "PARAMETER_ROUTING_KEY_3_2": "mykey",
                "MONITORING_HOST": "localhost",
                "OMD_SITE": "testsite",
                "HOSTURL": "/view?key=val",
                "SERVICEURL": "/view?key=val2",
                "HOSTNAME": "site1",
                "SERVICEDESC": "first",
                "SERVICESTATE": "CRITICAL",
                "NOTIFICATIONTYPE": "PROBLEM",
                "HOSTADDRESS": "127.0.0.1",
                "SERVICEOUTPUT": "Service Down",
                "WHAT": "SERVICE",
                "CONTACTNAME": "John,Doe",
                "LONGDATETIME": "Wed Sep 19 15:29:14 CEST 2018",
                "SERVICEPERFDATA": "last_updated=20.599114;;;; new_files=0;;;;",
            },
            {
                "dedup_key": "first/site1:127.0.0.1",
                "event_action": "trigger",
                "payload": {
                    "custom_details": {
                        "host": "site1",
                        "host_address": "127.0.0.1",
                        "info": "Service Down",
                    },
                    "severity": "critical",
                    "source": "127.0.0.1",
                    "summary": "CRITICAL: first on site1",
                },
                "routing_key": "mykey",
                "client": "Check_MK",
                "client_url": "http://localhost/testsite/view?key=val2",
            },
            id="notification_service_state",
        ),
        pytest.param(
            {
                "HOSTOUTPUT": "Packet received via smart PING",
                "HOSTADDRESS": "10.3.1.239",
                "PARAMETER_ROUTING_KEY_1": "cmk_postprocessed",
                "PARAMETER_ROUTING_KEY_2": "explicit_password",
                "PARAMETER_ROUTING_KEY_3": "uuidcdd72f8e-1b70-473e-9a5e-8abdb2c42580\tmypassword",
                "PARAMETER_ROUTING_KEY_3_1": "uuidcdd72f8e-1b70-473e-9a5e-8abdb2c42580",
                "PARAMETER_ROUTING_KEY_3_2": "mykey",
                "NOTIFICATIONTYPE": "RECOVERY",
                "HOSTURL": "/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dwin7vm%26site%3Dheute",
                "HOSTNAME": "win7vm",
                "PARAMETER_URL_PREFIX_1": "automatic_http",
                "HOSTSTATE": "UP",
                "OMD_SITE": "heute",
                "MONITORING_HOST": "localhost",
                "WHAT": "HOST",
                "HOSTPERFDATA": "",
            },
            {
                "client": "Check_MK",
                "client_url": "http://localhost/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dwin7vm%26site%3Dheute",
                "dedup_key": "win7vm:10.3.1.239",
                "event_action": "resolve",
                "payload": {
                    "custom_details": {
                        "host": "win7vm",
                        "host_address": "10.3.1.239",
                        "info": "Packet received via smart PING",
                    },
                    "severity": "info",
                    "source": "10.3.1.239",
                    "summary": "win7vm is UP",
                },
                "routing_key": "mykey",
            },
            id="notification_host_state",
        ),
        pytest.param(
            {
                "HOSTOUTPUT": "Packet received via smart PING",
                "HOSTADDRESS": "",
                "PARAMETER_ROUTING_KEY_1": "cmk_postprocessed",
                "PARAMETER_ROUTING_KEY_2": "explicit_password",
                "PARAMETER_ROUTING_KEY_3": "uuidcdd72f8e-1b70-473e-9a5e-8abdb2c42580\tmypassword",
                "PARAMETER_ROUTING_KEY_3_1": "uuidcdd72f8e-1b70-473e-9a5e-8abdb2c42580",
                "PARAMETER_ROUTING_KEY_3_2": "mykey",
                "NOTIFICATIONTYPE": "RECOVERY",
                "HOSTURL": "/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dwin7vm%26site%3Dheute",
                "HOSTNAME": "win7vm",
                "PARAMETER_URL_PREFIX_1": "automatic_http",
                "HOSTSTATE": "UP",
                "OMD_SITE": "heute",
                "MONITORING_HOST": "localhost",
                "WHAT": "HOST",
                "HOSTPERFDATA": "",
            },
            {
                "client": "Check_MK",
                "client_url": "http://localhost/heute/check_mk/index.py?start_url=view.py%3Fview_name%3Dhoststatus%26host%3Dwin7vm%26site%3Dheute",
                "dedup_key": "win7vm:",
                "event_action": "resolve",
                "payload": {
                    "custom_details": {
                        "host": "win7vm",
                        "host_address": "",
                        "info": "Packet received via smart PING",
                    },
                    "severity": "info",
                    "source": "win7vm",
                    "summary": "win7vm is UP",
                },
                "routing_key": "mykey",
            },
            id="notification_host_state_missing_host_address",
        ),
        pytest.param(
            {
                **_HOST_CONTEXT,
                # The format before the key became a password: ("routing_key", "mykey")
                "PARAMETER_ROUTING_KEY": "routing_key\tmykey",
                "PARAMETER_ROUTING_KEY_1": "routing_key",
                "PARAMETER_ROUTING_KEY_2": "mykey",
            },
            {
                "dedup_key": "myhost:10.0.0.1",
                "event_action": "trigger",
                "payload": {
                    "custom_details": {
                        "host": "myhost",
                        "host_address": "10.0.0.1",
                        "info": "Host unreachable",
                    },
                    "severity": "critical",
                    "source": "10.0.0.1",
                    "summary": "myhost is DOWN",
                },
                "routing_key": "mykey",
            },
            id="routing_key_in_format_before_password",
        ),
    ],
)
def test_pagerduty_message(
    context: dict[str, str],
    result: dict[str, str | dict[str, str | dict[str, str | dict[str, str]]]],
) -> None:
    msg = _pagerduty_msg(context)
    assert msg == result


def test_routing_key_stored_as_password_is_read_from_password_store() -> None:
    cmk.utils.password_store.save(
        {"my_key": "mykey"},
        cmk.utils.password_store.pending_password_store_path(),
    )
    context = {
        **_HOST_CONTEXT,
        "PARAMETER_ROUTING_KEY_1": "cmk_postprocessed",
        "PARAMETER_ROUTING_KEY_2": "stored_password",
        "PARAMETER_ROUTING_KEY_3": "my_key\t",
        "PARAMETER_ROUTING_KEY_3_1": "my_key",
        "PARAMETER_ROUTING_KEY_3_2": "",
    }

    assert _pagerduty_msg(context)["routing_key"] == "mykey"


def test_routing_key_from_password_store_in_format_before_password_is_read() -> None:
    cmk.utils.password_store.save(
        {"my_key": "mykey"},
        cmk.utils.password_store.pending_password_store_path(),
    )
    context = {
        **_HOST_CONTEXT,
        "PARAMETER_ROUTING_KEY": "store\tmy_key",
        "PARAMETER_ROUTING_KEY_1": "store",
        "PARAMETER_ROUTING_KEY_2": "my_key",
    }

    assert _pagerduty_msg(context)["routing_key"] == "mykey"


def test_routing_key_without_password_store_id_is_not_sent() -> None:
    cmk.utils.password_store.save(
        {"my_key": "mykey"},
        cmk.utils.password_store.pending_password_store_path(),
    )
    # A rule read through the REST API and written back stored ("store", "")
    context = {
        **_HOST_CONTEXT,
        "PARAMETER_ROUTING_KEY": "store\t",
        "PARAMETER_ROUTING_KEY_1": "store",
        "PARAMETER_ROUTING_KEY_2": "",
    }

    with pytest.raises(SystemExit) as exit_info:
        _pagerduty_msg(context)

    assert exit_info.value.code == 2
