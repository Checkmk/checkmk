#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Minimal SAML SP-initiated login client.

Drives the SP -> IdP -> SP login flow against the real Checkmk SAML endpoints
end-to-end, so the tests need no browser runtime.
"""

import logging
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlencode, urlparse

import requests

logger = logging.getLogger("identity-tests")


class _FormParser(HTMLParser):
    """Extract the first form's ``action`` and its hidden ``<input>`` values."""

    def __init__(self) -> None:
        super().__init__()
        self.action: str | None = None
        self.method: str | None = None
        self.fields: dict[str, str] = {}
        self._in_form = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_dict = {k: v or "" for k, v in attrs}
        if tag == "form" and self.action is None:
            self._in_form = True
            self.action = attr_dict.get("action")
            self.method = (attr_dict.get("method") or "get").lower()
        elif tag == "input" and self._in_form:
            name = attr_dict.get("name")
            if name:
                self.fields[name] = attr_dict.get("value", "")

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self._in_form = False


def _looks_like_idp_login_form(body: str) -> bool:
    """True iff the IdP rendered its password challenge (silent SSO omits it)."""
    return 'name="password"' in body


def _parse_form(html: str, response: requests.Response | None = None) -> _FormParser:
    parser = _FormParser()
    parser.feed(html)
    parser.close()
    if parser.action is None:
        ctx = ""
        if response is not None:
            literal_form_tags = html.lower().count("<form ")
            ctx = (
                f" (HTTP {response.status_code} from {response.url!r}, "
                f"content-type={response.headers.get('Content-Type')!r}, "
                f"body length={len(html)}, "
                f"literal '<form ' occurrences={literal_form_tags}, "
                f"body[:4000]={html[:4000]!r})"
            )
        raise RuntimeError(f"No <form> found in HTML response{ctx}")
    return parser


@dataclass(frozen=True)
class SamlLoginResult:
    """Outcome of a SAML SP-initiated login flow."""

    final_url: str
    final_status: int
    cookies: requests.cookies.RequestsCookieJar


class SamlLoginClient:
    """Walks an SP-initiated SAML SSO flow (submitting the self-posting forms requests can't)."""

    def __init__(
        self,
        site_url: str,
        connection_id: str,
        session: requests.Session | None = None,
    ) -> None:
        self._site_url = site_url.rstrip("/")
        self._connection_id = connection_id
        # A shared session lets several clients share one cookie jar (SSO across sites).
        self._session = session if session is not None else requests.Session()

    def login(self, username: str, password: str, target_url: str = "index.py") -> SamlLoginResult:
        """Full SP-initiated SAML login with explicit credentials at the IdP."""
        idp_response = self._send_authn_request(target_url)
        idp_response = self._submit_idp_credentials(idp_response, username, password)
        return self._deliver_assertion_to_sp(idp_response)

    def login_via_existing_idp_session(self, target_url: str = "index.py") -> SamlLoginResult:
        """SP-initiated login reusing an existing IdP session; raises if the IdP re-prompts for login."""
        idp_response = self._send_authn_request(target_url)
        if _looks_like_idp_login_form(idp_response.text):
            raise AssertionError(
                f"Expected silent SSO reuse against {self._site_url} but the IdP "
                f"served a login form (no valid IdP session in the shared jar). "
                f"URL: {idp_response.url!r}"
            )
        return self._deliver_assertion_to_sp(idp_response)

    def _send_authn_request(self, target_url: str) -> requests.Response:
        """Steps 1 & 2: ask the SP for an AuthnRequest, POST it to the IdP, return the IdP response."""
        relay_state = f"{self._connection_id},{target_url}"
        sso_request_url = f"{self._site_url}/saml_sso.py?{urlencode({'RelayState': relay_state})}"

        logger.info("SAML SSO step 1: GET %s", sso_request_url)
        sp_form_resp = self._session.get(sso_request_url, allow_redirects=True, timeout=30)
        self._raise_for_status_with_body(sp_form_resp, "Step 1 (GET saml_sso.py) failed")
        self._raise_if_saml_user_error(sp_form_resp.url, "saml_sso.py rejected the request")
        sp_form = _parse_form(sp_form_resp.text, sp_form_resp)
        if "SAMLRequest" not in sp_form.fields:
            raise RuntimeError(
                f"saml_sso.py did not return an AuthnRequest form — got "
                f"action={sp_form.action!r}, fields={sorted(sp_form.fields)} "
                f"at URL {sp_form_resp.url!r}"
            )
        assert sp_form.method == "post", f"Expected POST form to IdP, got method={sp_form.method!r}"

        # Step 2: POST the AuthnRequest. Don't assert response.ok — the IdP may serve the
        # login form with a 4xx; the subsequent form parse is the real correctness check.
        idp_resp = self._post_form_following_redirects(sp_form, sp_form_resp.url)
        if idp_resp.status_code >= 500:
            self._raise_for_status_with_body(idp_resp, "Step 2 (POST AuthnRequest to IdP) failed")
        return idp_resp

    def _submit_idp_credentials(
        self, idp_login_resp: requests.Response, username: str, password: str
    ) -> requests.Response:
        """Step 3: feed credentials into the IdP login form."""
        login_form = _parse_form(idp_login_resp.text, idp_login_resp)
        login_form.fields["username"] = username
        login_form.fields["password"] = password
        sso_resp = self._post_form_following_redirects(login_form, idp_login_resp.url)
        if sso_resp.status_code >= 500:
            self._raise_for_status_with_body(sso_resp, "Step 3 (POST credentials to IdP) failed")
        return sso_resp

    def _deliver_assertion_to_sp(self, idp_response: requests.Response) -> SamlLoginResult:
        """Step 4: forward the auto-posting ACS form back to Checkmk."""
        try:
            acs_form = _parse_form(idp_response.text, idp_response)
        except RuntimeError:
            raise RuntimeError(
                f"IdP did not return an ACS form — landed on {idp_response.url!r}. "
                f"Body excerpt: {idp_response.text[:600]!r}"
            ) from None
        if "SAMLResponse" not in acs_form.fields:
            raise RuntimeError(
                f"IdP form has no SAMLResponse field — login likely failed. "
                f"Form action: {acs_form.action!r}, fields: {sorted(acs_form.fields)}. "
                f"Body excerpt: {idp_response.text[:2000]!r}"
            )
        acs_resp = self._post_form(acs_form, idp_response.url, allow_redirects=True)
        self._raise_if_saml_user_error(acs_resp.url, "Checkmk SAML ACS rejected the assertion")

        return SamlLoginResult(
            final_url=acs_resp.url,
            final_status=acs_resp.status_code,
            cookies=self._session.cookies,
        )

    @staticmethod
    def _raise_for_status_with_body(response: requests.Response, context: str) -> None:
        """``raise_for_status`` that includes the response body in the message."""
        if response.ok:
            return
        raise RuntimeError(
            f"{context}: HTTP {response.status_code} for {response.url!r}. "
            f"Body excerpt: {response.text[:1500]!r}"
        )

    @staticmethod
    def _raise_if_saml_user_error(url: str, context: str) -> None:
        """Surface the ``_saml2_user_error`` Checkmk redirects to login.py with on failure."""
        if "_saml2_user_error" not in url:
            return
        qs = parse_qs(urlparse(url).query)
        err = qs.get("_saml2_user_error", ["<missing>"])[0]
        raise RuntimeError(f"{context}: {err!r} (URL {url})")

    def _post_form(
        self,
        form: _FormParser,
        base_url: str,
        allow_redirects: bool = True,
    ) -> requests.Response:
        action = self._absolute(form.action or "", base_url)
        logger.info("SAML SSO POST %s (fields=%s)", action, list(form.fields))
        return self._session.post(
            action, data=form.fields, allow_redirects=allow_redirects, timeout=30
        )

    def _post_form_following_redirects(
        self, form: _FormParser, base_url: str, max_redirects: int = 10
    ) -> requests.Response:
        """POST a form and walk redirects manually, clearing cookies' ``Secure`` flag between hops so they ride along over HTTP (requests won't otherwise send them)."""
        response = self._post_form(form, base_url, allow_redirects=False)
        for _ in range(max_redirects):
            if not response.is_redirect:
                return response
            for cookie in self._session.cookies:
                cookie.secure = False
            location = response.headers["Location"]
            next_url = self._absolute(location, response.url)
            response = self._session.get(next_url, allow_redirects=False, timeout=30)
        raise RuntimeError(f"Exceeded max_redirects={max_redirects} starting from {form.action!r}")

    @staticmethod
    def _absolute(action: str, base_url: str) -> str:
        if re.match(r"^https?://", action):
            return action
        parsed = urlparse(base_url)
        if action.startswith("/"):
            return f"{parsed.scheme}://{parsed.netloc}{action}"
        prefix = base_url.rsplit("/", 1)[0]
        return f"{prefix}/{action}"
