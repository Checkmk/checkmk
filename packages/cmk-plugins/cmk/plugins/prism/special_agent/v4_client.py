#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Client for the Nutanix v4 API on Prism Central"""

import logging
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timedelta, UTC
from http import HTTPStatus
from http.cookiejar import DefaultCookiePolicy

import requests
from requests.auth import HTTPBasicAuth
from urllib3.exceptions import ReadTimeoutError
from urllib3.util.retry import Retry

from cmk.plugins.prism.special_agent.session import new_session

LOGGER = logging.getLogger(__name__)

type JsonObject = Mapping[str, object]
type QueryParams = Mapping[str, str | int]

PAGE_LIMIT = 100
ATTEMPTS = 4
# Only status codes are retried: a timeout is not, so a call can't overrun its share of the
# time budget. Worst case per call: its share of the remaining budget plus 3 x 5 s waiting.
RETRY = Retry(
    total=ATTEMPTS - 1,
    connect=0,
    read=0,
    status_forcelist=(408, 429, 503, 504),
    allowed_methods=("GET",),
    backoff_factor=0.5,
    backoff_max=4,
    retry_after_max=5,
)


class PrismV4Error(Exception):
    pass


def _as_object(value: object, what: str) -> JsonObject:
    if not isinstance(value, dict):
        raise PrismV4Error(f"{what}: expected a JSON object, got {type(value).__name__}")
    return value


def _entities(body: JsonObject, path: str) -> list[JsonObject]:
    data = body.get("data")
    if data is None:
        return []
    if not isinstance(data, list):
        raise PrismV4Error(f"{path}: expected a list in 'data', got {type(data).__name__}")
    return [_as_object(entry, path) for entry in data]


def _metadata(body: JsonObject) -> JsonObject:
    return metadata if isinstance(metadata := body.get("metadata"), dict) else {}


def _has_next_page(body: JsonObject) -> bool:
    links = _metadata(body).get("links")
    return isinstance(links, list) and any(
        isinstance(link, dict) and link.get("rel") == "next" for link in links
    )


def _messages(error: object) -> str:
    """The texts of an AppMessage list or of a SchemaValidationError"""
    if isinstance(error, dict):
        error = error.get("validationErrorMessages") or [error]
    if not isinstance(error, list):
        return ""
    return "; ".join(
        message
        for item in error
        if isinstance(item, dict) and isinstance(message := item.get("message"), str)
    )


def _error_response(body: object) -> str | None:
    """Prism Central answers errors with an ErrorResponse in `data`"""
    if not isinstance(body, dict) or not isinstance(data := body.get("data"), dict):
        return None
    if "error" not in data:
        return None
    return _messages(data["error"]) or "no details"


def _has_error_flag(body: JsonObject) -> bool:
    flags = _metadata(body).get("flags")
    return isinstance(flags, list) and any(
        isinstance(flag, dict) and flag.get("name") == "hasError" and flag.get("value") is True
        for flag in flags
    )


def _json(response: requests.Response) -> object:
    try:
        return response.json()
    except ValueError:
        return None


def _http_error(response: requests.Response) -> str:
    body = _json(response)
    # A rejected login comes as {"message": ...} instead of an ErrorResponse
    plain = body.get("message") if isinstance(body, dict) else None
    detail = _error_response(body) or (plain if isinstance(plain, str) else response.reason)
    return f"HTTP {response.status_code} {detail}"


def _describe(error: requests.exceptions.RequestException) -> str:
    match error:
        case requests.exceptions.Timeout():
            return "timed out"
        case requests.exceptions.SSLError():
            return "TLS handshake failed"
        # requests wraps a timeout while reading the body as a ConnectionError
        case requests.exceptions.ConnectionError(args=(ReadTimeoutError(), *_)):
            return "timed out"
        case requests.exceptions.ConnectionError():
            return "connection failed"
        case requests.exceptions.RetryError():
            reason = getattr(error.args[0], "reason", None) if error.args else None
            return f"gave up after {ATTEMPTS} attempts ({reason or 'retries exhausted'})"
        case _:
            return type(error).__name__


def _iso(timestamp: datetime) -> str:
    return timestamp.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _with_stats_timestamp(select: Sequence[str]) -> Sequence[str]:
    """vmm stats tuples only carry their timestamp if it is selected"""
    if any(field.startswith("stats/") for field in select) and "stats/timestamp" not in select:
        return [*select, "stats/timestamp"]
    return select


class PrismV4Client:
    """Owns everything about talking to the API: session, retries, paging and
    the time budget. All failures are raised as PrismV4Error."""

    def __init__(
        self,
        base_url: str,
        username: str,
        password: str,
        cert_check: bool | str,
        timeout: int,
        deadline: float,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._session = new_session(base_url, cert_check, RETRY)
        # HostnameValidationAdapter overrides the Host header, so the session's cookie jar
        # files the cookies under the certificate name and never sends them back. The
        # client keeps them itself.
        self._session.cookies.set_policy(DefaultCookiePolicy(allowed_domains=[]))
        self._cookies: dict[str, str] = {}
        self._basic_auth = HTTPBasicAuth(username, password)
        self._auth_lock = threading.Lock()
        self._verify = cert_check is not False
        self._base_url = base_url
        self._timeout = timeout
        self._deadline = deadline
        self._now = now

    def get(self, path: str, params: QueryParams | None = None) -> JsonObject:
        try:
            response = self._authenticated_get(f"{self._base_url}/api/{path}", params)
        except requests.exceptions.RequestException as e:
            LOGGER.debug("%(path)s failed", {"path": path}, exc_info=True)
            raise PrismV4Error(f"{path}: {_describe(e)}") from e
        if not response.ok:
            raise PrismV4Error(f"{path}: {_http_error(response)}")
        if (remaining := response.headers.get("x-ratelimit-remaining")) is not None:
            LOGGER.debug("rate limit remaining: %(remaining)s", {"remaining": remaining})
        body = _as_object(_json(response), path)
        if (error := _error_response(body)) is not None or _has_error_flag(body):
            raise PrismV4Error(f"{path}: Prism Central reports an error: {error or 'no details'}")
        return body

    def _authenticated_get(self, url: str, params: QueryParams | None) -> requests.Response:
        """Basic auth only until Prism Central hands out session cookies, then the cookies
        alone; expired cookies are renewed once."""
        with self._auth_lock:
            cookies = dict(self._cookies)
        response = self._send(url, params, cookies)
        if response.status_code == HTTPStatus.UNAUTHORIZED and cookies:
            with self._auth_lock:
                if self._cookies == cookies:
                    self._cookies = {}
                cookies = dict(self._cookies)
            response = self._send(url, params, cookies)
        if response.cookies:
            with self._auth_lock:
                self._cookies.update(
                    {cookie.name: cookie.value or "" for cookie in response.cookies}
                )
        return response

    def _send(
        self, url: str, params: QueryParams | None, cookies: Mapping[str, str]
    ) -> requests.Response:
        if (remaining := self._deadline - time.monotonic()) <= 0:
            raise PrismV4Error("the time budget of this agent run is used up")
        return self._session.get(
            url,
            params=params,
            auth=None if cookies else self._basic_auth,
            headers={"Cookie": "; ".join(f"{k}={v}" for k, v in cookies.items())}
            if cookies
            else None,
            # All attempts of a retried call share what is left of the time budget
            timeout=min(self._timeout, remaining / ATTEMPTS),
            # Pass `verify` explicitly, otherwise REQUESTS_CA_BUNDLE would override it.
            verify=self._verify,
        )

    def list_all(self, path: str, params: QueryParams | None = None) -> list[JsonObject]:
        """Follow the pages of a list call as long as the API links a next one"""
        entities: list[JsonObject] = []
        page = 0
        while True:
            body = self.get(path, {**(params or {}), "$page": page, "$limit": PAGE_LIMIT})
            entities.extend(_entities(body, path))
            if not _has_next_page(body):
                return entities
            page += 1

    def _stats_params(
        self,
        window: timedelta,
        sampling_interval: timedelta,
        stat_type: str,
        select: Sequence[str],
    ) -> QueryParams:
        end = self._now()
        params: dict[str, str | int] = {
            "$startTime": _iso(end - window),
            "$endTime": _iso(end),
            "$samplingInterval": int(sampling_interval.total_seconds()),
            "$statType": stat_type,
        }
        if select:
            params["$select"] = ",".join(_with_stats_timestamp(select))
        return params

    def entity_stats(
        self,
        path: str,
        *,
        window: timedelta,
        sampling_interval: timedelta,
        stat_type: str = "LAST",
        select: Sequence[str] = (),
    ) -> JsonObject:
        """The raw stats of one entity, as time series

        The parse function picks the samples it needs. Fetchers must stay stateless: ask for
        a window and an aggregation (stat_type) that cover the check interval instead of
        remembering the last run.
        """
        body = self.get(path, self._stats_params(window, sampling_interval, stat_type, select))
        return _as_object(body.get("data", {}), path)

    def list_stats(
        self,
        path: str,
        *,
        window: timedelta,
        sampling_interval: timedelta,
        stat_type: str = "LAST",
        select: Sequence[str] = (),
    ) -> list[JsonObject]:
        """The raw stats of all entities of a list call, e.g. vmm/v4.0/ahv/stats/vms"""
        return self.list_all(path, self._stats_params(window, sampling_interval, stat_type, select))
