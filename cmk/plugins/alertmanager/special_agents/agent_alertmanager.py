#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring Promtheus Alertmanager with Checkmk.
"""

import argparse
import ast
import json
import logging
import sys
import traceback
from collections.abc import Sequence
from typing import Any, NotRequired, TypedDict

import requests

from cmk.plugins.lib.prometheus import (
    add_authentication_args,
    authentication_from_args,
    generate_api_session,
    get_api_url,
)
from cmk.special_agents.v0_unstable.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.v0_unstable.request_helper import ApiSession


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: raise Python exceptions"""
    )
    parser.add_argument(
        "--config",
        required=True,
        help="The configuration is passed as repr object. This option will change in the future.",
    )
    add_authentication_args(parser)
    parser.add_argument(
        "--disable-cert-verification",
        action="store_true",
        help="Do not verify TLS certificate.",
    )
    args = parser.parse_args(argv)
    return args


class IgnoreAlerts(TypedDict):
    ignore_na: NotRequired[bool]
    ignore_alert_rules: list[str]
    ignore_alert_groups: list[str]


class Rule(TypedDict):
    name: str
    state: str
    severity: str | None
    message: str | None


Groups = dict[str, list[Rule]]


class AlertmanagerAPI:
    """
    Realizes communication with the Alertmanager API
    """

    def __init__(self, session: ApiSession) -> None:
        self.session = session

    def query_static_endpoint(self, endpoint: str) -> requests.models.Response:
        """Query the given endpoint of the Alertmanager API expecting a text response

        Args:
            endpoint: Param which contains the Prometheus API endpoint to be queried

        Returns:
            Returns a response containing the text response
        """
        response = self.session.get(endpoint)
        response.raise_for_status()
        return response


def alertmanager_rules_section(
    api_client: AlertmanagerAPI,
    config: dict[str, Any],
) -> None:
    rule_groups = retrieve_rule_data(api_client)
    if not rule_groups.get("groups"):
        return
    parsed_data = parse_rule_data(rule_groups["groups"], config["ignore_alerts"])
    with ConditionalPiggybackSection(config["hostname"]):
        with SectionWriter("alertmanager") as writer:
            writer.append_json(parsed_data)


def retrieve_rule_data(api_client: AlertmanagerAPI) -> dict[str, Any]:
    endpoint_result = api_client.query_static_endpoint("rules")
    return json.loads(endpoint_result.content)["data"]


def parse_rule_data(group_data: list[dict[str, Any]], ignore_alerts: IgnoreAlerts) -> Groups:
    """Parses data from Alertmanager API endpoint

    Args:
        data: Raw  unparsed data from Alertmanager API endpoint

    Returns:
        Returns a dict of all alert rule groups containing a list
        of all alert rules within the group
    """
    groups: Groups = {}
    for group_entry in group_data:
        if group_entry["name"] in ignore_alerts["ignore_alert_groups"]:
            continue
        rule_list = []
        for rule_entry in group_entry["rules"]:
            if rule_entry["name"] in ignore_alerts["ignore_alert_rules"] or (
                ignore_alerts.get("ignore_na", False) and not rule_entry.get("state", False)
            ):
                continue

            labels = rule_entry.get("labels", {})
            annotations = rule_entry.get("annotations", {})
            rule_list.append(
                Rule(
                    name=rule_entry["name"],
                    state=rule_entry.get("state"),
                    severity=labels.get("severity"),
                    message=annotations.get("message"),
                )
            )
        groups[group_entry["name"]] = rule_list
    return groups


def main(argv: Sequence[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    args = parse_arguments(argv)
    try:
        config = ast.literal_eval(args.config)
        session = generate_api_session(
            get_api_url(config["connection"], config["protocol"]),
            authentication_from_args(args),
            not args.disable_cert_verification,
        )
        api_client = AlertmanagerAPI(session)
        alertmanager_rules_section(api_client, config)
    except Exception as e:
        if args.debug:
            raise
        logging.debug(traceback.format_exc())
        sys.stderr.write("%s\n" % e)
        return 1
    return 0
