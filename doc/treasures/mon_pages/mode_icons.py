#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Put one host per Mode-column icon into a dev site. 🎛️

The Mode column of the new monitoring pages (monitor_all_hosts.py) renders a
small set of icons, each driven by a different piece of monitoring state. This
script builds that state in a site: it creates one host named after every icon,
configures the rules and time period the period-based icons need, activates,
fires the Livestatus commands the rest need, and finally reports which icons
each host actually ends up showing.

The crash icon is the one exception: it exists only for services, so its host
carries a passive service that reports the crash marker instead.

Usage:
  mode_icons.py                       populate the only site on this machine
  mode_icons.py --site heute          populate a named site
  mode_icons.py --verify              only report, change nothing
  mode_icons.py --cleanup             remove everything the script created

Credentials default to the dev-site pair cmkadmin/cmk; override with
--user/--password or the CMK_PASSWORD environment variable.

Livestatus commands go through the site's UNIX socket. Run this as the site
user to talk to it directly; as any other user the script falls back to
`sudo -u <site> unixcat`.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

FOLDER_NAME = "mode_icons"
FOLDER_PATH = f"/{FOLDER_NAME}"
TIMEPERIOD = "mode_icons_never"
RULE_TAG = "cmk-mode-icons"
COMMENT = "Mode icon demo"
REACHABLE_IP = "127.0.0.1"
UNREACHABLE_IP = "192.0.2.1"
CRASH_SERVICE = "Crashed check"
CRASH_MARKER = "check failed - please submit a crash report!"
CRASH_OUTPUT = f"{CRASH_MARKER} (Crash-ID: 00000000-0000-0000-0000-000000000000)"
UNKNOWN_STATE = 3


@dataclass(frozen=True)
class ModeIcon:
    """One icon of the Mode column, and what it takes to make an object show it."""

    name: str
    title: str
    ip_address: str = REACHABLE_IP
    rule: tuple[str, str] | None = None
    down: bool = False
    service: str = ""

    @property
    def attributes(self) -> dict[str, str]:
        return {
            "alias": self.title,
            "ipaddress": self.ip_address,
            "tag_agent": "no-agent",
            "tag_snmp_ds": "no-snmp",
        }


def _never(ruleset: str) -> tuple[str, str]:
    return ruleset, repr(TIMEPERIOD)


MODE_ICONS: tuple[ModeIcon, ...] = (
    ModeIcon("downtime", "In scheduled downtime"),
    ModeIcon("ack", "Problem acknowledged", ip_address=UNREACHABLE_IP, down=True),
    ModeIcon("notif-disabled", "Notifications are disabled for this host"),
    ModeIcon("comment", "This host has 1 comment"),
    ModeIcon("disabled", "Active checks have been manually disabled for this host"),
    ModeIcon("npassive", "Passive checks have been manually disabled for this host"),
    ModeIcon(
        "outofnot",
        "Out of notification period",
        rule=_never("extra_host_conf:notification_period"),
    ),
    ModeIcon(
        "outof-serviceperiod",
        "Out of service period",
        rule=_never("extra_host_conf:service_period"),
    ),
    ModeIcon(
        "pause",
        "This host is currently not being checked",
        rule=_never("extra_host_conf:check_period"),
    ),
    ModeIcon(
        "crash",
        "This check crashed",
        rule=("custom_checks", repr({"service_description": CRASH_SERVICE})),
        service=CRASH_SERVICE,
    ),
)

SERVICE_COLUMNS = ("host_name", "description", "state", "plugin_output")

LIVESTATUS_COLUMNS = (
    "name",
    "acknowledged",
    "scheduled_downtime_depth",
    "notifications_enabled",
    "comments",
    "modified_attributes_list",
    "active_checks_enabled",
    "accept_passive_checks",
    "in_notification_period",
    "in_service_period",
    "in_check_period",
    "state",
    "has_been_checked",
)


class ApiError(RuntimeError):
    pass


class RestApi:
    """The site's REST API, over plain stdlib HTTP."""

    def __init__(self, base_url: str, user: str, password: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._auth = f"Bearer {user} {password}"
        self.user = user

    def get(self, path: str, query: Mapping[str, str] | None = None, **kwargs: object) -> dict:
        suffix = ""
        if query:
            suffix = "?" + "&".join(f"{k}={urllib.parse.quote(v)}" for k, v in query.items())
        return self._call("GET", path + suffix, **kwargs)

    def post(self, path: str, body: Mapping[str, object], **kwargs: object) -> dict:
        return self._call("POST", path, body, **kwargs)

    def delete(self, path: str, **kwargs: object) -> dict:
        return self._call("DELETE", path, **kwargs)

    def _call(
        self,
        method: str,
        path: str,
        body: Mapping[str, object] | None = None,
        *,
        if_match: str = "",
        tolerate: Sequence[int] = (),
    ) -> dict:
        headers = {"Authorization": self._auth, "Accept": "application/json"}
        if if_match:
            headers["If-Match"] = if_match
        data = None
        if body is not None:
            data = json.dumps(body).encode()
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            f"{self._base_url}{path}", data=data, headers=headers, method=method
        )
        try:
            with urllib.request.urlopen(request) as response:
                payload = response.read()
        except urllib.error.HTTPError as error:
            payload = error.read()
            if error.code in tolerate:
                return {"_status": error.code, "_body": _decode(payload)}
            raise ApiError(f"{method} {path} -> {error.code}\n{_pretty(payload)}") from error
        except urllib.error.URLError as error:
            raise ApiError(f"{method} {path} -> {error.reason}") from error
        return {"_status": 200, **_decode(payload)}


class Livestatus:
    """The site's Livestatus socket, directly or through `sudo unixcat`."""

    def __init__(self, site: str) -> None:
        self._site = site
        self._socket = Path(f"/omd/sites/{site}/tmp/run/live")
        self._unixcat = Path(f"/omd/sites/{site}/bin/unixcat")
        if not self._socket.exists():
            raise ApiError(f"No Livestatus socket at {self._socket} — is site {site!r} running?")
        self._direct = os.access(self._socket, os.R_OK | os.W_OK)

    def hosts(self, names: Sequence[str]) -> dict[str, dict[str, object]]:
        query = ["GET hosts", "Columns: " + " ".join(LIVESTATUS_COLUMNS)]
        query += [f"Filter: name = {name}" for name in names]
        query.append(f"Or: {len(names)}")
        query.append("OutputFormat: json")
        rows = json.loads(self._talk("\n".join(query) + "\n\n"))
        return {row[0]: dict(zip(LIVESTATUS_COLUMNS, row)) for row in rows}

    def services(self, host_name: str) -> dict[str, dict[str, object]]:
        query = [
            "GET services",
            "Columns: " + " ".join(SERVICE_COLUMNS),
            f"Filter: host_name = {host_name}",
            "OutputFormat: json",
        ]
        rows = json.loads(self._talk("\n".join(query) + "\n\n"))
        return {row[1]: dict(zip(SERVICE_COLUMNS, row)) for row in rows}

    def command(self, command: str) -> None:
        self._talk(f"COMMAND [{int(time.time())}] {command}\n\n", read=False)

    def _talk(self, payload: str, *, read: bool = True) -> str:
        if self._direct:
            return self._talk_directly(payload, read=read)
        result = subprocess.run(
            ["sudo", "-u", self._site, str(self._unixcat), str(self._socket)],
            input=payload,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            raise ApiError(f"unixcat failed: {result.stderr.strip()}")
        return result.stdout

    def _talk_directly(self, payload: str, *, read: bool) -> str:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            connection.connect(str(self._socket))
            connection.sendall(payload.encode())
            connection.shutdown(socket.SHUT_WR)
            if not read:
                return ""
            chunks = []
            while chunk := connection.recv(65536):
                chunks.append(chunk)
        return b"".join(chunks).decode()


class ModeIconSite:
    """A dev site carrying one host per Mode-column icon."""

    def __init__(self, api: RestApi, live: Livestatus, site: str) -> None:
        self._api = api
        self._live = live
        self._site = site

    def populate(self) -> None:
        self._create_folder()
        self._create_timeperiod()
        self._create_hosts()
        self._create_rules()
        self.activate()
        self._await_hosts()
        self._send_commands()

    def cleanup(self) -> None:
        self._delete_rules()
        self._delete_hosts()
        self._delete_folder()
        self._delete_timeperiod()
        self.activate()

    def activate(self) -> None:
        response = self._api.post(
            "/domain-types/activation_run/actions/activate-changes/invoke",
            {"redirect": False, "sites": [self._site], "force_foreign_changes": True},
            if_match="*",
            tolerate=(422,),
        )
        if response["_status"] == 422:
            _say("nothing to activate")
            return
        activation_id = response["id"]
        _say(f"activating changes ({activation_id})")
        self._await_activation(activation_id)

    def _await_activation(self, activation_id: str) -> None:
        """The wait endpoint redirects onto itself while the job runs; poll it by hand."""
        path = f"/objects/activation_run/{activation_id}/actions/wait-for-completion/invoke"
        deadline = time.time() + 300.0
        while time.time() < deadline:
            if self._api.get(path, tolerate=(302, 404))["_status"] != 302:
                return
            time.sleep(2.0)
        raise ApiError(f"activation {activation_id} did not complete within 300s")

    def report(self) -> list[tuple[ModeIcon, list[str]]]:
        rows = self._live.hosts([icon.name for icon in MODE_ICONS])
        return [(icon, self._rendered(icon, rows)) for icon in MODE_ICONS]

    def _rendered(self, icon: ModeIcon, rows: Mapping[str, Mapping[str, object]]) -> list[str]:
        if icon.service:
            service = self._live.services(icon.name).get(icon.service)
            return [] if service is None else _service_icons_of(service)
        row = rows.get(icon.name)
        return [] if row is None else _icons_of(row)

    def _create_folder(self) -> None:
        response = self._api.post(
            "/domain-types/folder_config/collections/all",
            {"name": FOLDER_NAME, "title": "Mode icons", "parent": "/"},
            tolerate=(400,),
        )
        _say(f"folder {FOLDER_PATH}" + (" (already there)" if response["_status"] == 400 else ""))

    def _create_timeperiod(self) -> None:
        response = self._api.post(
            "/domain-types/time_period/collections/all",
            {
                "name": TIMEPERIOD,
                "alias": "Never (mode icon demo)",
                "active_time_ranges": [],
            },
            tolerate=(400,),
        )
        _say(
            f"time period {TIMEPERIOD}" + (" (already there)" if response["_status"] == 400 else "")
        )

    def _create_hosts(self) -> None:
        existing = self._existing_hosts()
        missing = [icon for icon in MODE_ICONS if icon.name not in existing]
        if not missing:
            _say("all mode-icon hosts already exist")
            return
        self._api.post(
            "/domain-types/host_config/actions/bulk-create/invoke",
            {
                "entries": [
                    {
                        "host_name": icon.name,
                        "folder": FOLDER_PATH,
                        "attributes": icon.attributes,
                    }
                    for icon in missing
                ]
            },
        )
        _say(f"created {len(missing)} host(s): " + ", ".join(icon.name for icon in missing))

    def _create_rules(self) -> None:
        for icon in MODE_ICONS:
            if icon.rule is None:
                continue
            ruleset, value_raw = icon.rule
            if self._rule_ids(ruleset):
                continue
            self._api.post(
                "/domain-types/rule/collections/all",
                {
                    "ruleset": ruleset,
                    "folder": FOLDER_PATH,
                    "properties": {
                        "description": f"{RULE_TAG}: {icon.name}",
                        "disabled": False,
                    },
                    "value_raw": value_raw,
                    "conditions": {"host_name": {"match_on": [icon.name], "operator": "one_of"}},
                },
            )
            _say(f"rule {ruleset} -> {icon.name}")

    def _send_commands(self) -> None:
        rows = self._live.hosts([icon.name for icon in MODE_ICONS])
        for command in self._pending_commands(rows):
            self._live.command(command)
            _say(f"command {command.split(';')[0]}")
        self._acknowledge(rows)
        self._crash_a_check()
        self._await(lambda: all(icon.name in shown for icon, shown in self.report()))

    def _crash_a_check(self) -> None:
        """A crashed check is an UNKNOWN result carrying the marker, which a passive result can be."""
        icon = next(icon for icon in MODE_ICONS if icon.service)
        if "crash" in self._rendered(icon, {}):
            return
        if not self._await(lambda: icon.service in self._live.services(icon.name)):
            _say(f"warning: service {icon.service!r} never appeared on {icon.name}")
            return
        self._live.command(
            f"PROCESS_SERVICE_CHECK_RESULT;{icon.name};{icon.service};"
            f"{UNKNOWN_STATE};{CRASH_OUTPUT}"
        )
        _say("command PROCESS_SERVICE_CHECK_RESULT")

    def _pending_commands(self, rows: Mapping[str, Mapping[str, object]]) -> Iterator[str]:
        author = self._api.user
        now = int(time.time())
        for icon in MODE_ICONS:
            row = rows.get(icon.name)
            if row is None:
                continue
            modified = row["modified_attributes_list"]
            match icon.name:
                case "downtime" if not row["scheduled_downtime_depth"]:
                    yield (
                        f"SCHEDULE_HOST_DOWNTIME;{icon.name};{now};{now + 7200};1;0;0;"
                        f"{author};{COMMENT}"
                    )
                case "notif-disabled" if row["notifications_enabled"]:
                    yield f"DISABLE_HOST_NOTIFICATIONS;{icon.name}"
                case "comment" if not row["comments"]:
                    yield f"ADD_HOST_COMMENT;{icon.name};1;{author};{COMMENT}"
                case "disabled" if "active_checks_enabled" not in modified:
                    yield f"DISABLE_HOST_CHECK;{icon.name}"
                case "npassive" if "passive_checks_enabled" not in modified:
                    yield f"ENABLE_PASSIVE_HOST_CHECKS;{icon.name}"
                    yield f"DISABLE_PASSIVE_HOST_CHECKS;{icon.name}"
                case _:
                    continue

    def _acknowledge(self, rows: Mapping[str, Mapping[str, object]]) -> None:
        icon = next(icon for icon in MODE_ICONS if icon.down)
        row = rows.get(icon.name)
        if row is None or row["acknowledged"]:
            return
        self._live.command(f"PROCESS_HOST_CHECK_RESULT;{icon.name};1;{COMMENT}")
        if not self._await(lambda: self._live.hosts([icon.name])[icon.name]["state"] != 0):
            _say(f"warning: {icon.name} never went DOWN, acknowledging anyway")
        self._live.command(f"ACKNOWLEDGE_HOST_PROBLEM;{icon.name};2;0;1;{self._api.user};{COMMENT}")
        _say("command ACKNOWLEDGE_HOST_PROBLEM")

    def _await_hosts(self) -> None:
        names = [icon.name for icon in MODE_ICONS]
        if not self._await(lambda: len(self._live.hosts(names)) == len(names)):
            raise ApiError("hosts did not show up in Livestatus after activation")

    def _delete_rules(self) -> None:
        for ruleset in {icon.rule[0] for icon in MODE_ICONS if icon.rule is not None}:
            for rule_id in self._rule_ids(ruleset):
                self._api.delete(f"/objects/rule/{rule_id}", if_match="*")
                _say(f"deleted rule {rule_id} ({ruleset})")

    def _delete_hosts(self) -> None:
        existing = self._existing_hosts()
        names = [icon.name for icon in MODE_ICONS if icon.name in existing]
        if not names:
            return
        self._api.post("/domain-types/host_config/actions/bulk-delete/invoke", {"entries": names})
        _say(f"deleted {len(names)} host(s)")

    def _delete_folder(self) -> None:
        self._api.delete(
            f"/objects/folder_config/~{FOLDER_NAME}", if_match="*", tolerate=(404, 400)
        )
        _say(f"deleted folder {FOLDER_PATH}")

    def _delete_timeperiod(self) -> None:
        self._api.delete(f"/objects/time_period/{TIMEPERIOD}", if_match="*", tolerate=(404, 409))
        _say(f"deleted time period {TIMEPERIOD}")

    def _existing_hosts(self) -> set[str]:
        response = self._api.get("/domain-types/host_config/collections/all")
        return {entry["id"] for entry in response["value"]}

    def _rule_ids(self, ruleset: str) -> list[str]:
        response = self._api.get("/domain-types/rule/collections/all", {"ruleset_name": ruleset})
        return [
            entry["id"]
            for entry in response["value"]
            if entry["extensions"]["properties"].get("description", "").startswith(RULE_TAG)
        ]

    @staticmethod
    def _await(condition, *, timeout: float = 30.0) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                if condition():
                    return True
            except KeyError, IndexError:
                pass
            time.sleep(1.0)
        return False


def _service_icons_of(row: Mapping[str, object]) -> list[str]:
    """Mirror of the crash branch of ``build_service_modes``; a passive demo service has no other."""
    crashed = row["state"] == UNKNOWN_STATE and CRASH_MARKER in str(row["plugin_output"])
    return ["crash"] if crashed else []


def _icons_of(row: Mapping[str, object]) -> list[str]:
    """Mirror of ``cmk.gui.monitor.hosts._api._modes.build_host_modes``."""
    modified = row["modified_attributes_list"]
    icons = []
    if row["scheduled_downtime_depth"]:
        icons.append("downtime")
    if row["acknowledged"]:
        icons.append("ack")
    if not row["notifications_enabled"]:
        icons.append("notif-disabled")
    if row["comments"]:
        icons.append("comment")
    if "active_checks_enabled" in modified and not row["active_checks_enabled"]:
        icons.append("disabled")
    if "passive_checks_enabled" in modified and not row["accept_passive_checks"]:
        icons.append("npassive")
    if not row["in_notification_period"]:
        icons.append("outofnot")
    if not row["in_service_period"]:
        icons.append("outof-serviceperiod")
    if not row["in_check_period"]:
        icons.append("pause")
    return icons


def _decode(payload: bytes) -> dict:
    if not payload:
        return {}
    try:
        return json.loads(payload)
    except json.JSONDecodeError:
        return {"_raw": payload.decode(errors="replace")}


def _pretty(payload: bytes) -> str:
    decoded = _decode(payload)
    return decoded.get("_raw") or json.dumps(decoded, indent=2)


def _say(message: str) -> None:
    print(f"  {message}", file=sys.stderr)


def _only_site() -> str:
    if site := os.environ.get("OMD_SITE"):
        return site
    sites = sorted(path.name for path in Path("/omd/sites").iterdir() if path.is_dir())
    if len(sites) != 1:
        raise ApiError(f"Pick a site with --site; found {sites or 'none'}")
    return sites[0]


def _print_report(report: Sequence[tuple[ModeIcon, Sequence[str]]], site: str) -> int:
    width = max(len(icon.name) for icon, _ in report)
    print()
    print(f"{'host / icon'.ljust(width)}  {'rendered'.ljust(width)}  status")
    print(f"{'-' * width}  {'-' * width}  ------")
    failures = 0
    for icon, rendered in report:
        if not rendered:
            status, failures = "MISSING", failures + 1
        elif list(rendered) == [icon.name]:
            status = "ok"
        elif icon.name in rendered:
            status = "ok (+ " + ", ".join(n for n in rendered if n != icon.name) + ")"
        else:
            status, failures = "WRONG", failures + 1
        print(f"{icon.name.ljust(width)}  {', '.join(rendered).ljust(width)}  {status}")
    print()
    print(f"  http://localhost/{site}/check_mk/monitor_all_hosts.py")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--site", help="OMD site to work on (default: the only one)")
    parser.add_argument("--user", default="cmkadmin", help="REST API user (default: cmkadmin)")
    parser.add_argument(
        "--password",
        default=os.environ.get("CMK_PASSWORD", "cmk"),
        help="REST API password (default: $CMK_PASSWORD or 'cmk')",
    )
    parser.add_argument(
        "--url",
        help="REST API base URL (default: http://localhost/<site>/check_mk/api/1.0)",
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--verify", action="store_true", help="only report what is rendered")
    group.add_argument("--cleanup", action="store_true", help="remove everything again")
    args = parser.parse_args()

    try:
        site = args.site or _only_site()
        url = args.url or f"http://localhost/{site}/check_mk/api/1.0"
        target = ModeIconSite(RestApi(url, args.user, args.password), Livestatus(site), site)
        if args.cleanup:
            target.cleanup()
            return 0
        if not args.verify:
            target.populate()
        return _print_report(target.report(), site)
    except ApiError as error:
        print(f"mode_icons: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
