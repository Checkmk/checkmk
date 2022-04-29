#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2021 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring "Monitors" and "Events" of a datadog instance with Checkmk. The data
is fetched from the Datadog API, https://docs.datadoghq.com/api/, version 1. Endpoints:
* Monitors: monitor
* Events: events
"""

import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, Mapping, Optional, Sequence, Tuple, Union

import requests

from cmk.utils import paths, store
from cmk.utils.http_proxy_config import deserialize_http_proxy_config
from cmk.utils.misc import typeshed_issue_7724

from cmk.special_agents.utils.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.utils.argument_parsing import Args, create_default_argument_parser

from cmk.ec.export import (  # pylint: disable=cmk-module-layer-violation # isort: skip
    SyslogForwarderUnixSocket,
    SyslogMessage,
)

Tags = Sequence[str]
DatadogAPIResponse = Mapping[str, Any]

LOGGER = logging.getLogger("agent_datadog")


def parse_arguments(argv: Optional[Sequence[str]]) -> Args:
    parser = create_default_argument_parser(description=__doc__)
    parser.add_argument(
        "hostname",
        type=str,
        metavar="NAME",
        help=(
            "Name of the Checkmk host on which the agent is executed (used as filename to store "
            "the timestamp of the last event)"
        ),
    )
    parser.add_argument(
        "api_key",
        type=str,
        metavar="KEY",
        help="Datatog API Key",
    )
    parser.add_argument(
        "app_key",
        type=str,
        metavar="KEY",
        help="Datadog application key",
    )
    parser.add_argument(
        "api_host",
        type=str,
        metavar="ADDRESS",
        help="Datadog API host to connect to",
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default=None,
        metavar="PROXY",
        help=(
            "HTTP proxy used to connect to the Datadog API. If not set, the environment settings "
            "will be used."
        ),
    )
    parser.add_argument(
        "--sections",
        type=str,
        nargs="*",
        metavar="SECTION1 SECTION2 ...",
        help="Sections to be produced",
        choices=[
            "monitors",
            "events",
        ],
        default=[],
    )
    parser.add_argument(
        "--monitor_tags",
        type=str,
        nargs="*",
        metavar="TAG1 TAG2 ...",
        help="Restrict fetched monitors to tags",
        default=[],
    )
    parser.add_argument(
        "--monitor_monitor_tags",
        type=str,
        nargs="*",
        metavar="TAG1 TAG2 ...",
        help="Restrict fetched monitors to monitor tags",
        default=[],
    )
    parser.add_argument(
        "--event_max_age",
        type=int,
        metavar="AGE",
        help="Restrict maximum age of fetched events (in seconds)",
        default=600,
    )
    parser.add_argument(
        "--event_tags",
        type=str,
        nargs="*",
        metavar="TAG1 TAG2 ...",
        help="Restrict fetched events to tags",
        default=[],
    )
    parser.add_argument(
        "--event_tags_show",
        type=str,
        nargs="*",
        metavar="REGEX1 REGEX2 ...",
        help=(
            "Any tag of a fetched event matching one of these regular expressions will be shown "
            "in the EC"
        ),
        default=[],
    )
    parser.add_argument(
        "--event_syslog_facility",
        type=int,
        metavar="FACILITY",
        help="Syslog facility set when forwarding events to the EC",
        default=1,
    )
    parser.add_argument(
        "--event_syslog_priority",
        type=int,
        metavar="PRIORITY",
        help="Syslog priority set when forwarding events to the EC",
        default=1,
    )
    parser.add_argument(
        "--event_service_level",
        type=int,
        metavar="SL",
        help="Service level set when forwarding events to the EC",
        default=0,
    )
    parser.add_argument(
        "--event_add_text",
        action="store_true",
        help="Add text of events to data forwarded to the EC. Newline characters are replaced by '~'.",
    )
    return parser.parse_args(argv)


class DatadogAPI:
    def __init__(
        self,
        api_host: str,
        api_key: str,
        app_key: str,
        proxy: Optional[str] = None,
    ) -> None:
        self._query_heads = {
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }
        self._api_url = api_host.rstrip("/") + "/api/v1"
        self._proxy = deserialize_http_proxy_config(proxy)

    def get_request_json_decoded(
        self,
        api_endpoint: str,
        params: Mapping[str, Any],
    ) -> Any:
        return requests.get(
            f"{self._api_url}/{api_endpoint}",
            headers=self._query_heads,
            params=params,
            proxies=typeshed_issue_7724(self._proxy.to_requests_proxies()),
        ).json()


class MonitorsQuerier:
    def __init__(
        self,
        datadog_api: DatadogAPI,
    ) -> None:
        self._datadog_api = datadog_api

    def query_monitors(
        self,
        tags: Tags,
        monitor_tags: Tags,
        page_size: int = 100,
    ) -> Iterable[DatadogAPIResponse]:
        """
        Query monitors from the endpoint monitor
        https://docs.datadoghq.com/api/latest/monitors/#get-all-monitor-details
        """
        current_page = 0
        while True:
            if monitors_in_page := self._query_monitors_page(
                tags,
                monitor_tags,
                page_size,
                current_page,
            ):
                yield from monitors_in_page
                current_page += 1
                continue

            return

    def _query_monitors_page(
        self,
        tags: Tags,
        monitor_tags: Tags,
        page_size: int,
        current_page: int,
    ) -> Sequence[DatadogAPIResponse]:
        """
        Query paginated monitors (endpoint monitor)
        https://docs.datadoghq.com/api/latest/monitors/#get-all-monitor-details
        """
        # we use pagination to avoid running into any limits
        params: Dict[str, Union[int, str]] = {
            "page_size": page_size,
            "page": current_page,
        }
        if tags:
            params["tags"] = ",".join(tags)
        if monitor_tags:
            params["monitor_tags"] = ",".join(monitor_tags)

        return self._datadog_api.get_request_json_decoded(
            "monitor",
            params,
        )


class EventsQuerier:
    def __init__(
        self,
        datadog_api: DatadogAPI,
        host_name: str,
        max_age: int,
    ) -> None:
        self._datadog_api = datadog_api
        self._path_last_event_ids = (
            Path(paths.tmp_dir) / "agents" / "agent_datadog" / (host_name + ".json")
        )
        self._max_age = max_age

    def query_events(
        self,
        tags: Tags,
    ) -> Iterable[DatadogAPIResponse]:
        last_event_ids = self._read_last_event_ids()
        queried_events = list(self._execute_query(tags))
        self._store_last_event_ids(event["id"] for event in queried_events)
        yield from (event for event in queried_events if event["id"] not in last_event_ids)

    def _execute_query(
        self,
        tags: Tags,
    ) -> Iterable[DatadogAPIResponse]:
        """
        Query events from the endpoint events
        https://docs.datadoghq.com/api/latest/events/#query-the-event-stream
        """
        start, end = self._events_query_time_range()
        current_page = 0

        while True:
            if events_in_page := self._query_events_page_in_time_window(
                start,
                end,
                current_page,
                tags,
            ):
                yield from events_in_page
                current_page += 1
                continue

            break

    def _events_query_time_range(self) -> Tuple[int, int]:
        now = int(time.time())
        return now - self._max_age, now

    def _query_events_page_in_time_window(
        self,
        start: int,
        end: int,
        page: int,
        tags: Tags,
    ) -> Sequence[DatadogAPIResponse]:
        """
        Query paginated events (endpoint events)
        https://docs.datadoghq.com/api/latest/events/#query-the-event-stream
        """
        params: Dict[str, Union[int, str]] = {
            "start": start,
            "end": end,
            "page": page,
            "exclude_aggregate": True,
        }
        if tags:
            params["tags"] = ",".join(tags)

        return self._datadog_api.get_request_json_decoded(
            "events",
            params,
        )["events"]

    def _store_last_event_ids(
        self,
        ids: Iterable[int],
    ) -> None:
        store.save_text_to_file(
            self._path_last_event_ids,
            json.dumps(list(ids)),
        )

    def _read_last_event_ids(self) -> FrozenSet[int]:
        return frozenset(
            json.loads(
                store.load_text_from_file(
                    self._path_last_event_ids,
                    default="[]",
                )
            )
        )


def _to_syslog_message(
    raw_event: DatadogAPIResponse,
    tag_regexes: Iterable[str],
    facility: int,
    severity: int,
    service_level: int,
    add_text: bool,
) -> SyslogMessage:
    LOGGER.debug(raw_event)
    matching_tags = ", ".join(
        tag
        for tag in raw_event["tags"]
        if any(re.match(tag_regex, tag) for tag_regex in tag_regexes)
    )
    tags_text = f", Tags: {matching_tags}" if matching_tags else ""
    details = str(raw_event["text"]).replace("\n", " ~ ")
    details_text = f", Text: {details}" if add_text else ""
    return SyslogMessage(
        facility=facility,
        severity=severity,
        timestamp=raw_event["date_happened"],
        host_name=str(raw_event["host"]),
        application=str(raw_event["source"]),
        service_level=service_level,
        text=str(raw_event["title"]) + tags_text + details_text,
    )


def _forward_events_to_ec(
    raw_events: Iterable[DatadogAPIResponse],
    tag_regexes: Iterable[str],
    facility: int,
    severity: int,
    service_level: int,
    add_text: bool,
) -> None:
    SyslogForwarderUnixSocket().forward(
        _to_syslog_message(
            raw_event,
            tag_regexes,
            facility,
            severity,
            service_level,
            add_text,
        )
        for raw_event in raw_events
    )


def _monitors_section(
    datadog_api: DatadogAPI,
    args: Args,
) -> None:
    LOGGER.debug("Querying monitors")
    with SectionWriter("datadog_monitors") as writer:
        for monitor in MonitorsQuerier(datadog_api).query_monitors(
            args.monitor_tags,
            args.monitor_monitor_tags,
        ):
            writer.append_json(monitor)


def _events_section(datadog_api: DatadogAPI, args: Args) -> None:
    LOGGER.debug("Querying events")
    events = list(
        EventsQuerier(
            datadog_api,
            args.hostname,
            args.event_max_age,
        ).query_events(args.event_tags)
    )
    _forward_events_to_ec(
        events,
        args.event_tags_show,
        args.event_syslog_facility,
        args.event_syslog_priority,
        args.event_service_level,
        args.event_add_text,
    )
    with SectionWriter("datadog_events") as writer:
        writer.append(len(events))


def agent_datadog_main(args: Args) -> None:
    datadog_api = DatadogAPI(
        args.api_host,
        args.api_key,
        args.app_key,
        proxy=args.proxy,
    )
    for section in args.sections:
        {"monitors": _monitors_section, "events": _events_section,}[section](
            datadog_api,
            args,
        )


def main() -> None:
    """Main entry point to be used"""
    special_agent_main(parse_arguments, agent_datadog_main)
