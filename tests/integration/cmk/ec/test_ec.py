import pprint
import subprocess
import time
from collections.abc import Iterator

import pytest

from tests.testlib.site import Site
import re


def _get_ec_rule(rule_id: str, title: str, state: int, match: str) -> list:
    """EC rule to inject in the test-site"""
    return [
        {
            "id": rule_id,
            "title": title,
            "disabled": False,
            "rules": [
                {
                    "id": rule_id,
                    "description": "",
                    "comment": "",
                    "docu_url": "",
                    "disabled": False,
                    "drop": False,
                    "state": state,
                    "sl": {"value": 0, "precedence": "message"},
                    "actions": [],
                    "actions_in_downtime": True,
                    "cancel_actions": [],
                    "cancel_action_phases": "always",
                    "autodelete": False,
                    "event_limit": None,
                    "match": match,
                    "invert_matching": False,
                }
            ],
        },
        {"id": "default", "title": "Default rule pack", "rules": [], "disabled": False},
    ]


def _get_replication_change() -> dict:
    """Replication change to inject in the test-site"""
    return {
        "id": "",
        "action_name": "edit-rule-pack",
        "text": "Modified rule pack test",
        "object": None,
        "user_id": "cmkadmin",
        "domains": ["ec"],
        "time": 0,
        "need_sync": True,
        "need_restart": True,
        "domain_settings": {},
        "prevent_discard_changes": False,
        "diff_text": None,
        "has_been_activated": False,
    }


def _write_ec_rule(site: Site, rule: list | None) -> None:
    ec_rules_path = site.path("etc/check_mk/mkeventd.d/wato/rules.mk")
    site.write_text_file(str(ec_rules_path), f"rule_packs += {rule}" if rule else "")


def _activate_ec_changes(site: Site) -> None:
    replication_changes_path = site.path(f"var/check_mk/wato/replication_changes_{site.id}.mk")
    site.write_text_file(str(replication_changes_path), str(_get_replication_change()))
    site.openapi.activate_changes_and_wait_for_completion(force_foreign_changes=True)


def _generate_event_message(site: Site, message: str) -> None:
    """Generate EC message via Unix socket"""
    events_path = site.path("tmp/run/mkeventd/events")
    cmd = f"sudo su -l {site.id} -c 'echo {message} > {events_path}'"
    rc = subprocess.Popen(  # pylint: disable=consider-using-with
        cmd, encoding="utf-8", shell=True
    ).wait()
    assert rc == 0, "Failed to generate EC message via Unix socket"


def _get_snmp_trap_cmd(event_message: str) -> list:
    return [
        "snmptrap",
        "-v",
        "1",
        "-c",
        "public",
        "127.0.0.1",
        ".1.3.6.1",
        "192.168.178.30",
        "6",
        "17",
        '""',
        ".1.3.6.1",
        "s",
        f'"{event_message}"',
    ]


@pytest.fixture(name="setup_ec", scope="function")
def _setup_ec(site: Site) -> Iterator:
    match = "dummy"
    rule_id = f"test {match}"
    rule_state = 1

    _write_ec_rule(site, _get_ec_rule(title="", rule_id=rule_id, state=rule_state, match=match))

    # in order for the EC rule to take effect, we need to inject a change in the EC domain and
    # perform a changes' activation
    _activate_ec_changes(site)

    yield match, rule_id, rule_state

    # cleanup: remove EC rules and activate changes
    _write_ec_rule(site, rule=None)
    _activate_ec_changes(site)

    # cleanup: archive generated events
    for event_id in site.live.query_column("GET eventconsoleevents\nColumns: event_id\n"):
        resp = site.openapi.post(
            "domain-types/event_console/actions/delete/invoke",
            headers={"Content-Type": "application/json"},
            json={
                "site_id": site.id,
                "filter_type": "by_id",
                "event_id": event_id,
            },
        )

        assert resp.status_code == 204, pprint.pformat(resp.json())


def _change_snmp_trap_receiver(site: Site, enable_receiver: bool = True):
    site.stop()
    assert (
        site.execute(
            ["omd", "config", "set", "MKEVENTD_SNMPTRAP", "on" if enable_receiver else "off"]
        ).wait()
        == 0
    )
    site.start()


def test_ec_rule_match(site: Site, setup_ec: Iterator) -> None:
    """Generate a message matching an EC rule and assert an event is created"""
    match, rule_id, rule_state = setup_ec

    event_message = f"some {match} status"
    _generate_event_message(site, event_message)

    live = site.live

    # retrieve id of matching rule via livestatus query
    queried_rule_ids = live.query_column("GET eventconsolerules\nColumns: rule_id\n")
    assert rule_id in queried_rule_ids

    # retrieve matching event state via livestatus query
    queried_event_states = live.query_column("GET eventconsoleevents\nColumns: event_state\n")
    assert len(queried_event_states) == 1
    assert queried_event_states[0] == rule_state

    # retrieve matching event message via livestatus query
    queried_event_messages = live.query_column("GET eventconsoleevents\nColumns: event_text")
    assert len(queried_event_messages) == 1
    assert queried_event_messages[0] == event_message


def test_ec_rule_no_match(site: Site, setup_ec: Iterator) -> None:
    """Generate a message not matching any EC rule and assert no event is created"""
    match, _, _ = setup_ec
    event_message = "some other status"
    assert match not in event_message

    _generate_event_message(site, event_message)

    live = site.live

    queried_event_states = live.query_column("GET eventconsoleevents\nColumns: event_state\n")
    assert not queried_event_states

    queried_event_messages = live.query_column("GET eventconsoleevents\nColumns: event_text")
    assert not queried_event_messages


def test_ec_rule_match_snmp_trap(site: Site, setup_ec: Iterator) -> None:
    """Generate a message via SNMP trap matching an EC rule and assert an event is created"""
    match, rule_id, rule_state = setup_ec
    event_message = f"some {match} status"

    _change_snmp_trap_receiver(site, enable_receiver=True)

    rc = site.execute(_get_snmp_trap_cmd(event_message)).wait()
    assert rc == 0, "Failed to send message via SNMP trap"

    assert event_message in site.read_file("var/log/mkeventd.log")

    live = site.live

    # retrieve id of matching rule via livestatus query
    queried_rule_ids = live.query_column("GET eventconsolerules\nColumns: rule_id\n")
    assert rule_id in queried_rule_ids

    # retrieve matching event state via livestatus query
    queried_event_states = live.query_column("GET eventconsoleevents\nColumns: event_state\n")
    assert len(queried_event_states) == 1
    assert queried_event_states[0] == rule_state

    # retrieve matching event message via livestatus query
    queried_event_messages = live.query_column("GET eventconsoleevents\nColumns: event_text")
    assert len(queried_event_messages) == 1
    assert event_message in queried_event_messages[0]

    # cleanup: disable SNMP trap receiver
    _change_snmp_trap_receiver(site, enable_receiver=False)


def test_ec_rule_no_match_snmp_trap(site: Site, setup_ec: Iterator) -> None:
    """Generate a message via SNMP trap not matching any EC rule and assert no event is created"""
    match, _, _ = setup_ec
    event_message = "some other status"
    assert match not in event_message

    _change_snmp_trap_receiver(site, enable_receiver=True)

    rc = site.execute(_get_snmp_trap_cmd(event_message)).wait()
    assert rc == 0, "Failed to send message via SNMP trap"

    live = site.live

    queried_event_states = live.query_column("GET eventconsoleevents\nColumns: event_state\n")
    assert not queried_event_states

    queried_event_messages = live.query_column("GET eventconsoleevents\nColumns: event_text")
    assert not queried_event_messages

    # cleanup: disable SNMP trap receiver
    _change_snmp_trap_receiver(site, enable_receiver=False)


def test_ec_global_settings(site: Site, setup_ec: Iterator):
    """Assert that global settings of the EC are applied to the EC

    * Activate SNMP traps translation via EC global rules
    * Send message via SNMP trap
    * Assert SNMP-MIB is found in the event message
    """
    match, _, _ = setup_ec
    event_message = f"some {match} status"

    _change_snmp_trap_receiver(site, enable_receiver=True)

    # activate EC global rules to translate SNMP traps
    ec_global_rules_path = site.path("etc/check_mk/mkeventd.d/wato/global.mk")
    site.write_text_file(str(ec_global_rules_path), "translate_snmptraps = (True, {})")

    _activate_ec_changes(site)

    rc = site.execute(_get_snmp_trap_cmd(event_message)).wait()
    assert rc == 0, "Failed to send message via SNMP trap"

    live = site.live
    time.sleep(1)  # wait to set up connection

    queried_event_messages = live.query_column("GET eventconsoleevents\nColumns: event_text")
    assert len(queried_event_messages) == 1

    pattern = "SNMP.*MIB"  # pattern expected after SNMP traps translation
    match = re.compile(pattern).search(queried_event_messages[0])
    assert match, f"{pattern} not found in the event message"

    # cleanup: disable SNMP trap receiver
    _change_snmp_trap_receiver(site, enable_receiver=False)
