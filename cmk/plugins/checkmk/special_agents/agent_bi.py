#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import argparse
import json
import select
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Any, Literal, NotRequired, Self, TypedDict

import requests
import urllib3
from pydantic import BaseModel, Field

import cmk.ccc.site
from cmk.ccc.exceptions import MKException
from cmk.ccc.site import omd_site
from cmk.ccc.user import UserId

from cmk.utils.local_secrets import AutomationUserSecret, SiteInternalSecret
from cmk.utils.password_store import lookup
from cmk.utils.paths import omd_root
from cmk.utils.regex import regex

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AgentBiUserAuthentication(BaseModel):
    username: str
    password_store_path: Path | None
    password_store_identifier: str | None

    def merge_arg(self, arg: str) -> None:
        pw_id, pw_file = arg.split(":", 1)
        self.password_store_path = Path(pw_file)
        self.password_store_identifier = pw_id

    def lookup(self) -> str:
        assert self.password_store_path is not None and self.password_store_identifier is not None

        return lookup(
            self.password_store_path,
            self.password_store_identifier,
        )


class AgentBiAutomationUserAuthentication(BaseModel):
    username: str

    def lookup(self) -> str:
        return AutomationUserSecret(UserId(self.username)).read()


class AgentBiAdditionalOptions(TypedDict):
    state_scheduled_downtime: NotRequired[Literal[0, 1, 2, 3]]
    state_acknowledged: NotRequired[Literal[0, 1, 2, 3]]


class AgentBiAssignments(BaseModel):
    querying_host: bool = False
    affected_hosts: bool = False
    regex: list[tuple[str, str]] = Field(default_factory=list)


class AgentBiFilter(BaseModel):
    names: list[str] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)


# Help mypy a bit...
def _agent_bi_additional_options_factory() -> AgentBiAdditionalOptions:
    return AgentBiAdditionalOptions()


class AgentBiConfig(BaseModel):
    assignments: AgentBiAssignments | None = None
    authentication: AgentBiAutomationUserAuthentication | AgentBiUserAuthentication | None = None
    filter: AgentBiFilter = Field(default_factory=AgentBiFilter)
    options: AgentBiAdditionalOptions = Field(default_factory=_agent_bi_additional_options_factory)
    site_url: str | None = None


class AggregationData:
    def __init__(
        self,
        bi_rawdata: Mapping[str, Any] | None,
        config: AgentBiConfig,
        error: str | None,
    ) -> None:
        super().__init__()
        self._bi_rawdata = bi_rawdata
        self._error = error

        self._output: list[str] = []
        self._options = config.options
        self._assignments = config.assignments
        self._missing_sites: list = []
        self._missing_aggr: list = []
        self._aggregation_targets: dict = {}

    @property
    def bi_rawdata(self) -> Mapping[str, Any] | None:
        return self._bi_rawdata

    @property
    def missing_aggr(self):
        return self._missing_aggr

    @property
    def missing_sites(self):
        return self._missing_sites

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def output(self) -> list[str]:
        return self._output

    def evaluate(self) -> None:
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
    def parse_aggregation_response(
        cls, aggr_response: Mapping[str, Any]
    ) -> dict[str, dict[str, Any]]:
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

    def _rewrite_aggregation(self, aggr_data: dict[str, Any]) -> None:
        aggr_data["state_computed_by_agent"] = aggr_data["state"]
        if aggr_data["in_downtime"] and "state_scheduled_downtime" in self._options:
            aggr_data["state_computed_by_agent"] = self._options["state_scheduled_downtime"]

        if aggr_data["acknowledged"] and "state_acknowledged" in self._options:
            aggr_data["state_computed_by_agent"] = self._options["state_acknowledged"]

    def _process_assignments(self, aggr_name: str, aggr_data: dict[str, Any]) -> None:
        if not self._assignments:
            self._aggregation_targets.setdefault(None, {})[aggr_name] = aggr_data
            return

        if self._assignments.querying_host:
            self._aggregation_targets.setdefault(None, {})[aggr_name] = aggr_data

        if self._assignments.affected_hosts:
            for hostname in aggr_data["hosts"]:
                self._aggregation_targets.setdefault(hostname, {})[aggr_name] = aggr_data

        for pattern, target_host in self._assignments.regex:
            if mo := regex(pattern).match(aggr_name):
                target_name = target_host
                for nr, text in enumerate(mo.groups("")):
                    target_name = target_name.replace("\\%d" % (nr + 1), text)
                self._aggregation_targets.setdefault(target_name, {})[aggr_name] = aggr_data


class RawdataException(MKException):
    pass


class AggregationRawdataGenerator:
    def __init__(self, config: AgentBiConfig) -> None:
        self._config = config

        if self._config.site_url is None:
            self._site_url = "http://localhost:%d/%s" % (
                cmk.ccc.site.get_apache_port(omd_root),
                omd_site(),
            )
        else:
            self._site_url = self._config.site_url

    def _get_authentication_token(self) -> str:
        if self._config.authentication is None:
            return f"InternalToken {SiteInternalSecret().secret.b64_str}"
        secret = self._config.authentication.lookup()
        return f"Bearer {self._config.authentication.username} {secret.strip()}"

    def generate_data(self) -> AggregationData:
        try:
            response_text = self._fetch_aggregation_data()
            rawdata = self._parse_response_text(response_text)
            return AggregationData(rawdata, self._config, None)
        except RawdataException as e:
            return AggregationData(None, self._config, str(e))
        except requests.exceptions.RequestException as e:
            return AggregationData(None, self._config, "Request Error %s" % e)

    def _fetch_aggregation_data(self) -> str:
        filter_query = self._config.filter

        response = requests.get(
            f"{self._site_url}"
            + "/check_mk/api/1.0"
            + "/domain-types/bi_aggregation/actions/aggregation_state/invoke",
            headers={"Authorization": self._get_authentication_token()},
            params={
                "filter_names": filter_query.names,
                "filter_groups": filter_query.groups,
            },
            timeout=900,
        )
        response.raise_for_status()
        return response.text

    def _parse_response_text(self, response_text: str) -> dict[str, Any]:
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
    def render(self, aggregation_data_results: Sequence[AggregationData]) -> None:
        connection_info_fields = ["missing_sites", "missing_aggr", "generic_errors"]
        connection_info: dict[str, set[str]] = {field: set() for field in connection_info_fields}

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


def query_data(config: AgentBiConfig) -> AggregationData:
    output_generator = AggregationRawdataGenerator(config)
    return output_generator.generate_data()


def merge_config(secrets: Sequence[str], raw_configs: Sequence[str]) -> list[AgentBiConfig]:
    # we could just use zip( . , strict=True), but let's be explicit:
    if (ls := len(secrets)) != (lc := len(raw_configs)):
        raise ValueError(
            f"Number of arguments to `--secrets` ({ls}) and `--configs` ({lc}) must match"
        )
    configs = []
    for arg, config_j in zip(secrets, raw_configs):
        config = AgentBiConfig.model_validate_json(config_j)
        if isinstance(config.authentication, AgentBiUserAuthentication) is (":" not in arg):
            raise ValueError("Secrets and configs must match")
        configs.append(config)
        if isinstance(config.authentication, AgentBiUserAuthentication):
            config.authentication.merge_arg(arg)
    return configs


@dataclass(frozen=True)
class _Args:
    debug: bool
    configs: Sequence[AgentBiConfig]

    @classmethod
    def from_argv(cls, args: Sequence[str]) -> Self:
        raw = parse_arguments(args)
        return cls(debug=bool(raw.debug), configs=merge_config(raw.secrets, raw.configs))


def _optionally_read_stdin_list() -> list[str]:
    """Try to read additional argv elements from stdin

    Most of the time, stdin will be available, and we immediately return
    the read elements.
    In case stdin is not provided (in manual calls for example) we time out
    after just 1 second.
    """
    if select.select([sys.stdin], [], [], 1.0)[0]:
        return json.load(sys.stdin)
    return []


def parse_arguments(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--debug", action="store_true", help="Debug mode: raise Python exceptions")
    parser.add_argument("--secrets", default=[], nargs="*", help="List of secrets")
    parser.add_argument("--configs", default=[], nargs="*", help="List of configs")
    return parser.parse_args(argv)


def main() -> int:
    args = _Args.from_argv(sys.argv[1:] + _optionally_read_stdin_list())
    try:
        p = ThreadPool()
        results = p.map(query_data, args.configs)
        AggregationOutputRenderer().render(results)
    except () if args.debug else (Exception,) as e:
        sys.stderr.write("%s" % e)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
