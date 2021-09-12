#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
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
from typing import Any, Dict, List, Optional, TypedDict

import requests

from cmk.special_agents.utils.agent_common import ConditionalPiggybackSection, SectionWriter
from cmk.special_agents.utils.prometheus import extract_connection_args, generate_api_session


def parse_arguments(argv):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--debug", action="store_true", help="""Debug mode: raise Python exceptions"""
    )

    args = parser.parse_args(argv)
    return args


class IgnoreAlerts(TypedDict, total=False):
    # TODO: Remove total=False and mark as ignore_na as
    # not required when upgrading to Python 3.10:
    # https://www.python.org/dev/peps/pep-0655/
    ignore_na: bool
    ignore_alert_rules: List[str]
    ignore_alert_groups: List[str]


class Rule(TypedDict):
    name: str
    state: str
    severity: Optional[str]
    message: Optional[str]


Groups = Dict[str, List[Rule]]


class AlertmanagerAPI:
    """
    Realizes communication with the Alertmanager API
    """

    def __init__(self, session) -> None:
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
    config: Dict[str, Any],
) -> None:
    rule_groups = retrieve_rule_data(api_client)
    if not rule_groups.get("groups"):
        return
    parsed_data = parse_rule_data(rule_groups["groups"], config["ignore_alerts"])
    with ConditionalPiggybackSection(config["hostname"]):
        with SectionWriter("alertmanager") as writer:
            writer.append_json(parsed_data)


def retrieve_rule_data(api_client: AlertmanagerAPI) -> Dict[str, Any]:
    endpoint_result = api_client.query_static_endpoint("/rules")
    return json.loads(endpoint_result.content)["data"]


def parse_rule_data(group_data: List[Dict[str, Any]], ignore_alerts: IgnoreAlerts) -> Groups:
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


def main(argv=None):
    if argv is None:
        argv = sys.argv[1:]
    args = parse_arguments(argv)
    try:
        config = ast.literal_eval(sys.stdin.read())
        session = generate_api_session(extract_connection_args(config))
        api_client = AlertmanagerAPI(session)
        alertmanager_rules_section(api_client, config)
    except Exception as e:
        if args.debug:
            raise
        logging.debug(traceback.format_exc())
        sys.stderr.write("%s\n" % e)
        return 1
    return 0
