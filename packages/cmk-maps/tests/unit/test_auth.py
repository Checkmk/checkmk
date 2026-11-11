#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""What the daemon makes of what the GUI says about a session.

The GUI is simulated at the HTTP boundary, so the requests the daemon sends are
pinned as well as what it makes of the answers.
"""

import asyncio
import json
from collections.abc import Callable, Mapping
from http import HTTPStatus
from pathlib import Path

import httpx2
import pytest

from cmk.crypto.secrets import Secret
from cmk.fastapi.gui_session import GuiLoopback, IDENTITY_TTL, Rejected, Unavailable
from cmk.maps.backend.core.auth import Forbidden, GuiAuth, LinkTarget, NoMap, Principal
from cmk.maps.backend.schemas.map import MapConfig
from cmk.maps.shared.map_links import CACHED_MAP_REFS_MAX
from cmk.maps.shared.map_signature import sign_config, signed_config_size

_COOKIE = "jdoe:4f1c2b1e-0d7a-4a3b-9a55-8d9d7c3a2b10:9c1e0000"
_IDENTIFY = "/domain-types/gui_session/actions/identify/invoke"
_MONITORED_SITES = "/domain-types/maps_monitored_sites/actions/show/invoke"
_ACCESS = "/domain-types/maps_access/actions/resolve/invoke"
_LINK_TARGETS = "/domain-types/maps_link_targets/actions/resolve/invoke"
_SECRET = Secret(b"0123456789abcdef0123456789abcdef")

_ALL_PERMISSIONS = {
    "maps.use": True,
    "general.edit_map": True,
    "general.edit_foreign_map": False,
    "maps.configure": False,
    "general.see_all": False,
    "wato.see_all_folders": True,
}


class _GUI:
    def __init__(
        self,
        answers: dict[str, httpx2.Response],
        before_answer: Callable[[], None] = lambda: None,
    ) -> None:
        self.answers = answers
        self.requests: list[tuple[str, object]] = []
        self._before_answer = before_answer

    def handle(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append((request.url.path, json.loads(request.content)))
        self._before_answer()
        return self.answers[request.url.path]


def _identified(
    user_id: str = "jdoe", *, permissions: Mapping[str, bool] | None = None
) -> httpx2.Response:
    return httpx2.Response(
        HTTPStatus.OK,
        json={
            "user_id": user_id,
            "permissions": {**_ALL_PERMISSIONS, **(permissions or {})},
            "contact_groups": ["linux"],
        },
    )


def _monitoring(sites: list[str] | None) -> httpx2.Response:
    return httpx2.Response(HTTPStatus.OK, json={"monitored_sites": sites})


def _auth(gui: _GUI) -> GuiAuth:
    return GuiAuth(
        GuiLoopback(
            httpx2.AsyncClient(base_url="http://gui", transport=httpx2.MockTransport(gui.handle))
        )
    )


def test_the_user_comes_with_what_the_gui_says_about_them() -> None:
    gui = _GUI({_IDENTIFY: _identified(), _MONITORED_SITES: _monitoring(["central"])})

    principal = asyncio.run(_auth(gui).principal(_COOKIE, now=0.0))

    assert gui.requests == [
        (
            _IDENTIFY,
            {
                "session_cookie": _COOKIE,
                "required_permissions": list(_ALL_PERMISSIONS),
                "include_contact_groups": True,
            },
        ),
        (_MONITORED_SITES, {"user_id": "jdoe"}),
    ]
    assert principal == Principal(
        name="jdoe",
        may_edit=True,
        configure=False,
        see_all=False,
        folder_see_all=True,
        contact_groups=frozenset({"linux"}),
        monitored_sites=frozenset({"central"}),
    )


def test_a_user_without_monitored_sites_set_is_asked_all_sites_for() -> None:
    gui = _GUI({_IDENTIFY: _identified(), _MONITORED_SITES: _monitoring(None)})

    principal = asyncio.run(_auth(gui).principal(_COOKIE, now=0.0))

    assert isinstance(principal, Principal)
    assert principal.monitored_sites is None


@pytest.mark.parametrize(
    "answer",
    [
        pytest.param(httpx2.Response(HTTPStatus.OK, json={}), id="no sites named"),
        pytest.param(httpx2.Response(HTTPStatus.NOT_FOUND), id="user gone"),
    ],
)
def test_a_user_whose_monitored_sites_the_gui_does_not_name_is_not_let_in(
    answer: httpx2.Response,
) -> None:
    gui = _GUI({_IDENTIFY: _identified(), _MONITORED_SITES: answer})

    assert isinstance(asyncio.run(_auth(gui).principal(_COOKIE, now=0.0)), Unavailable)


def test_a_user_without_named_monitored_sites_is_asked_about_again() -> None:
    gui = _GUI({_IDENTIFY: _identified(), _MONITORED_SITES: httpx2.Response(HTTPStatus.NOT_FOUND)})
    auth = _auth(gui)

    async def _ask_twice() -> None:
        await auth.principal(_COOKIE, now=0.0)
        await auth.principal(_COOKIE, now=1.0)

    asyncio.run(_ask_twice())

    assert [path for path, _body in gui.requests] == [_IDENTIFY, _MONITORED_SITES] * 2


def test_a_user_without_maps_is_forbidden() -> None:
    gui = _GUI({_IDENTIFY: _identified(permissions={"maps.use": False})})

    assert asyncio.run(_auth(gui).principal(_COOKIE, now=0.0)) == Forbidden()
    assert [path for path, _body in gui.requests] == [_IDENTIFY]


def test_a_user_name_with_a_line_break_is_forbidden() -> None:
    gui = _GUI({_IDENTIFY: _identified("jdoe\n")})

    assert asyncio.run(_auth(gui).principal(_COOKIE, now=0.0)) == Forbidden()


def test_a_refused_session_is_rejected() -> None:
    refused = httpx2.Response(
        HTTPStatus.BAD_REQUEST,
        json={"title": "t", "status": 400, "detail": "d", "ext": {"error": "invalid_grant"}},
    )
    gui = _GUI({_IDENTIFY: refused})

    assert asyncio.run(_auth(gui).principal(_COOKIE, now=0.0)) == Rejected()


def test_the_user_is_kept_for_a_session_until_the_ttl_has_passed() -> None:
    gui = _GUI({_IDENTIFY: _identified(), _MONITORED_SITES: _monitoring(None)})
    auth = _auth(gui)

    async def _ask_at(*times: float) -> None:
        for now in times:
            await auth.principal(_COOKIE, now=now)

    asyncio.run(_ask_at(0.0, IDENTITY_TTL - 0.1, IDENTITY_TTL))

    assert [path for path, _body in gui.requests] == [_IDENTIFY, _MONITORED_SITES] * 2


def test_a_forbidden_user_is_asked_about_again() -> None:
    gui = _GUI({_IDENTIFY: _identified(permissions={"maps.use": False})})
    auth = _auth(gui)

    async def _ask_twice() -> None:
        await auth.principal(_COOKIE, now=0.0)
        await auth.principal(_COOKIE, now=1.0)

    asyncio.run(_ask_twice())

    assert len(gui.requests) == 2


def test_the_map_owner_is_what_the_gui_names_for_the_user() -> None:
    gui = _GUI({_ACCESS: httpx2.Response(HTTPStatus.OK, json={"owner": "alice"})})

    owner = asyncio.run(_auth(gui).map_owner(Principal(name="jdoe"), "dc1", now=0.0))

    assert gui.requests == [(_ACCESS, {"user_id": "jdoe", "name": "dc1"})]
    assert owner == "alice"


def test_a_built_in_map_has_the_empty_owner() -> None:
    gui = _GUI({_ACCESS: httpx2.Response(HTTPStatus.OK, json={"owner": ""})})

    owner = asyncio.run(_auth(gui).map_owner(Principal(name="jdoe"), "dc1", now=0.0))

    assert owner == ""


def test_a_viewer_of_a_built_in_map_shares_the_loop_of_the_empty_owner() -> None:
    # The empty owner is a real one: the shared loop is keyed by it, not by the viewer.
    assert Principal(name="jdoe").viewing("", "dc1").map_key_owner == ""


def test_a_map_the_user_does_not_see_has_no_owner() -> None:
    gui = _GUI({_ACCESS: httpx2.Response(HTTPStatus.OK, json={})})

    owner = asyncio.run(_auth(gui).map_owner(Principal(name="jdoe"), "dc1", now=0.0))

    assert owner == NoMap()


def test_the_map_owner_is_kept_per_user_and_map() -> None:
    gui = _GUI({_ACCESS: httpx2.Response(HTTPStatus.OK, json={"owner": "alice"})})
    auth = _auth(gui)

    async def _ask() -> None:
        await auth.map_owner(Principal(name="jdoe"), "dc1", now=0.0)
        await auth.map_owner(Principal(name="jdoe"), "dc1", now=1.0)
        await auth.map_owner(Principal(name="jdoe"), "dc2", now=1.0)
        await auth.map_owner(Principal(name="hdoe"), "dc1", now=1.0)

    asyncio.run(_ask())

    assert [body for _path, body in gui.requests] == [
        {"user_id": "jdoe", "name": "dc1"},
        {"user_id": "jdoe", "name": "dc2"},
        {"user_id": "hdoe", "name": "dc1"},
    ]


def test_a_withdrawn_map_has_its_owner_asked_about_again() -> None:
    gui = _GUI({_ACCESS: httpx2.Response(HTTPStatus.OK, json={"owner": "alice"})})
    auth = _auth(gui)

    async def _ask_around_a_withdrawal() -> None:
        await auth.map_owner(Principal(name="jdoe"), "dc1", now=0.0)
        await auth.map_owner(Principal(name="jdoe"), "dc2", now=0.0)
        auth.forget_owners("dc1")
        await auth.map_owner(Principal(name="jdoe"), "dc1", now=1.0)
        await auth.map_owner(Principal(name="jdoe"), "dc2", now=1.0)

    asyncio.run(_ask_around_a_withdrawal())

    assert [body for _path, body in gui.requests] == [
        {"user_id": "jdoe", "name": name} for name in ("dc1", "dc2", "dc1")
    ]


def test_a_map_withdrawn_again_after_the_first_withdrawal_expired_is_asked_about_again() -> None:
    gui = _GUI({_ACCESS: httpx2.Response(HTTPStatus.OK, json={"owner": "alice"})})
    clock = [0.0]
    auth = GuiAuth(
        GuiLoopback(
            httpx2.AsyncClient(base_url="http://gui", transport=httpx2.MockTransport(gui.handle))
        ),
        clock=lambda: clock[0],
    )
    just_before_expiry = IDENTITY_TTL - 1.0
    just_after_expiry = IDENTITY_TTL + 1.0

    async def _ask_around_two_withdrawals() -> None:
        auth.forget_owners("dc1")
        clock[0] = just_before_expiry
        await auth.map_owner(Principal(name="jdoe"), "dc1", now=just_before_expiry)
        clock[0] = just_after_expiry
        auth.forget_owners("dc1")
        await auth.map_owner(Principal(name="jdoe"), "dc1", now=just_after_expiry)

    asyncio.run(_ask_around_two_withdrawals())

    assert len(gui.requests) == 2


def test_a_withdrawn_map_is_asked_about_again_after_many_other_withdrawals() -> None:
    gui = _GUI({_ACCESS: httpx2.Response(HTTPStatus.OK, json={"owner": "alice"})})
    auth = _auth(gui)

    async def _ask_around_a_flood_of_withdrawals() -> None:
        await auth.map_owner(Principal(name="jdoe"), "dc1", now=0.0)
        auth.forget_owners("dc1")
        for i in range(10_000):
            auth.forget_owners(f"other{i}")
        await auth.map_owner(Principal(name="jdoe"), "dc1", now=1.0)

    asyncio.run(_ask_around_a_flood_of_withdrawals())

    assert len(gui.requests) == 2


def test_an_odd_map_answer_is_no_verdict() -> None:
    gui = _GUI({_ACCESS: httpx2.Response(HTTPStatus.OK, json={"owner": 1})})

    owner = asyncio.run(_auth(gui).map_owner(Principal(name="jdoe"), "dc1", now=0.0))

    assert isinstance(owner, Unavailable)


@pytest.fixture
def _site_secret(site_secret_file: Path) -> None:
    site_secret_file.write_bytes(_SECRET.reveal())


def _targets(*targets: dict[str, str]) -> httpx2.Response:
    return httpx2.Response(HTTPStatus.OK, json={"targets": list(targets)})


def _signed_target(owner: str, name: str) -> dict[str, str]:
    signed = sign_config({"name": name}, _SECRET.hmac, owner=owner)
    return {"name": name, "owner": owner, **signed}


def _target_of(signed: dict[str, str]) -> LinkTarget:
    return LinkTarget(
        signed["owner"], MapConfig(name=signed["name"]), signed_config_size(signed["config_b64"])
    )


@pytest.mark.usefixtures("_site_secret")
def test_a_link_target_comes_with_the_config_the_gui_signed() -> None:
    signed = _signed_target("carol", "net")
    gui = _GUI({_LINK_TARGETS: _targets(signed)})

    targets = asyncio.run(_auth(gui).link_targets("jdoe", ["net", "gone"], set(), now=0.0))

    assert gui.requests == [
        (_LINK_TARGETS, {"names": ["net", "gone"], "cached": [], "user_id": "jdoe"})
    ]
    assert targets == {"net": _target_of(signed)}


@pytest.mark.usefixtures("_site_secret")
def test_a_link_target_signed_for_another_owner_is_left_out() -> None:
    forged = {**_signed_target("carol", "net"), "owner": "jdoe"}
    gui = _GUI({_LINK_TARGETS: _targets(forged)})

    assert asyncio.run(_auth(gui).link_targets("jdoe", ["net"], set(), now=0.0)) == {}


def test_a_link_target_is_asked_about_again_once_the_secret_is_readable(
    site_secret_file: Path,
) -> None:
    signed = _signed_target("carol", "net")
    gui = _GUI({_LINK_TARGETS: _targets(signed)})
    auth = _auth(gui)
    # omd has truncated the file and not yet written the secret.
    assert asyncio.run(auth.link_targets("jdoe", ["net"], set(), now=0.0)) == {}

    site_secret_file.write_bytes(_SECRET.reveal())

    assert asyncio.run(auth.link_targets("jdoe", ["net"], set(), now=11.0)) == {
        "net": _target_of(signed)
    }


@pytest.mark.usefixtures("site_secret_file")
def test_a_held_link_target_needs_no_secret() -> None:
    gui = _GUI({_LINK_TARGETS: _targets({"name": "net", "owner": "carol"})})

    targets = asyncio.run(_auth(gui).link_targets("jdoe", ["net"], {("carol", "net")}, now=0.0))

    assert targets == {"net": LinkTarget("carol")}


def test_the_empty_user_asks_for_built_in_maps_only() -> None:
    gui = _GUI({_LINK_TARGETS: _targets({"name": "net", "owner": ""})})

    targets = asyncio.run(_auth(gui).link_targets("", ["net"], {("", "net")}, now=0.0))

    assert gui.requests == [
        (_LINK_TARGETS, {"names": ["net"], "cached": [{"owner": "", "name": "net"}]})
    ]
    assert targets == {"net": LinkTarget("")}


@pytest.mark.usefixtures("_site_secret")
def test_more_held_maps_than_the_gui_takes_are_left_out_of_the_question() -> None:
    held = {(f"user{i}", "net") for i in range(CACHED_MAP_REFS_MAX + 1)}
    signed = _signed_target("carol", "net")
    gui = _GUI({_LINK_TARGETS: _targets(signed)})

    targets = asyncio.run(_auth(gui).link_targets("jdoe", ["net"], held, now=0.0))

    [(_path, body)] = gui.requests
    assert isinstance(body, dict) and len(body["cached"]) == CACHED_MAP_REFS_MAX
    assert targets == {"net": _target_of(signed)}


def test_link_targets_are_kept_per_user_while_the_daemon_holds_them() -> None:
    gui = _GUI({_LINK_TARGETS: _targets({"name": "net", "owner": "carol"})})
    auth = _auth(gui)
    held = {("carol", "net")}

    async def _ask() -> None:
        await auth.link_targets("jdoe", ["net", "gone"], held, now=0.0)
        await auth.link_targets("jdoe", ["net", "gone"], held, now=1.0)
        await auth.link_targets("jdoe", ["net"], set(), now=1.0)
        await auth.link_targets("hdoe", ["net"], held, now=1.0)
        await auth.link_targets("jdoe", ["net"], held, now=1.0 + IDENTITY_TTL)

    asyncio.run(_ask())

    cached = [{"owner": "carol", "name": "net"}]
    assert [body for _path, body in gui.requests] == [
        {"names": ["net", "gone"], "cached": cached, "user_id": "jdoe"},
        {"names": ["net"], "cached": [], "user_id": "jdoe"},
        {"names": ["net"], "cached": cached, "user_id": "hdoe"},
        {"names": ["net"], "cached": cached, "user_id": "jdoe"},
    ]


def test_a_link_target_withdrawn_while_the_gui_is_asked_is_left_out() -> None:
    gui = _GUI(
        {_LINK_TARGETS: _targets({"name": "net", "owner": "carol"})},
        before_answer=lambda: auth.forget_owners("net"),
    )
    auth = _auth(gui)

    targets = asyncio.run(auth.link_targets("jdoe", ["net"], {("carol", "net")}, now=0.0))

    assert targets == {}


def test_a_link_target_withdrawn_while_the_gui_is_asked_is_asked_about_again() -> None:
    gui = _GUI(
        {_LINK_TARGETS: _targets({"name": "net", "owner": "carol"})},
        before_answer=lambda: auth.forget_owners("net"),
    )
    auth = _auth(gui)
    held = {("carol", "net")}

    async def _ask_twice() -> None:
        await auth.link_targets("jdoe", ["net"], held, now=0.0)
        await auth.link_targets("jdoe", ["net"], held, now=1.0)

    asyncio.run(_ask_twice())

    assert len(gui.requests) == 2


def test_link_targets_without_an_answer_resolve_to_no_map_for_a_while() -> None:
    gui = _GUI({_LINK_TARGETS: httpx2.Response(HTTPStatus.SERVICE_UNAVAILABLE)})
    auth = _auth(gui)

    async def _ask_at(*times: float) -> list[dict[str, LinkTarget]]:
        return [await auth.link_targets("jdoe", ["net"], set(), now=now) for now in times]

    assert asyncio.run(_ask_at(0.0, 1.0, 10.0)) == [{}, {}, {}]
    assert len(gui.requests) == 2


@pytest.mark.parametrize("name", ["Data Center", "net\n"])
def test_a_name_no_map_can_have_is_not_asked_about(name: str) -> None:
    gui = _GUI({_LINK_TARGETS: _targets()})

    asyncio.run(_auth(gui).link_targets("jdoe", [name, "net"], set(), now=0.0))

    assert [body for _path, body in gui.requests] == [
        {"names": ["net"], "cached": [], "user_id": "jdoe"}
    ]


@pytest.mark.parametrize(
    ("user", "owner", "expected"),
    [
        pytest.param(Principal(name="a", may_edit=True), "a", True, id="own map"),
        pytest.param(Principal(name="a"), "a", False, id="own map without edit"),
        pytest.param(Principal(name="a", may_edit=True), "b", False, id="foreign map"),
        pytest.param(Principal(name="a", may_edit_foreign=True), "b", True, id="foreign editor"),
        pytest.param(Principal(name="a", may_edit=True), "", True, id="built-in customized"),
        pytest.param(Principal(name="a"), "", False, id="built-in without edit"),
    ],
)
def test_who_may_preview_a_map_is_who_may_save_it(
    user: Principal, owner: str, expected: bool
) -> None:
    assert user.may_preview(owner) is expected
