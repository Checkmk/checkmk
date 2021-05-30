#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
import argparse
from typing import List, Dict, Tuple, Optional
import requests


class SummaryStructure:
    def __init__(self, system_alerts: Dict[Tuple[str, str], dict],
                    env_alerts: Dict[Tuple[str, str], dict],
                    fuse_alerts: Dict[str, dict]
                ) -> None:
        self.system_alerts: Dict[Tuple[str, str], dict] = system_alerts
        self.env_alerts: Dict[Tuple[str, str], dict] = env_alerts
        self.fuse_alerts: Dict[str, dict] = fuse_alerts
    def __eq__(self, other):
        try:
            return (
                self.system_alerts == other.system_alerts and
                self.env_alerts == other.env_alerts and
                self.fuse_alerts == other.fuse_alerts
            )
        except AttributeError:
            return NotImplemented

class LayoutResponse:
    def __init__(self, code: int, data: dict) -> None:
        self.code: int = code
        self.data: dict = data


class SummaryResponse:
    def __init__(self, code: int, data: list) -> None:
        self.code: int = code
        self.data: list = data


class Alert:
    def __init__(self, fuse_id: str, name: str,
                    own_type: str, component_type: str,
                    errors: int, warnings: int, link: str
                ) -> None:
        self.fuse_id: str = fuse_id
        self.name: str = name
        self.type: str = own_type
        self.component_type: str = component_type
        self.errors: int = errors
        self.warnings: int = warnings
        self.link: str = link
    def __eq__(self, other):
        try:
            return (
                self.fuse_id == other.fuse_id and
                self.name == other.name and
                self.type == other.type and
                self.component_type == other.component_type and
                self.errors == other.errors and
                self.warnings == other.warnings and
                self.link == other.link
            )
        except AttributeError:
            return NotImplemented


class LayoutConnection:
    def __init__(self, url: str) -> None:
        self.base_url: str = "%s/layout" % url


class SummaryConnection:
    def __init__(self, url: str) -> None:
        self.base_url: str = "%s/summary" % url


class FuseRequest:
    def __init__(self, connection_url: str, username: str, password: str) -> None:
        self.endpoint: str = "%s" % connection_url
        self.username: str = username
        self.password: str = password
    def get_layout(self) -> LayoutResponse:
        data: dict = {}
        try:
            response = requests.get(self.endpoint, auth=(self.username, self.password))
            code: int = response.status_code
            if code == 200:
                data = json.loads(response.text)
        except requests.exceptions.RequestException:
            code = 404
        return LayoutResponse(code, data)
    def get_summary(self) -> SummaryResponse:
        data: list = []
        try:
            response = requests.get(self.endpoint, auth=(self.username, self.password))
            code: int = response.status_code
            if code == 200:
                data = json.loads(response.text)
        except requests.exceptions.RequestException:
            code = 404
        return SummaryResponse(code, data)


def get_summary_structure(summary: list) -> SummaryStructure:
    system_alerts_map: Dict[Tuple[str, str], dict] = {}
    env_alerts_map: Dict[Tuple[str, str], dict] = {}
    fuse_alerts_map: Dict[str, dict] = {}
    for alert in summary:
        if "systemId" in alert:
            system_alerts_map[(alert["systemId"], alert["componentType"])] = alert
        elif "envId" in alert:
            env_alerts_map[(alert["envId"], alert["componentType"])] = alert
        else:
            fuse_alerts_map[alert["componentType"]] = alert
    return SummaryStructure(system_alerts_map, env_alerts_map, fuse_alerts_map)


def get_systems_alerts(layout: dict, system_alerts_map: Dict[Tuple[str, str], dict]) -> List[Alert]:
    system_alerts: List[Alert] = []
    if "systems" in layout:
        for system in layout["systems"]:
            for component in system["componentTypes"]:
                system_alert: Alert = Alert(system["id"], system["name"],
                                                system["type"], component["displayName"],
                                                0, 0, ""
                                            )
                if (system["id"], component["id"]) in system_alerts_map:
                    alert = system_alerts_map[(system["id"], component["id"])]
                    if "errors" in alert:
                        system_alert.errors = int(alert["errors"])
                    if "warnings" in alert:
                        system_alert.warnings = int(alert["warnings"])
                    if "link" in alert:
                        system_alert.link = alert["link"]
                system_alerts.append(system_alert)
    return system_alerts


def get_environment_alerts(layout: dict, env_alert_map: Dict[Tuple[str, str], dict]) -> List[Alert]:
    env_alerts: List[Alert] = []
    if "environments" in layout:
        for environment in layout["environments"]:
            for component in environment["componentTypes"]:
                env_alert: Alert = Alert(environment["id"], environment["name"],
                                            "", component["displayName"], 0, 0, ""
                                        )
                if (environment["id"], component["id"]) in env_alert_map:
                    alert = env_alert_map[(environment["id"], component["id"])]
                    if "errors" in alert:
                        env_alert.errors = int(alert["errors"])
                    if "warnings" in alert:
                        env_alert.warnings = int(alert["warnings"])
                    if "link" in alert:
                        env_alert.link = alert["link"]
                env_alerts.append(env_alert)
    return env_alerts


def get_admin_alerts(layout: dict, env_admin_map: Dict[str, dict]) -> List[Alert]:
    admin_alerts: List[Alert] = []
    if "admin" in layout:
        admin = layout["admin"]
        for component in admin["componentTypes"]:
            admin_alert: Alert = Alert("", "", "", component["displayName"], 0, 0, "")
            if component["id"] in env_admin_map:
                alert = env_admin_map[component["id"]]
                if "errors" in alert:
                    admin_alert.errors = int(alert["errors"])
                if "warnings" in alert:
                    admin_alert.warnings = int(alert["warnings"])
                if "link" in alert:
                    admin_alert.link = alert["link"]
            admin_alerts.append(admin_alert)
    return admin_alerts


def parse_arguments(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("user",
                        metavar="USER",
                        help="")
    parser.add_argument("password",
                        metavar="PASSWORD",
                        help="")
    parser.add_argument("url",
                        metavar="URL",
                        help="")
    parser.add_argument("host",
                        metavar="HOST",
                        help="")
    return parser.parse_args(argv)


def main(args: Optional[List[str]] = None) -> int:
    if args is None:
        args = sys.argv[1:]
    opt: argparse.Namespace = parse_arguments(args)

    layout_connection: LayoutConnection = LayoutConnection(opt.url)
    layout_request: FuseRequest  = FuseRequest(layout_connection.base_url, opt.user, opt.password)
    layout_response: LayoutResponse = layout_request.get_layout()

    summary_connection: SummaryConnection = SummaryConnection(opt.url)
    summary_request: FuseRequest = FuseRequest(summary_connection.base_url, opt.user, opt.password)
    summary_response: SummaryResponse = summary_request.get_summary()

    state: str = "up"
    if layout_response.code == 401 or summary_response.code == 401:
        state = "unauth"
    elif layout_response.code != 200 or summary_response.code != 200:
        state = "down"
    elif not layout_response.data:
        state = "empty"

    sys.stdout.write("<<<fuse_instance:sep(0)>>>\n")
    sys.stdout.write("{}\n".format(state))

    if state == "up":
        layout: dict = layout_response.data
        summary: list = summary_response.data

        summary_structure: SummaryStructure = get_summary_structure(summary)

        system_alerts: List[Alert] = get_systems_alerts(layout, summary_structure.system_alerts)
        sys.stdout.write("<<<fuse_system_alerts:sep(0)>>>\n")
        sys.stdout.write("{}\n".format(json.dumps([alert.__dict__ for alert in system_alerts])))

        env_alerts: List[Alert] = get_environment_alerts(layout, summary_structure.env_alerts)
        sys.stdout.write("<<<fuse_env_alerts:sep(0)>>>\n")
        sys.stdout.write("{}\n".format(json.dumps([alert.__dict__ for alert in env_alerts])))

        admin_alerts: List[Alert] = get_admin_alerts(layout, summary_structure.fuse_alerts)
        sys.stdout.write("<<<fuse_admin_alerts:sep(0)>>>\n")
        sys.stdout.write("{}\n".format(json.dumps([alert.__dict__ for alert in admin_alerts])))

    return 0


if __name__ == "__main__":
    main()
