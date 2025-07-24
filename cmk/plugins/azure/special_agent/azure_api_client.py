#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import asyncio
import logging
from collections.abc import Callable, Mapping
from typing import Literal, NamedTuple

import aiohttp  # type: ignore[import-not-found]  # type: ignore[import-not-found]
import msal
import requests

from cmk.utils.http_proxy_config import HTTPProxyConfig

# TODO: improve logger
LOGGER = logging.getLogger()  # root logger for now


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


def _make_exception(error_data: object) -> ApiError:
    match error_data:
        case {"code": "Authorization_RequestDenied", **rest}:
            message = rest.get("message", error_data)
            assert isinstance(message, Mapping)
            return ApiErrorAuthorizationRequestDenied(**message)
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


class BaseApiClient:
    def __init__(
        self,
        authority_urls: _AuthorityURLs,
        http_proxy_config: HTTPProxyConfig,
    ) -> None:
        self._ratelimit = float("Inf")
        self._headers: dict = {}
        self._login_url = authority_urls.login
        self._resource_url = authority_urls.resource
        self._base_url = authority_urls.base
        self._regional_url = authority_urls.regional
        self._http_proxy_config = http_proxy_config

    def build_regional_url(self, region: str, uri_end: str) -> str:
        if self._regional_url is None:
            raise ValueError("Regional URL not configured")

        return self._regional_url(region) + uri_end

    @property
    def ratelimit(self):
        if isinstance(self._ratelimit, int):
            return self._ratelimit
        return None

    def _update_ratelimit(self, response: requests.Response) -> None:
        try:
            new_value = int(response.headers["x-ms-ratelimit-remaining-subscription-reads"])
        except (KeyError, ValueError, TypeError):
            return
        self._ratelimit = min(self._ratelimit, new_value)

    def request(
        self,
        method,
        uri_end=None,
        full_uri=None,
        body=None,
        key=None,
        params=None,
        next_page_key="nextLink",
    ):
        uri = full_uri or self._base_url + uri_end
        if not uri:
            raise ValueError("No URI provided")

        json_data = self._request_json_from_url(method, uri, body=body, params=params)

        if (error := json_data.get("error")) is not None:
            raise _make_exception(error)

        if key is None:  # we do not paginate without a key
            return json_data

        data = self.lookup_json_data(json_data, key)

        while next_link := json_data.get(next_page_key):
            json_data = self._request_json_from_url(method, next_link, body=body)
            data += self.lookup_json_data(json_data, key)

        return data

    def _request_json_from_url(self, method, url, *, body=None, params=None):
        response = requests.request(
            method,
            url,
            json=body,
            params=params,
            headers=self._headers,
            proxies=self._http_proxy_config.to_requests_proxies(),
        )

        json_data = response.json()
        LOGGER.debug("response: %r", json_data)
        return json_data

    @staticmethod
    def lookup_json_data(json_data, key):
        try:
            return json_data[key]
        except KeyError:
            raise _make_exception(json_data)


class BaseAsyncApiClient(BaseApiClient):
    # TODO: type
    def __init__(self, authority_urls, http_proxy_config, tenant, client, secret):
        super().__init__(authority_urls, http_proxy_config)
        self._session = None
        self._tenant = tenant
        self._client = client
        self._secret = secret

    async def __aenter__(self):
        await self.login_async(tenant=self._tenant, client=self._client, secret=self._secret)
        if self._session is None or self._session.closed:
            proxy_mapping = self._http_proxy_config.to_requests_proxies()
            self._session = aiohttp.ClientSession(
                # aiohttp session and aiohttp request only accept a string as proxy
                # (not the mapping with multiple schemes of the classical requests library)
                # I assume it will always be https since all the url (for management and graph) are https
                headers=self._headers,
                proxy=proxy_mapping["https"] if proxy_mapping else None,
                timeout=aiohttp.ClientTimeout(total=30),
            )

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._session and not self._session.closed:
            await self._session.close()
        self._session = None

    async def login_async(self, tenant: str, client: str, secret: str) -> None:
        client_app = msal.ConfidentialClientApplication(
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

        response = await get_response()
        for cool_off_interval in (5, 10):
            if response.status != 429:
                break

            LOGGER.debug("Rate limit exceeded, waiting %s seconds", cool_off_interval)
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
    ):
        uri = full_uri or self._base_url + uri_end
        if not uri:
            raise ValueError("No URI provided")

        response = await self._handle_ratelimit_async(
            method,
            uri,
            custom_headers=custom_headers,
            json=body,
            params=params,
        )
        json_data = await response.json()
        LOGGER.debug("response: %r", json_data)

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
