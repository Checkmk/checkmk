#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""
Special agent for monitoring "Monitors" and "Events" of a datadog instance with Checkmk. The data
is fetched from the Datadog API, https://docs.datadoghq.com/api/. Endpoints:
* Monitors: monitor (v1)
* Events: events (v1)
* Logs: logs (v2)
"""

import datetime
import json
import logging
import re
import time
from collections.abc import Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any, Final, Generic, Protocol, TypeVar

import pydantic
import requests
from dateutil import parser as dateutil_parser

from cmk.ccc import store

from cmk.utils import paths
from cmk.utils.http_proxy_config import deserialize_http_proxy_config

import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation

from cmk.special_agents.v0_unstable.agent_common import SectionWriter, special_agent_main
from cmk.special_agents.v0_unstable.argument_parsing import Args, create_default_argument_parser

Tags = Sequence[str]

LOGGER = logging.getLogger("agent_datadog")


@dataclass(frozen=True)
class LogMessageElement:
    name: str
    key: str

    @classmethod
    def from_arg(cls, arg: str) -> "LogMessageElement":
        name, key = arg.split(":", maxsplit=1)
        return cls(name, key)


def parse_arguments(argv: Sequence[str] | None) -> Args:
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
        help="Datatog API key",
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
        choices=["monitors", "events", "logs"],
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
    parser.add_argument(
        "--log_max_age",
        type=int,
        metavar="AGE",
        help="Restrict maximum age of fetched logs (in seconds)",
        default=600,
    )
    parser.add_argument("--log_query", type=str, help="filter logs by this query.", default="")
    parser.add_argument(
        "--log_indexes",
        type=str,
        nargs="*",
        metavar="IDX1 IDX2 ...",
        help="Indexes to search",
        default="*",
    )
    parser.add_argument(
        "--log_text",
        type=LogMessageElement.from_arg,
        nargs="*",
        metavar="name:key other:nested.key ...",
        help="Value from message to use for event text",
        default="message:message",
    )
    parser.add_argument(
        "--log_syslog_facility",
        type=int,
        metavar="FACILITY",
        help="Syslog facility set when forwarding logs to the EC",
        default=1,
    )
    parser.add_argument(
        "--log_service_level",
        type=int,
        metavar="SL",
        help="Service level set when forwarding logs to the EC",
        default=0,
    )
    return parser.parse_args(argv)


class DatadogAPI(Protocol):
    """
    Notes:
        * The DatadogAPI in rare occurrences can report a 503 which they described as follows:
        'Service Unavailable, the server is not ready to handle the request probably because
        it is overloaded, request should be retried after some time'
    """

    def get_request(
        self,
        api_endpoint: str,
        params: Mapping[str, str | int],
        version: str = "v1",
    ) -> requests.Response: ...

    def post_request(
        self,
        api_endpoint: str,
        body: Mapping[str, str | int],
        version: str = "v1",
    ) -> requests.Response: ...


class ImplDatadogAPI:
    def __init__(
        self,
        api_host: str,
        api_key: str,
        app_key: str,
        proxy: str | None = None,
    ) -> None:
        self._query_heads = {
            "DD-API-KEY": api_key,
            "DD-APPLICATION-KEY": app_key,
        }
        self._api_url = api_host.rstrip("/") + "/api"
        self._proxy = deserialize_http_proxy_config(proxy)

    def get_request(
        self,
        api_endpoint: str,
        params: Mapping[str, str | int],
        version: str = "v1",
    ) -> requests.Response:
        return requests.get(
            f"{self._api_url}/{version}/{api_endpoint}",
            headers=self._query_heads,
            params=params,
            proxies=self._proxy.to_requests_proxies(),
            timeout=900,
        )

    def post_request(
        self,
        api_endpoint: str,
        body: Mapping[str, Any],
        version: str = "v1",
    ) -> requests.Response:
        return requests.post(
            f"{self._api_url}/{version}/{api_endpoint}",
            headers=self._query_heads,
            json=body,
            proxies=self._proxy.to_requests_proxies(),
            timeout=900,
        )


_TID = TypeVar("_TID", str, int)


class IDStore(Generic[_TID]):
    def __init__(self, path: Path):
        self.path: Final = path

    def write(self, ids: Iterable[_TID]) -> None:
        store.save_text_to_file(
            self.path,
            json.dumps(list(ids)),
        )

    def read(self) -> frozenset[_TID]:
        return frozenset(
            json.loads(
                store.load_text_from_file(
                    self.path,
                    default="[]",
                )
            )
        )


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
    ) -> Iterator[object]:
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
    ) -> list[object]:
        """
        Query paginated monitors (endpoint monitor)
        https://docs.datadoghq.com/api/latest/monitors/#get-all-monitor-details
        """
        # we use pagination to avoid running into any limits
        params: dict[str, int | str] = {
            "page_size": page_size,
            "page": current_page,
        }
        if tags:
            params["tags"] = ",".join(tags)
        if monitor_tags:
            params["monitor_tags"] = ",".join(monitor_tags)

        resp = self._datadog_api.get_request(
            "monitor",
            params,
        )
        resp.raise_for_status()
        return resp.json()


class Event(pydantic.BaseModel, frozen=True):
    id: int
    tags: Sequence[str]
    text: str
    date_happened: int
    # None should not happen according to docs, but reality says something different ...
    host: str | None = None
    title: str
    source: str


class EventsQuerier:
    def __init__(
        self,
        datadog_api: DatadogAPI,
        host_name: str,
        max_age: int,
    ) -> None:
        self.datadog_api: Final = datadog_api
        self.id_store: Final = IDStore[int](
            paths.tmp_dir / "agents" / "agent_datadog" / f"{host_name}.json"
        )
        self.max_age: Final = max_age

    def query_events(
        self,
        tags: Tags,
    ) -> Iterator[Event]:
        last_event_ids = self.id_store.read()
        queried_events = list(self._execute_query(tags))
        self.id_store.write(event.id for event in queried_events)
        yield from (event for event in queried_events if event.id not in last_event_ids)

    def _execute_query(
        self,
        tags: Tags,
    ) -> Iterator[Event]:
        """
        Query events from the endpoint events
        https://docs.datadoghq.com/api/latest/events/#query-the-event-stream
        """
        start, end = self._events_query_time_range()
        current_page = 0

        while True:
            if raw_events_in_page := self._query_events_page_in_time_window(
                start,
                end,
                current_page,
                tags,
            ):
                yield from (Event.model_validate(raw_event) for raw_event in raw_events_in_page)
                current_page += 1
                continue

            break

    def _events_query_time_range(self) -> tuple[int, int]:
        now = int(time.time())
        return now - self.max_age, now

    def _query_events_page_in_time_window(
        self,
        start: int,
        end: int,
        page: int,
        tags: Tags,
    ) -> list[object]:
        """
        Query paginated events (endpoint events)
        https://docs.datadoghq.com/api/latest/events/#query-the-event-stream
        """
        params: dict[str, int | str] = {
            "start": start,
            "end": end,
            "page": page,
            "exclude_aggregate": True,
        }
        if tags:
            params["tags"] = ",".join(tags)

        resp = self.datadog_api.get_request(
            "events",
            params,
        )
        resp.raise_for_status()
        return resp.json()["events"]


def _sanitize_event_text(text: str) -> str:
    return text.replace("\n", " ~ ")


def _event_to_syslog_message(
    event: Event,
    tag_regexes: Iterable[str],
    facility: int,
    severity: int,
    service_level: int,
    add_text: bool,
) -> ec.SyslogMessage:
    LOGGER.debug(event)
    matching_tags = ", ".join(
        tag for tag in event.tags if any(re.match(tag_regex, tag) for tag_regex in tag_regexes)
    )
    tags_text = f", Tags: {matching_tags}" if matching_tags else ""
    details_text = f", Text: {event.text}" if add_text else ""
    return ec.SyslogMessage(
        facility=facility,
        severity=severity,
        timestamp=event.date_happened,
        host_name=str(event.host),
        application=event.source,
        service_level=service_level,
        text=_sanitize_event_text(event.title + tags_text + details_text),
    )


def _forward_events_to_ec(
    events: Iterable[Event],
    tag_regexes: Iterable[str],
    facility: int,
    severity: int,
    service_level: int,
    add_text: bool,
) -> None:
    ec.forward_to_unix_socket(
        _event_to_syslog_message(
            event,
            tag_regexes,
            facility,
            severity,
            service_level,
            add_text,
        )
        for event in events
    )


class LogAttributes(pydantic.BaseModel, frozen=True):
    # This field is apparently optional, even though the API documentation does not say that.
    # It was observed to be missing when setting log_query to the empty string.
    attributes: Mapping[str, Any] = pydantic.Field(default={})
    host: str
    message: str | None = None
    service: str
    status: str
    tags: Sequence[str]
    timestamp: str


class Log(pydantic.BaseModel, frozen=True):
    attributes: LogAttributes
    id: str


class LogsQuerier:
    def __init__(
        self,
        datadog_api: DatadogAPI,
        max_age: int,
        indexes: Sequence[str],
        query: str,
        hostname: str,
        cooldown_too_many_requests: int = 5,
    ) -> None:
        self.datadog_api: Final = datadog_api
        self.id_store: Final = IDStore[str](
            paths.tmp_dir / "agents" / "agent_datadog" / f"{hostname}_logs.json"
        )
        self.max_age: Final = max_age
        self.indexes: Final = indexes
        self.query: Final = query
        self.cooldown_too_many_requests: Final = cooldown_too_many_requests

    def query_logs(
        self,
    ) -> Iterable[Log]:
        last_ids = self.id_store.read()
        queried_logs = list(self._execute_query())
        self.id_store.write(log.id for log in queried_logs)
        yield from (log for log in queried_logs if log.id not in last_ids)

    def _execute_query(
        self,
    ) -> Iterable[Log]:
        """
        Query logs from the endpoint events
        https://docs.datadoghq.com/api/latest/logs/#search-logs
        """
        start, end = self._query_time_range()
        cursor: str | None = None

        while True:
            response = self._query_logs_page_in_time_window(
                start,
                end,
                self.query,
                self.indexes,
                cursor,
            )
            yield from (Log.model_validate(raw_log) for raw_log in response["data"])
            if (meta := response.get("meta")) is None:
                break

            if "page" not in meta:
                break
            cursor = meta["page"].get("after")

    def _query_time_range(self) -> tuple[datetime.datetime, datetime.datetime]:
        now = datetime.datetime.now()
        return now - datetime.timedelta(seconds=self.max_age), now

    def _query_logs_page_in_time_window(
        self,
        start: datetime.datetime,
        end: datetime.datetime,
        query: str,
        indexes: Sequence[str],
        cursor: str | None,
    ) -> Mapping[str, Any]:
        body: dict[str, Any] = {
            "filter": {
                "from": self._datetime_to_api_compliant_str(start),
                "to": self._datetime_to_api_compliant_str(end),
                "query": query,
                "indexes": indexes,
            },
            "page": {"limit": 200},
            "sort": "timestamp",
        }
        if cursor is not None:
            body["page"]["cursor"] = cursor

        resp = self.datadog_api.post_request("logs/events/search", body, version="v2")
        while HTTPStatus(resp.status_code) is HTTPStatus.TOO_MANY_REQUESTS:
            LOGGER.debug(
                "Encountered %s, sleeping %s seconds",
                int(HTTPStatus.TOO_MANY_REQUESTS),
                self.cooldown_too_many_requests,
            )
            time.sleep(self.cooldown_too_many_requests)
            resp = self.datadog_api.post_request("logs/events/search", body, version="v2")
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _datetime_to_api_compliant_str(d: datetime.datetime) -> str:
        return d.astimezone().isoformat(timespec="seconds")


_SEVERITY_MAPPER: Mapping[str, int] = {
    "emergency": 0,
    "alert": 1,
    "critical": 2,
    "crit": 2,
    "error": 3,
    "warning": 4,
    "warn": 4,
    "notice": 5,
    "informational": 6,
    "info": 6,
    "debug": 7,
}


def _get_nested(attributes: Mapping[str, Any], nested_keys: str) -> str | None:
    if "." in nested_keys:
        next_key, remainder = nested_keys.split(".", maxsplit=1)
        return _get_nested(attributes.get(next_key, {}), remainder)
    return attributes.get(nested_keys)


def _sanitize_log_text(text: str) -> str:
    return text.replace("'", "").replace("{", "").replace("}", "").replace("\n", " ~ ")


def _log_to_syslog_message(
    log: Log,
    facility: int,
    service_level: int,
    translator: Sequence[LogMessageElement],
) -> ec.SyslogMessage:
    LOGGER.debug(log)
    attributes = dict(log.attributes)
    text_elements = {el.name: _get_nested(attributes, el.key) for el in translator}
    for name, value in text_elements.items():
        if value is None:
            LOGGER.debug("Did not find value for message element: %s", name)
    return ec.SyslogMessage(
        facility=facility,
        service_level=service_level,
        severity=_SEVERITY_MAPPER[log.attributes.status],
        timestamp=dateutil_parser.isoparse(log.attributes.timestamp).timestamp(),
        host_name=log.attributes.host,
        application=log.attributes.service,
        text=_sanitize_event_text(
            ", ".join(
                f"{name}={_sanitize_log_text(repr(value))}"
                for name, value in text_elements.items()
                if value is not None
            )
        ),
    )


def _forward_logs_to_ec(
    logs: Iterable[Log],
    facility: int,
    service_level: int,
    translator: Sequence[LogMessageElement],
) -> None:
    ec.forward_to_unix_socket(
        _log_to_syslog_message(
            log,
            facility,
            service_level,
            translator,
        )
        for log in logs
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


def _logs_section(datadog_api: DatadogAPI, args: Args) -> None:
    LOGGER.debug("Querying logs")
    logs = list(
        LogsQuerier(
            datadog_api,
            args.log_max_age,
            query=args.log_query,
            indexes=args.log_indexes,
            hostname=args.hostname,
        ).query_logs()
    )
    _forward_logs_to_ec(
        logs,
        facility=args.log_syslog_facility,
        service_level=args.log_service_level,
        translator=args.log_text,
    )
    with SectionWriter("datadog_logs") as writer:
        writer.append(len(logs))


def agent_datadog_main(args: Args) -> int:
    datadog_api = ImplDatadogAPI(
        args.api_host,
        args.api_key,
        args.app_key,
        proxy=args.proxy,
    )
    for section in args.sections:
        {"monitors": _monitors_section, "events": _events_section, "logs": _logs_section}[section](
            datadog_api,
            args,
        )
    return 0


def main() -> int:
    """Main entry point to be used"""
    return special_agent_main(parse_arguments, agent_datadog_main)
