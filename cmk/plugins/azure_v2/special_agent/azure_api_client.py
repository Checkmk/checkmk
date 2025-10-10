#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import asyncio
import logging
import os
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Literal, NamedTuple

# mypy: disable-error-code="no-untyped-call"
# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

# workaround - can be removed when CMK-25281 is resolved
os.environ["SSL_CERT_FILE"] = str(Path(os.getenv("OMD_ROOT", "")) / "var/ssl/ca-certificates.crt")

import aiohttp
import msal

from cmk.utils.http_proxy_config import HTTPProxyConfig

LOGGER = logging.getLogger("azure_v2_api_client")


class ApiError(RuntimeError):
    pass


class ApiLoginFailed(ApiError):
    pass


class ApiErrorMissingData(ApiError):
    pass


class NoConsumptionAPIError(ApiError):
    pass


class ApiErrorAuthorizationRequestDenied(ApiError):
    pass


class RateLimitException(ApiError):
    def __init__(self, message: str, context: Mapping[str, str | int]):
        super().__init__(message)
        self.context = context


def _make_exception(error_data: object) -> ApiError:
    match error_data:
        case {"code": "Authorization_RequestDenied", **rest}:
            message = rest.get("message", error_data)
            return ApiErrorAuthorizationRequestDenied(message)
        case {"code": _, "message": message}:
            return ApiError(message)
        case other:
            return ApiError(other)


class _AuthorityURLs(NamedTuple):
    login: str
    resource: str
    base: str
    regional: Callable[[str], str] | None = None


def get_graph_authority_urls(authority: Literal["global", "china"]) -> _AuthorityURLs:
    if authority == "global":
        return _AuthorityURLs(
            "https://login.microsoftonline.com",
            "https://graph.microsoft.com",
            "https://graph.microsoft.com/v1.0/",
        )
    if authority == "china":
        return _AuthorityURLs(
            "https://login.partner.microsoftonline.cn",
            "https://microsoftgraph.chinacloudapi.cn",
            "https://microsoftgraph.chinacloudapi.cn/v1.0/",
        )
    raise ValueError("Unknown authority %r" % authority)


def _get_regional_url_func(subscription: str) -> Callable[[str], str]:
    def get_regional_url(region: str) -> str:
        return f"https://{region}.metrics.monitor.azure.com/subscriptions/{subscription}"

    return get_regional_url


def get_mgmt_authority_urls(
    authority: Literal["global", "china"], subscription: str
) -> _AuthorityURLs:
    if authority == "global":
        return _AuthorityURLs(
            "https://login.microsoftonline.com",
            "https://management.azure.com",
            f"https://management.azure.com/subscriptions/{subscription}/",
            _get_regional_url_func(subscription),
        )
    if authority == "china":
        return _AuthorityURLs(
            "https://login.partner.microsoftonline.cn",
            "https://management.chinacloudapi.cn",
            f"https://management.chinacloudapi.cn/subscriptions/{subscription}/",
            lambda r: f"https://metrics.monitor.azure.cn/subscriptions/{subscription}/",
        )
    raise ValueError("Unknown authority %r" % authority)


class BaseAsyncApiClient:
    def __init__(
        self,
        authority_urls: _AuthorityURLs,
        http_proxy_config: HTTPProxyConfig,
        tenant: str,
        client: str,
        secret: str,
    ):
        self._login_url = authority_urls.login
        self._resource_url = authority_urls.resource
        self._base_url = authority_urls.base
        self._regional_url = authority_urls.regional
        self._http_proxy_config = http_proxy_config

        self._tenant = tenant
        self._client = client
        self._secret = secret

        self._headers: dict = {}
        self._ratelimit = float("Inf")
        self._session: aiohttp.ClientSession | None = None

    def build_regional_url(self, region: str, uri_end: str) -> str:
        if self._regional_url is None:
            raise ValueError("Regional URL not configured")

        return self._regional_url(region) + uri_end

    @property
    def ratelimit(self):
        if isinstance(self._ratelimit, int):
            return self._ratelimit
        return None

    def _update_ratelimit(self, response: aiohttp.ClientResponse) -> None:
        try:
            new_value = int(response.headers["x-ms-ratelimit-remaining-subscription-reads"])
        except (KeyError, ValueError, TypeError):
            return
        self._ratelimit = min(self._ratelimit, new_value)

    @staticmethod
    def lookup_json_data(json_data, key):
        try:
            return json_data[key]
        except KeyError:
            raise _make_exception(json_data)

    async def _login_and_create_session(self) -> aiohttp.ClientSession:
        await self.login_async(tenant=self._tenant, client=self._client, secret=self._secret)
        if self._session is None or self._session.closed:
            proxy_mapping = self._http_proxy_config.to_requests_proxies()
            session = aiohttp.ClientSession(
                # aiohttp session and aiohttp request only accept a string as proxy
                # (not the mapping with multiple schemes of the classical requests library)
                # I assume it will always be https since all the url (for management and graph) are https
                headers=self._headers,
                proxy=proxy_mapping["https"] if proxy_mapping else None,
                timeout=aiohttp.ClientTimeout(total=30),
            )

        return session

    async def __aenter__(self):
        if self._session is None or self._session.closed:
            self._session = await self._login_and_create_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def login_async(self, tenant: str, client: str, secret: str) -> None:
        client_app = msal.ConfidentialClientApplication(  # type: ignore[attr-defined]
            client,
            secret,
            f"{self._login_url}/{tenant}",
            proxies=self._http_proxy_config.to_requests_proxies(),
        )
        # this should be safe,
        # the default thread pool in asyncio typically has a maximum number of worker threads
        # tied to the system's CPU count
        token = await asyncio.to_thread(
            client_app.acquire_token_for_client, [self._resource_url + "/.default"]
        )

        if error := token.get("error"):
            if error_description := token.get("error_description"):
                error = f"{error}. {error_description}"
            raise ApiLoginFailed(error)

        self._headers.update(
            {
                "Authorization": "Bearer %s" % token["access_token"],
                "Content-Type": "application/json",
                "ClientType": "monitoring-custom-client-type",
            }
        )

    async def _handle_ratelimit_async(self, method, url, custom_headers=None, **kwargs):
        async def get_response():
            if self._session is None or self._session.closed:
                raise RuntimeError(
                    "Session is not active. Use 'async with BaseAsyncApiClient(...) as client: ...'"
                )

            async with self._session.request(
                method, url, headers=custom_headers, **kwargs
            ) as response:
                await response.json()
                return response

        raise_for_rate_limit = kwargs.pop("raise_for_rate_limit", False)
        response = await get_response()
        for cool_off_interval in (5, 10):
            if response.status != 429:
                break
            if raise_for_rate_limit:
                raise RateLimitException(
                    f"Rate limit exceeded for {method} {url}: {response.status} {response.reason}",
                    context=response.headers,
                )

            LOGGER.error("Rate limit exceeded, waiting %s seconds", cool_off_interval)
            await asyncio.sleep(cool_off_interval)
            response = await get_response()
        self._update_ratelimit(response)

        return response

    async def request_async(
        self,
        method,
        uri_end=None,
        full_uri=None,
        body=None,
        key=None,
        params=None,
        next_page_key="nextLink",
        custom_headers={},
        raise_for_rate_limit=False,
    ):
        uri = full_uri or self._base_url + uri_end
        if not uri:
            raise ValueError("No URI provided")

        LOGGER.debug("Querying uri: %r", uri)
        response = await self._handle_ratelimit_async(
            method,
            uri,
            custom_headers=custom_headers,
            json=body,
            params=params,
            raise_for_rate_limit=raise_for_rate_limit,
        )
        json_data = await response.json()
        LOGGER.debug("API response: %r", json_data)

        if (error := json_data.get("error")) is not None:
            raise _make_exception(error)

        if key is None:  # we do not paginate here without a key
            return json_data

        data = self.lookup_json_data(json_data, key)

        while next_link := json_data.get(next_page_key):
            json_data = await self.request_async(method, full_uri=next_link, body=body)
            data += self.lookup_json_data(json_data, key)

        return data

    async def get_async(
        self,
        uri_end,
        key=None,
        params=None,
        next_page_key="nextLink",
    ):
        return await self.request_async(
            method="GET",
            uri_end=uri_end,
            key=key,
            params=params,
            next_page_key=next_page_key,
        )


class SharedSessionApiClient(BaseAsyncApiClient):
    _shared_session: aiohttp.ClientSession | None = None
    _sessions_count: int = 0
    _shared_session_lock: asyncio.Lock | None = None

    def __init__(
        self,
        authority_urls: _AuthorityURLs,
        http_proxy_config: HTTPProxyConfig,
        tenant: str,
        client: str,
        secret: str,
    ):
        super().__init__(authority_urls, http_proxy_config, tenant, client, secret)
        if SharedSessionApiClient._shared_session_lock is None:
            SharedSessionApiClient._shared_session_lock = asyncio.Lock()

    async def __aenter__(self):
        if SharedSessionApiClient._shared_session_lock is None:
            raise RuntimeError(
                "Session lock is not initialized. Ensure that the client is correctly created."
            )

        async with SharedSessionApiClient._shared_session_lock:
            LOGGER.debug("Acquiring lock for session setup...")
            if (
                SharedSessionApiClient._shared_session is None
                or SharedSessionApiClient._shared_session.closed
            ):
                SharedSessionApiClient._shared_session = await self._login_and_create_session()
                LOGGER.debug("Created new aiohttp session")

        SharedSessionApiClient._sessions_count += 1
        self._session = SharedSessionApiClient._shared_session
        LOGGER.debug("Lock released, session ready")

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if SharedSessionApiClient._shared_session_lock is None:
            raise RuntimeError(
                "Session lock is not initialized. Ensure that the client is correctly created."
            )

        async with SharedSessionApiClient._shared_session_lock:
            SharedSessionApiClient._sessions_count -= 1
            if (
                SharedSessionApiClient._sessions_count <= 0
                and SharedSessionApiClient._shared_session
                and not SharedSessionApiClient._shared_session.closed
            ):
                await SharedSessionApiClient._shared_session.close()
                SharedSessionApiClient._shared_session = None

        self._session = None
