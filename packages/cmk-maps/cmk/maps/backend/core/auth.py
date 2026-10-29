#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Authenticates a request to the Maps daemon by the GUI session it carries.

The daemon runs behind the site Apache and handles no users, sessions or
passwords of its own. The browser sends the GUI session cookie with every
request. The daemon asks the GUI of its site who is behind it and which of the
permissions Maps needs they hold (``gui_session/identify``), which map a name
means for that user (``maps_access/resolve``), and which maps the names of map
links mean (``maps_link_targets/resolve``). It keeps the first answer per session
and the others per user for :data:`~cmk.fastapi.gui_session.IDENTITY_TTL` seconds.

The map config a viewer relays is signed by the GUI and verified here against
the owner the GUI named, see :mod:`cmk.maps.shared.map_signature`.
"""

import dataclasses
import functools
import hmac
import logging
from collections.abc import Sequence
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from typing import Final

from pydantic import BaseModel, ConfigDict, ValidationError

from cmk.fastapi.gui_session import (
    GuiLoopback,
    Identity,
    IDENTITY_TTL,
    IdentityCache,
    Rejected,
    Unavailable,
    unavailable,
)
from cmk.maps.backend.schemas.map import MapConfig
from cmk.maps.shared.map_links import CACHED_MAP_REFS_MAX
from cmk.maps.shared.map_signature import HmacFn, InvalidSignature, verify_config
from cmk.maps.shared.validators import is_valid_map_name
from cmk.utils import paths

__all__ = [
    "Forbidden",
    "GuiAuth",
    "InvalidSignature",
    "NoMap",
    "Principal",
    "verify_map_config",
]

_USE_PERMISSION: Final = "maps.use"
_EDIT_PERMISSION: Final = "general.edit_map"
_CONFIGURE_PERMISSION: Final = "maps.configure"
_SEE_ALL_PERMISSION: Final = "general.see_all"
_SEE_ALL_FOLDERS_PERMISSION: Final = "wato.see_all_folders"
_PERMISSIONS: Final = (
    _USE_PERMISSION,
    _EDIT_PERMISSION,
    _CONFIGURE_PERMISSION,
    _SEE_ALL_PERMISSION,
    _SEE_ALL_FOLDERS_PERMISSION,
)

_ACCESS_PATH: Final = "domain-types/maps_access/actions/resolve/invoke"
_LINK_TARGETS_PATH: Final = "domain-types/maps_link_targets/actions/resolve/invoke"
_LINK_RETRY_AFTER: Final = 10.0

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Principal:
    """The Checkmk user behind a request, with what the daemon needs to know of them.

    Per-map view/edit authorization is NOT done by the daemon. The GUI holds the
    pagetype + RBAC context and is the single authority: it names the map a user
    sees under a name (``map_owner``), and re-checks edit on save. Every
    Livestatus query the daemon runs is additionally bound to the user's
    contact-group scope (``auth_user``).
    """

    name: str
    # ``general.edit_map``: register unsigned editor previews, read the connection list.
    may_edit: bool = False
    # ``maps.configure``: read the full connection details.
    configure: bool = False
    # ``see_all`` bypasses Livestatus contact-group filtering (general.see_all / admin).
    see_all: bool = False
    # ``folder_see_all`` is the independent SETUP-folder read scope
    # (wato.see_all_folders); ``contact_groups`` scopes folder reads otherwise.
    folder_see_all: bool = False
    contact_groups: frozenset[str] = field(default_factory=frozenset)
    # The map the request is about, as the GUI resolved its name for this user, so
    # the daemon keys its shared broadcast loop by the map's true owner (not the
    # viewer). ``None`` for requests about no map in particular.
    map_owner: str | None = None
    map_name: str | None = None

    def viewing(self, owner: str, name: str) -> Principal:
        return dataclasses.replace(self, map_owner=owner, map_name=name)

    @property
    def auth_user(self) -> str | None:
        """Livestatus ``AuthUser`` scope, or ``None`` for see-all access."""
        return None if self.see_all else self.name

    @property
    def map_key_owner(self) -> str:
        """The map owner the daemon keys the shared broadcast loop / map cache
        by: the map's owner for a request about a map (so every viewer of a
        published map shares one loop), else the caller's own namespace.

        A built-in map's owner is the empty string (``UserId.builtin()``), which
        is a real owner — the GUI signs its config under ``""`` and keys the
        shared loop by it. Test ``map_owner is not None`` rather than truthiness
        so that empty owner survives."""
        return self.map_owner if self.map_owner is not None else self.name


@dataclass(frozen=True, slots=True)
class Forbidden:
    """The session is fine, but the user may not use Maps."""


@dataclass(frozen=True, slots=True)
class NoMap:
    """The user sees no map of that name."""


class _AccessAnswer(BaseModel):
    model_config = ConfigDict(strict=True)

    owner: str | None = None


class _LinkTarget(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str
    owner: str
    config_b64: str | None = None
    sig: str | None = None


class _LinkTargetsAnswer(BaseModel):
    model_config = ConfigDict(strict=True)

    targets: list[_LinkTarget]


@dataclass(frozen=True, slots=True)
class LinkTarget:
    """The map a link's name means. ``config`` is ``None`` for a map the daemon holds."""

    owner: str
    config: MapConfig | None = None


def _principal(identity: Identity) -> Principal:
    return Principal(
        name=identity.user_id,
        may_edit=identity.permissions[_EDIT_PERMISSION],
        configure=identity.permissions[_CONFIGURE_PERMISSION],
        see_all=identity.permissions[_SEE_ALL_PERMISSION],
        folder_see_all=identity.permissions[_SEE_ALL_FOLDERS_PERMISSION],
        contact_groups=frozenset(identity.contact_groups),
    )


class GuiAuth:
    """What the GUI of the site said about a session, kept for a limited time.

    A refused session and a user without Maps are asked about again, so they
    get in as soon as the GUI lets them.
    """

    def __init__(self, gui: GuiLoopback) -> None:
        self._gui = gui
        self._principals = IdentityCache[Principal](IDENTITY_TTL)
        self._owners = IdentityCache[str | NoMap](IDENTITY_TTL)
        self._link_owners = IdentityCache[str | NoMap](IDENTITY_TTL)
        # A GUI that gave no answer is not asked again on every state fetch.
        self._links_unanswered = IdentityCache[bool](_LINK_RETRY_AFTER)

    async def principal(
        self, session_cookie: str, *, now: float
    ) -> Principal | Rejected | Forbidden | Unavailable:
        if (principal := self._principals.get(session_cookie, now=now)) is not None:
            return principal
        match await self._gui.identify(
            session_cookie, required_permissions=_PERMISSIONS, include_contact_groups=True
        ):
            case Identity() as identity:
                if not identity.permissions[_USE_PERMISSION]:
                    return Forbidden()
                principal = _principal(identity)
                self._principals.put(session_cookie, principal, now=now)
                return principal
            case other:
                return other

    async def map_owner(
        self, user: Principal, name: str, *, now: float
    ) -> str | NoMap | Unavailable:
        """The owner of the map ``user`` sees under ``name``."""
        # The answer depends on the user, not the session, so all their sessions share it.
        # A map name holds no newline, so the key of one user and map cannot be another's.
        key = f"{user.name}\n{name}"
        if (owner := self._owners.get(key, now=now)) is not None:
            return owner
        resolved = await self._gui.post(
            "map access", _ACCESS_PATH, {"user_id": user.name, "name": name}, _AccessAnswer
        )
        if isinstance(resolved, Rejected):
            # The endpoint judges no session, so it has no reason to say this.
            return unavailable("map access", "status 400, error invalid_grant")
        if isinstance(resolved, Unavailable):
            return resolved
        owner = NoMap() if resolved.owner is None else resolved.owner
        self._owners.put(key, owner, now=now)
        return owner

    async def link_targets(
        self,
        as_user: str,
        names: Sequence[str],
        held: AbstractSet[tuple[str, str]],
        *,
        now: float,
    ) -> dict[str, LinkTarget]:
        """The maps ``as_user`` sees under the names of map links, the empty user
        seeing built-in maps only.

        ``held`` are the maps the daemon holds; any other comes with its config. A
        name without an answer of the GUI resolves to no map until the next fetch.
        """
        targets: dict[str, LinkTarget] = {}
        ask = []
        # A name no map can have would fail the question for all the others.
        for name in filter(is_valid_map_name, names):
            match self._link_owners.get(f"{as_user}\n{name}", now=now):
                case None:
                    ask.append(name)
                case NoMap():
                    pass
                case str() as owner if (owner, name) in held:
                    targets[name] = LinkTarget(owner)
                case _:
                    ask.append(name)
        if not ask or self._links_unanswered.get(as_user, now=now):
            return targets
        asked = set(ask)
        body: dict[str, object] = {
            "names": ask,
            "cached": [{"owner": o, "name": n} for o, n in held if n in asked][
                :CACHED_MAP_REFS_MAX
            ],
        }
        if as_user:
            body["user_id"] = as_user
        answer = await self._gui.post(
            "map link targets", _LINK_TARGETS_PATH, body, _LinkTargetsAnswer
        )
        if not isinstance(answer, _LinkTargetsAnswer):
            self._links_unanswered.put(as_user, True, now=now)
            return targets
        found = {t.name: t for t in answer.targets if t.name in asked}
        for name in ask:
            target = found.get(name)
            resolved = None if target is None else _usable_target(target, held)
            if resolved is None:
                self._link_owners.put(f"{as_user}\n{name}", NoMap(), now=now)
            else:
                self._link_owners.put(f"{as_user}\n{name}", resolved.owner, now=now)
                targets[name] = resolved
        return targets


def _usable_target(target: _LinkTarget, held: AbstractSet[tuple[str, str]]) -> LinkTarget | None:
    if target.config_b64 is None or target.sig is None:
        return LinkTarget(target.owner) if (target.owner, target.name) in held else None
    try:
        cfg = MapConfig.model_validate(
            verify_map_config(target.config_b64, target.sig, owner=target.owner)
        )
    except (InvalidSignature, ValidationError) as exc:
        logger.debug(
            "A map link's target %(map)s cannot be used: %(error)s",
            {"map": target.name, "error": exc},
        )
        return None
    return LinkTarget(target.owner, cfg) if cfg.name == target.name else None


# ``LocalSecret.regenerate`` always writes 32 bytes; anything else is a rewrite in progress.
_SITE_SECRET_SIZE = 32


@functools.lru_cache(maxsize=1)
def _site_hmac_for_file(_key: tuple[int, int, int]) -> HmacFn:
    # Read-only on purpose: ``SiteInternalSecret()`` writes its own secret into an
    # empty file, racing omd's rewrite.
    try:
        value = paths.site_internal_secret_file.read_bytes()
    except OSError as exc:
        raise InvalidSignature("site-internal secret is not readable") from exc
    if len(value) != _SITE_SECRET_SIZE:
        raise InvalidSignature("site-internal secret is being rotated")
    # Same HMAC-SHA256 as ``cmk.crypto.secrets.Secret.hmac``, which the GUI signs with.
    return functools.partial(hmac.digest, value, digest="sha256")


def _site_hmac() -> HmacFn:
    """HMAC with the site-internal secret, cached until the file changes.

    Keyed on inode, mtime and size: omd truncates and rewrites the file in place,
    usually within one coarse mtime tick.
    """
    try:
        st = paths.site_internal_secret_file.stat()
    except OSError as exc:
        raise InvalidSignature("site-internal secret is not readable") from exc
    return _site_hmac_for_file((st.st_ino, st.st_mtime_ns, st.st_size))


def verify_map_config(config_b64: str, sig: str, *, owner: str) -> dict[str, object]:
    """Verify a GUI-signed map config and return the parsed JSON object.

    ``owner`` is the owner the GUI named for the map, so a viewer can't
    substitute a tampered config, nor relay a config signed for a foreign owner,
    for a shared broadcast loop. Raises :class:`InvalidSignature` on any decode,
    signature or JSON problem.
    """
    return verify_config(config_b64, sig, _site_hmac(), owner=owner)
