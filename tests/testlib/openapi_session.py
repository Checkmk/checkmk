import logging
import time
from typing import Any, List, NamedTuple, Optional

import requests

logger = logging.getLogger("rest-session")


class RestSessionException(Exception):
    pass


class UnexpectedResponse(RestSessionException):
    @classmethod
    def from_response(cls, response: requests.Response) -> "UnexpectedResponse":
        return cls(status_code=response.status_code, response_text=response.text)

    def __init__(self, status_code: int, response_text: str) -> None:
        super().__init__(f"[{status_code}] {response_text}")


class AuthorizationFailed(RestSessionException):
    def __init__(self, header: str, site: str) -> None:
        super().__init__(f"Authorization header {header!r} on site {site!r} failed")


class Redirect(RestSessionException):
    def __init__(self, redirect_url: str) -> None:
        super().__init__(redirect_url)
        self.redirect_url = redirect_url


class BakingStatus(NamedTuple):
    state: str
    started: float


class User(NamedTuple):
    title: str


class CMKOpenApiSession(requests.Session):
    def __init__(
        self,
        host: str,
        user: str,
        password: str,
        port: int = 80,
        site: str = "heute",
        api_version: str = "1.0",
    ):
        super().__init__()
        self.host = host
        self.port = port
        self.site = site
        self.api_version = api_version
        self.headers["Accept"] = "application/json"
        self.set_authentication_header(user, password)

    def set_authentication_header(self, user: str, password: str):
        self.headers["Authorization"] = f"Bearer {user} {password}"

    def request(self, method: str, url: str, *args, **kwargs) -> requests.Response:  # type: ignore
        """
        Suggested method to use a base url with a requests.Session
        see https://github.com/psf/requests/issues/2554#issuecomment-109341010
        """
        url = f"http://{self.host}:{self.port}/{self.site}/check_mk/api/{self.api_version}/{url.strip('/')}"

        logger.debug("> [%s] %s (%s, %s)", method, url, args, kwargs)
        response = super().request(method, url, *args, **kwargs)
        logger.debug("< [%s] %s", response.status_code, response.text)

        if response.status_code == 401:
            raise AuthorizationFailed(self.headers["Authorization"], self.site)

        return response

    def activate_changes(
        self,
        sites: Optional[list[str]] = None,
        force_foreign_changes: bool = False,
    ) -> bool:
        """
        Returns
            True if changes are activated
            False if there are no changes to be activated
        """
        response = self.post(
            "/domain-types/activation_run/actions/activate-changes/invoke",
            json={
                "redirect": True,
                "sites": sites or [],
                "force_foreign_changes": force_foreign_changes,
            },
            # We want to get the redirect response and handle that below. So don't let requests
            # handle that for us.
            allow_redirects=False,
        )
        if response.status_code == 200:
            return True  # changes are activated
        if response.status_code == 422:
            return False  # no changes
        if response.status_code == 302:
            raise Redirect(redirect_url=response.headers["Location"])  # activation pending
        raise UnexpectedResponse.from_response(response)

    def activate_changes_and_wait_for_completion(
        self,
        sites: Optional[list[str]] = None,
        force_foreign_changes: bool = False,
        timeout: int = 60,
    ) -> bool:
        start = time.time()
        try:
            return self.activate_changes(sites, force_foreign_changes)
        except Redirect as redirect:
            redirect_url = redirect.redirect_url
            while redirect_url:
                if time.time() > (start + timeout):
                    raise TimeoutError("wait for completion on activate changes timed out")

                response = self.get(redirect_url, allow_redirects=False)
                if response.status_code == 204:
                    break
                if response.status_code == 302:
                    # Would be correct to follow the new URL, but it is not computed correctly.
                    # Might be enabled once CMK-9669 is fixed.
                    # redirect_url = response.headers["Location"]
                    pass
                else:
                    raise UnexpectedResponse.from_response(response)
            return True

    def create_user(
        self, username: str, fullname: str, password: str, email: str, contactgroups: List[str]
    ) -> None:
        response = self.post(
            "domain-types/user_config/collections/all",
            json={
                "username": username,
                "fullname": fullname,
                "auth_option": {
                    "auth_type": "password",
                    "password": password,
                },
                "contact_options": {
                    "email": email,
                },
                "contactgroups": contactgroups,
            },
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def get_all_users(self) -> List[User]:
        response = self.get("domain-types/user_config/collections/all")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)
        return [User(title=user_dict["title"]) for user_dict in response.json()["value"]]

    def delete_user(self, username: str) -> None:
        response = self.delete(f"/objects/user_config/{username}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def create_host(
        self,
        hostname: str,
        folder: str = "/",
        attributes: Optional[dict[str, Any]] = None,
        bake_agent: bool = False,
    ) -> None:
        query_string = "?bake_agent=1" if bake_agent else ""
        response = self.post(
            f"/domain-types/host_config/collections/all{query_string}",
            json={"folder": folder, "host_name": hostname, "attributes": attributes or {}},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def delete_host(self, hostname: str) -> None:
        response = self.delete(f"/objects/host_config/{hostname}")
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)

    def discover_services(self, hostname: str) -> None:
        response = self.post(
            f"/objects/host/{hostname}/actions/discover_services/invoke",
            json={"mode": "new"},
        )
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

    def get_baking_status(self) -> BakingStatus:
        response = self.get("/domain-types/agent/actions/baking_status/invoke")
        if response.status_code != 200:
            raise UnexpectedResponse.from_response(response)

        result = response.json()["result"]["value"]
        return BakingStatus(
            state=result["state"],
            started=result["started"],
        )

    def sign_agents(self, key_id: int, passphrase: str) -> None:
        response = self.post(
            "/domain-types/agent/actions/sign/invoke",
            json={"key_id": key_id, "passphrase": passphrase},
        )
        if response.status_code != 204:
            raise UnexpectedResponse.from_response(response)
