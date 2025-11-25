#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path
from types import TracebackType
from typing import Any, NamedTuple, Self

import msal
import requests
from requests import JSONDecodeError

from cmk.password_store.v1_unstable import PasswordStore, Secret
from cmk.server_side_programs.v1_unstable import Storage


class AuthorityURLs(NamedTuple):
    login: str
    resource: str
    base: str


ONE_DAY_IN_SECONDS = 24 * 60 * 60


class GraphApiClient:
    EXPIRY_OVERLAP = 300  # seconds

    def __init__(
        self,
        tenant: str,
        client: str,
        secret: str,
        authority_urls: AuthorityURLs,
        pw_store: PasswordStore,
        pw_store_file: Path,
        storage: Storage,
        initial_access_token: str,
        initial_refresh_token: str,
    ):
        self._login_url = authority_urls.login
        self._resource_url = authority_urls.resource
        self._base_url = authority_urls.base

        self._tenant = tenant
        self._client = client
        self._secret = secret

        self._pw_store = pw_store
        self._pw_store_file = pw_store_file
        self._storage = storage

        self._headers: dict[str, str | bytes] = {}
        self._session: requests.Session | None = None
        self._session_closed = False

        self._initial_access_token = Secret(initial_access_token)
        self._initial_refresh_token = Secret(initial_refresh_token)

    def __enter__(self) -> Self:
        if self._session is None or self._session_closed:
            self._session = self._login_and_create_session()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._session and not self._session_closed:
            self._session.close()
            self._session_closed = True
        self._session = None

    def _get_stored_token(self, secret_id: str, default: Secret[str]) -> str:
        try:
            store_bytes = self._pw_store_file.read_bytes()
        except FileNotFoundError:
            return default.reveal()

        store = self._pw_store.load_bytes(store_bytes)
        try:
            return store[secret_id].reveal()
        except KeyError:
            return default.reveal()

    def _store_token(self, secret_id: str, value: Secret[str]) -> None:
        try:
            store_bytes = self._pw_store_file.read_bytes()
            store = {**self._pw_store.load_bytes(store_bytes)}
        except FileNotFoundError:
            store = {}
        store[secret_id] = value
        self._pw_store_file.write_bytes(self._pw_store.dump_bytes(store))

    @property
    def refresh_token(self) -> str:
        return self._get_stored_token("refresh_token", self._initial_refresh_token)

    @refresh_token.setter
    def refresh_token(self, value: Secret[str]) -> None:
        self._store_token("refresh_token", value)

    @property
    def access_token(self) -> str:
        return self._get_stored_token("access_token", self._initial_access_token)

    @access_token.setter
    def access_token(self, value: Secret[str]) -> None:
        self._store_token("access_token", value)

    def request(
        self,
        method: str,
        uri_end: str | None = None,
        full_uri: str | None = None,
        json: dict[str, Any] | None = None,
        params: dict[str, str | bytes] | None = None,
        custom_headers: dict[str, str | bytes] | None = None,
    ) -> object:
        if custom_headers is None:
            custom_headers = {}
        uri = full_uri or self._base_url + (uri_end or "")
        if not uri:
            raise ValueError("No URI provided")

        if self._session is None or self._session_closed:
            raise RuntimeError(
                "Session is not active. Use 'with GraphApiClient(...) as client: ...'"
            )

        with self._session.request(
            method,
            uri,
            headers=custom_headers,
            json=json,
            params=params,
        ) as response:
            try:
                json_data = response.json()
            # not always contains JSON data, it can for example also be 202 Accepted with no body
            except JSONDecodeError:
                json_data = {}

        if (error := json_data.get("error")) is not None:
            raise RuntimeError(error)

        return json_data

    def get(
        self,
        uri_end: str,
        params: dict[str, str | bytes] | None = None,
    ) -> object:
        return self.request(
            method="GET",
            uri_end=uri_end,
            params=params,
        )

    def login(self, tenant: str, client: str, secret: str) -> None:
        client_app = msal.ConfidentialClientApplication(  # type: ignore[attr-defined, no-untyped-call]
            client,
            secret,
            f"{self._login_url}/{tenant}",
        )
        if access_token_expiry := self._storage.read("access_token_expiry", None):
            if int(access_token_expiry) > int(time.time()) + self.EXPIRY_OVERLAP:
                self._headers.update(
                    {
                        "Authorization": "Bearer %s" % self.access_token,
                        "Content-Type": "application/json",
                        "ClientType": "monitoring-custom-client-type",
                    }
                )
                return
        if refresh_token_expiry := self._storage.read("refresh_token_expiry", None):
            if int(refresh_token_expiry) > int(time.time()) + self.EXPIRY_OVERLAP:
                if self._try_refresh_via_initial_token(client_app):
                    return
                raise RuntimeError(
                    "Refresh token has expired, re-login required. "
                    "Please re-connect to your mailbox via the UI."
                )
        self._refresh_token(client_app)

    def _try_refresh_via_initial_token(
        self,
        client_app: msal.ConfidentialClientApplication,  # type: ignore[name-defined]
    ) -> bool:
        token = client_app.acquire_token_by_refresh_token(
            refresh_token=self._initial_refresh_token.reveal(),
            scopes=[self._resource_url + "/.default"],
        )

        if token.get("error"):
            return False

        self._update_tokens_after_refresh(
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
            access_token_expires_in=token["expires_in"],
        )
        return True

    def _refresh_token(self, client_app: msal.ConfidentialClientApplication) -> None:  # type: ignore[name-defined]
        token = client_app.acquire_token_by_refresh_token(
            refresh_token=self.refresh_token,
            scopes=[self._resource_url + "/.default"],
        )

        if error := token.get("error"):
            if error_description := token.get("error_description"):
                error = f"{error}. {error_description}"
            raise RuntimeError(error)
        self._update_tokens_after_refresh(
            access_token=token["access_token"],
            refresh_token=token["refresh_token"],
            access_token_expires_in=token["expires_in"],
        )

    def _update_tokens_after_refresh(
        self, access_token: str, refresh_token: str, access_token_expires_in: int
    ) -> None:
        self.refresh_token = Secret(access_token)
        self.access_token = Secret(refresh_token)
        self._storage.write("access_token_expiry", str(access_token_expires_in + int(time.time())))
        self._storage.write("refresh_token_expiry", str(ONE_DAY_IN_SECONDS + int(time.time())))
        self._headers.update(
            {
                "Authorization": "Bearer %s" % self.access_token,
                "Content-Type": "application/json",
                "ClientType": "monitoring-custom-client-type",
            }
        )

    def _login_and_create_session(self) -> requests.Session:
        self.login(tenant=self._tenant, client=self._client, secret=self._secret)
        if self._session is None or self._session_closed:
            session = requests.Session()
            session.headers.update(self._headers)
            return session
        return self._session
