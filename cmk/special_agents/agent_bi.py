#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
import json
import sys
from multiprocessing.pool import ThreadPool
from typing import Any, Dict, Mapping, Set

import requests
import urllib3

import cmk.utils.site
from cmk.utils.exceptions import MKException
from cmk.utils.password_store import extract
from cmk.utils.paths import profile_dir
from cmk.utils.regex import regex
from cmk.utils.site import omd_site

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AggregationData:
    def __init__(self, bi_rawdata, config, error) -> None:
        super().__init__()
        self._bi_rawdata = bi_rawdata
        self._error = error

        self._output: list = []
        self._options = config.get("options", {})
        self._assignments = config.get("assignments", {})
        self._missing_sites: list = []
        self._missing_aggr: list = []
        self._aggregation_targets: dict = {}

    @property
    def bi_rawdata(self):
        return self._bi_rawdata

    @property
    def missing_aggr(self):
        return self._missing_aggr

    @property
    def missing_sites(self):
        return self._missing_sites

    @property
    def error(self):
        return self._error

    @property
    def output(self):
        return self._output

    def evaluate(self):
        if not self._bi_rawdata:
            return

        self._missing_sites = self._bi_rawdata["missing_sites"]
        self._missing_aggr = self._bi_rawdata["missing_aggr"]

        aggregations = self.parse_aggregation_response(self._bi_rawdata)

        for aggr_name, aggr_data in aggregations.items():
            self._rewrite_aggregation(aggr_data)
            self._process_assignments(aggr_name, aggr_data)

        # Output result
        for target_host, aggregations in self._aggregation_targets.items():
            if target_host is None:
                self._output.append("<<<<>>>>")
            else:
                self._output.append("<<<<%s>>>>" % target_host)

            self._output.append("<<<bi_aggregation:sep(0)>>>")
            self._output.append(repr(aggregations))

    @classmethod
    def parse_aggregation_response(cls, aggr_response):
        if "rows" in aggr_response:
            return AggregationData.parse_legacy_response(aggr_response["rows"])
        return aggr_response["aggregations"]

    @classmethod
    def parse_legacy_response(cls, rows):
        result = {}
        for row in rows:
            tree = row["tree"]
            effective_state = tree["aggr_effective_state"]
            result[tree["aggr_name"]] = {
                "state": effective_state["state"],
                "hosts": [x[1] for x in tree["aggr_hosts"]],
                "acknowledged": effective_state["acknowledged"],
                "in_downtime": effective_state["in_downtime"],
                "in_service_period": effective_state["in_service_period"],
                "infos": [],
            }
        return result

    def _rewrite_aggregation(self, aggr_data):
        aggr_data["state_computed_by_agent"] = aggr_data["state"]
        if aggr_data["in_downtime"] and "state_scheduled_downtime" in self._options:
            aggr_data["state_computed_by_agent"] = self._options["state_scheduled_downtime"]

        if aggr_data["acknowledged"] and "state_acknowledged" in self._options:
            aggr_data["state_computed_by_agent"] = self._options["state_acknowledged"]

    def _process_assignments(self, aggr_name, aggr_data):
        if not self._assignments:
            self._aggregation_targets.setdefault(None, {})[aggr_name] = aggr_data
            return

        if "querying_host" in self._assignments:
            self._aggregation_targets.setdefault(None, {})[aggr_name] = aggr_data

        if "affected_hosts" in self._assignments:
            for hostname in aggr_data["hosts"]:
                self._aggregation_targets.setdefault(hostname, {})[aggr_name] = aggr_data

        for pattern, target_host in self._assignments.get("regex", []):
            if regex(pattern).match(aggr_name):
                self._aggregation_targets.setdefault(target_host, {})[aggr_name] = aggr_data


class RawdataException(MKException):
    pass


class AggregationRawdataGenerator:
    def __init__(self, config: Mapping[str, Any]) -> None:
        self._config = config

        self._credentials = config["credentials"]
        if self._credentials == "automation":
            self._username = self._credentials
            self._secret = (profile_dir / self._username / "automation.secret").read_text(
                encoding="utf-8"
            )
        else:
            self._username, automation_secret = self._credentials[1]
            self._secret = extract(automation_secret)

        site_config = config["site"]

        if site_config == "local":
            self._site_url = "http://localhost:%d/%s" % (
                cmk.utils.site.get_apache_port(),
                omd_site(),
            )
        else:
            self._site_url = site_config[1]

    def generate_data(self) -> AggregationData:
        try:
            response_text = self._fetch_aggregation_data()
            rawdata = self._parse_response_text(response_text)
            return AggregationData(rawdata, self._config, None)
        except RawdataException as e:
            return AggregationData(None, self._config, str(e))
        except requests.exceptions.RequestException as e:
            return AggregationData(None, self._config, "Request Error %s" % e)

    def _fetch_aggregation_data(self):
        filter_query = self._config.get("filter") or {}

        response = requests.post(
            f"{self._site_url}"
            + "/check_mk/api/1.0"
            + "/domain-types/bi_aggregation/actions/aggregation_state/invoke",
            headers={"Authorization": f"Bearer {self._username} {self._secret.strip()}"},
            json={
                "filter_names": filter_query.get("names") or [],
                "filter_groups": filter_query.get("groups") or [],
            },
        )
        response.raise_for_status()
        return response.text

    def _parse_response_text(self, response_text):
        try:
            data = json.loads(response_text)
        except ValueError:
            if "automation secret" in response_text:
                raise RawdataException(
                    "Error: Unable to parse data from monitoring instance. Please check the login credentials"
                )
            raise RawdataException("Error: Unable to parse data from monitoring instance")

        if not isinstance(data, dict):
            raise RawdataException("Error: Unable to process parsed data from monitoring instance")

        return data


class AggregationOutputRenderer:
    def render(self, aggregation_data_results) -> None:
        connection_info_fields = ["missing_sites", "missing_aggr", "generic_errors"]
        connection_info: Dict[str, Set[str]] = {field: set() for field in connection_info_fields}  #

        output = []
        for aggregation_result in aggregation_data_results:
            aggregation_result.evaluate()
            connection_info["missing_aggr"].update(set(aggregation_result.missing_aggr))
            connection_info["missing_sites"].update(set(aggregation_result.missing_sites))
            if aggregation_result.error:
                connection_info["generic_errors"].add(aggregation_result.error)
            output.extend(aggregation_result.output)

        if not output:
            if connection_info["generic_errors"]:
                sys.stderr.write(
                    "Agent error(s): %s\n" % "\n".join(connection_info["generic_errors"])
                )
            else:
                sys.stderr.write("Got no information. Did you configure a BI aggregation?\n")
            sys.exit(1)

        sys.stdout.write("<<<bi_aggregation_connection:sep(0)>>>\n")
        result = {field: list(connection_info[field]) for field in connection_info_fields}
        sys.stdout.write(repr(result) + "\n")

        output.append("<<<<>>>>\n")
        sys.stdout.write("\n".join(output))


def query_data(config: Mapping[str, Any]) -> AggregationData:
    output_generator = AggregationRawdataGenerator(config)
    return output_generator.generate_data()


def main():
    try:
        # Config is a list of site connections
        config = ast.literal_eval(sys.stdin.read())
        p = ThreadPool()
        results = p.map(query_data, config)
        AggregationOutputRenderer().render(results)
    except Exception as e:
        sys.stderr.write("%s" % e)
        return 1
    return 0
