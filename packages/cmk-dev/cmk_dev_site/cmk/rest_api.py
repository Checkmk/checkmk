# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import time
from pathlib import Path
from typing import (
    Any,
    NotRequired,
    override,
    TypedDict,
    TypeVar,
)

import requests
from requests.exceptions import JSONDecodeError

T = TypeVar("T")


class BasicSettings(TypedDict):
    alias: str
    site_id: str
    customer: NotRequired[str]


class ConnectionDetails(TypedDict):
    socket_type: str
    host: str
    port: int
    encrypted: bool
    verify: bool


class StatusHost(TypedDict):
    status_host_set: str


class StatusConnection(TypedDict):
    connection: ConnectionDetails
    proxy: dict[str, str]
    connect_timeout: int
    persistent_connection: bool
    url_prefix: str
    status_host: StatusHost
    disable_in_status_gui: bool


class UserSync(TypedDict):
    sync_with_ldap_connections: str


class AuthenticationConnections(TypedDict):
    type: str


class ConfigurationConnection(TypedDict):
    enable_replication: bool
    url_of_remote_site: str
    disable_remote_configuration: bool
    ignore_tls_errors: bool
    direct_login_to_web_gui_allowed: bool
    authentication_connections: NotRequired[AuthenticationConnections]
    user_sync: UserSync
    replicate_event_console: bool
    replicate_extensions: bool
    message_broker_port: NotRequired[int]
    is_trusted: bool


class RemoteSiteConnectionConfig(TypedDict):
    basic_settings: BasicSettings
    status_connection: StatusConnection
    configuration_connection: ConfigurationConnection


class CheckmkAPIException(Exception):
    """Base exception for Checkmk API errors."""

    def __init__(  # type: ignore[explicit-any]
        self,
        message: str,
        status_code: int | None = None,
        response_data: dict[Any, Any] | str | None = None,
    ):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

    @override
    def __str__(self) -> str:
        parts = [super().__str__()]
        if self.status_code is not None:
            parts.append(f"Status code: {self.status_code}")
        if self.response_data is not None:
            parts.append(f"Response: {self.response_data}")
        return "\n".join(parts)


def build_exception(response: requests.Response, message: str) -> CheckmkAPIException:
    try:
        return CheckmkAPIException(
            message=message,
            status_code=response.status_code,
            response_data=response.json(),
        )
    except JSONDecodeError:
        return CheckmkAPIException(
            message=message + "\nFailed to parse response",
            status_code=response.status_code,
            response_data=response.text if response.text else None,
        )


class APIClient:
    """Checkmk API client."""

    def __init__(
        self,
        site_name: str = "heute",
        username: str = "cmkadmin",
        password: str = "cmk",
        # Note: don't be confused with the hosts registered on checkmk
        server_host_name: str = "localhost",
        proto: str = "http",
    ) -> None:
        self.base_url = f"{proto}://{server_host_name}/{site_name}/check_mk/api/1.0"

        self.site_name = site_name
        self.session = requests.session()
        self.session.headers["Authorization"] = f"Bearer {username} {password}"
        self.session.headers["Accept"] = "application/json"

    def version(self) -> dict[str, str] | None:
        response = self.session.get(
            f"{self.base_url}/version",
            headers={
                "Content-Type": "application/json",
            },
        )
        if response.status_code == 200:  # astrein: disable=http-status-literal
            return response.json()  # type: ignore[no-any-return]
        return None

    def create_host(
        self,
        host_name: str,
        logical_site_name: str | None = None,
        ip_address: str = "127.0.0.1",
    ) -> None:
        """Create a host on the Checkmk server."""
        logical_site_name = logical_site_name or self.site_name
        response = self.session.post(
            f"{self.base_url}/domain-types/host_config/collections/all",
            headers={
                "Content-Type": "application/json",
            },
            json={
                "host_name": host_name,
                "folder": "/",
                "attributes": {
                    "ipaddress": ip_address,
                    "site": logical_site_name,
                },
            },
        )
        if response.status_code != 200:  # astrein: disable=http-status-literal
            raise build_exception(response, message="Failed to create host")

    def list_all_hosts(self) -> list[str]:
        """List all hosts registered on the Checkmk server."""
        response = self.session.get(
            f"{self.base_url}/domain-types/host_config/collections/all",
            headers={
                "Content-Type": "application/json",
            },
        )
        if response.status_code != 200:  # astrein: disable=http-status-literal
            raise build_exception(response, message="Failed to list all hosts")

        hosts = [host["title"] for host in response.json()["value"]]
        return hosts  # noqa: RET504

    def _get_href_from_links(self, links: list[dict[str, str]], name: str) -> str | None:
        """Extract the href from the links."""
        for link in links:
            if link["rel"] == name:
                return link["href"]
        return None

    def _get(self, url: str) -> requests.Response:
        """Make a GET request to the Checkmk server."""
        full_url = url if url.startswith(("http://", "https://")) else f"{self.base_url}{url}"
        return self.session.get(full_url)

    def create_site_connection(self, site_config: RemoteSiteConnectionConfig) -> None:
        """Create a site connection on the Checkmk server."""
        response = self.session.post(
            f"{self.base_url}/domain-types/site_connection/collections/all",
            headers={
                "Content-Type": "application/json",
            },
            json={"site_config": site_config},  # type: ignore[dict-item]
        )

        if response.status_code != 200:  # astrein: disable=http-status-literal
            raise build_exception(response, "Failed to create site connection")

    def set_user_language(self, language: str) -> None:
        """Set the user language on the Checkmk server."""
        response = self.session.put(
            f"{self.base_url}/objects/user_config/cmkadmin",
            headers={
                # (required) The value of the, to be modified, object's ETag header.
                "If-Match": "*",
                "Content-Type": "application/json",
            },
            json={"language": language},
        )
        if response.status_code != 200:  # astrein: disable=http-status-literal
            raise build_exception(response, "Failed to set user language")

    def list_all_site_connections(self) -> list[str]:
        """List all site connections registered on the Checkmk server."""
        response = self.session.get(
            f"{self.base_url}/domain-types/site_connection/collections/all",
            headers={
                "Content-Type": "application/json",
            },
        )
        if response.status_code != 200:  # astrein: disable=http-status-literal
            raise build_exception(response, "Failed to list all site connections")

        site_connections = [site["id"] for site in response.json()["value"]]
        return site_connections  # noqa: RET504

    def activate_changes(self) -> list[str] | None:
        """Activate pending changes on the Checkmk server.

        Returns:
            list: A list of activated changes if any were made.
            None: If there were no changes to activate.
        """
        response = self.session.post(
            f"{self.base_url}/domain-types/activation_run/actions/activate-changes/invoke",
            headers={
                # (required) The value of the, to be modified, object's ETag header.
                "If-Match": "*",
                # (required) A header specifying which type of content
                # is in the request/response body.
                "Content-Type": "application/json",
            },
            json={
                "redirect": False,
                "sites": [],
                "force_foreign_changes": True,
            },
            allow_redirects=True,
        )

        if response.status_code == 422:  # astrein: disable=http-status-literal
            return None
        if response.status_code != 200:  # astrein: disable=http-status-literal
            raise build_exception(response, "Failed to activate changes")

        changes: set[str] = set()
        # Polling loop
        link = self._get_href_from_links(response.json()["links"], "self")
        if link is None:
            raise build_exception(
                response,
                "Activate change : Failed to find 'self' link in the response",
            )

        while True:
            # Fetch data
            response = self._get(link)
            if response.status_code != 200:  # astrein: disable=http-status-literal
                raise build_exception(response, "Failed to fetch activation changes")
            data = response.json()

            # Process changes
            for change in data["extensions"]["changes"]:
                change_id = change["id"]
                if change_id not in changes:
                    changes.add(change_id)

            # Check if processing is complete
            if not data["extensions"]["is_running"]:
                return list(changes)
            # Wait before polling again
            time.sleep(1)

    def login_to_remote_site(
        self, site_id: str, user: str = "cmkadmin", password: str = "cmk"
    ) -> None:
        response = self.session.post(
            f"{self.base_url}/objects/site_connection/{site_id}/actions/login/invoke",
            headers={
                "Content-Type": "application/json",
            },
            json={"username": user, "password": password},
        )

        if response.status_code != 204:  # astrein: disable=http-status-literal
            raise build_exception(response, "Failed to login to remote site")

    def download_agent(self, download_path: Path) -> None:
        """Download the Checkmk agent."""
        response = self.session.get(
            f"{self.base_url}/domain-types/agent/actions/download/invoke",
            params={"os_type": "linux_deb"},
            headers={
                "Accept": "application/octet-stream",
                "Content-Type": "application/json",
            },
        )
        if response.status_code == 200:  # astrein: disable=http-status-literal
            with open(download_path, "wb") as f:
                f.write(response.content)
        else:
            raise build_exception(response, "Failed to download agent")
