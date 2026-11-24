#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"
# mypy: disable-error-code="type-arg"

import socket
from typing import Any

from cmk.ccc.user import UserId
from cmk.ec.config import (
    ECRulePackSpec,
    EventLimit,
    Rule,
    ServiceLevel,
    State,
)
from cmk.gui.watolib.site_changes import ChangeSpec
from tests.testlib.system.site import Site


class CMKEventConsole:
    def __init__(self, site: Site) -> None:
        super().__init__()
        self.site = site
        self.status = CMKEventConsoleStatus(f"{site.root}/tmp/run/mkeventd/status")


class CMKEventConsoleStatus:
    def __init__(self, address: str) -> None:
        self._address = address

    # Copied from web/htdocs/mkeventd.py. Better move to some common lib.
    def query(self, query: str) -> Any:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        timeout = 10

        sock.settimeout(timeout)
        sock.connect(self._address)
        sock.sendall(query.encode("utf-8"))
        sock.shutdown(socket.SHUT_WR)

        response_text = b""
        while True:
            chunk = sock.recv(8192)
            response_text += chunk
            if not chunk:
                break

        return eval(response_text)

    def query_table_assoc(self, query: str) -> list[dict]:
        response = self.query(query)
        headers = response[0]
        result = []
        for line in response[1:]:
            result.append(dict(zip(headers, line)))
        return result

    def query_value(self, query: str) -> Any:
        return self.query(query)[0][0]


def get_ec_rule_packs(
    rule_id: str, title: str, state: State, match: str, limit: int | None = None
) -> list[ECRulePackSpec]:
    """EC rule to inject in the test-site, which stops creating events at the limit, if given"""
    rule = Rule(
        id=rule_id,
        description="",
        comment="",
        docu_url="",
        disabled=False,
        state=state,
        sl=ServiceLevel(value=0, precedence="message"),
        actions=[],
        actions_in_downtime=True,
        cancel_actions=[],
        cancel_action_phases="always",
        autodelete=False,
        match=match,
        invert_matching=False,
    )
    if limit is not None:
        rule["event_limit"] = EventLimit(action="stop", limit=limit)
    return [
        ECRulePackSpec(
            id=rule_id,
            title=title,
            disabled=False,
            rules=[rule],
        )
    ]


def _get_replication_change() -> ChangeSpec:
    """Replication change to inject in the test-site"""
    return ChangeSpec(
        {
            "id": "",
            "action_name": "edit-rule-pack",
            "text": "Modified rule pack test",
            "object": None,
            "user_id": UserId("cmkadmin"),
            "domains": ["ec"],
            "time": 0,
            "force_sync": True,
            "force_restart": True,
            "force_apache_reload": False,
            "domain_settings": {},
            "prevent_discard_changes": False,
            "diff_text": None,
        }
    )


def write_ec_rule(site: Site, rule: list | None) -> None:
    ec_rules_path = site.path("etc/check_mk/mkeventd.d/wato/rules.mk")
    site.write_file(str(ec_rules_path), f"rule_packs += {rule}" if rule else "")


def activate_ec_changes(site: Site) -> None:
    replication_changes_path = site.path(f"var/check_mk/wato/replication_changes_{site.id}.mk")
    # ABCAppendStore entries are "\0"-terminated; without it the next append concatenates onto ours.
    site.write_file(str(replication_changes_path), f"{_get_replication_change()}\0")
    site.openapi.changes.activate_and_wait_for_completion(force_foreign_changes=True)
