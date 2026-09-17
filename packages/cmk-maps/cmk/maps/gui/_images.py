#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI-owned image library and map backgrounds (upload / list / delete / usage).

The daemon owns only live state now, so image and map-background management —
plain file I/O plus validation — is a GUI concern. Files are written under
``var/maps/{images,maps/backgrounds}`` and served statically by Apache (the
daemon no longer proxies or gates them). Built-in icons ship with this package
(``builtin_icons/``) and are seeded into the served images dir on page load.

Usage scans run over the maps the caller may see (the pagetype store), so unlike
the old daemon endpoint they never disclose maps outside the caller's scope.
"""

import hashlib
import secrets
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import override, TypedDict

import cmk.utils.paths
from cmk.ccc import store
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.pages import AjaxPage, PageContext, PageResult
from cmk.maps.gui._image_security import (
    BACKGROUND_MIME_TYPES,
    BACKGROUND_SUFFIXES,
    ICON_MIME_TYPES,
    ICON_SUFFIXES,
    is_valid_image,
    is_valid_image_name,
    safe_image_stem,
)
from cmk.maps.gui.store import get_permitted_map, get_permitted_maps, is_valid_map_name
from cmk.web.utils.csrf_token import check_csrf_token

_MAX_ICON_BYTES = 2 * 1024 * 1024  # 2 MB
_MAX_BACKGROUND_BYTES = 10 * 1024 * 1024  # 10 MB
_BUILTIN_DIR = Path(__file__).resolve().parent / "builtin_icons"


@dataclass(frozen=True, kw_only=True)
class ImageListEntry:
    name: str
    url: str
    builtin: bool


@dataclass(frozen=True, kw_only=True)
class ImageUsageEntry:
    """One map (the caller may see) referencing an image."""

    map_name: str
    alias: str | None
    object_ids: list[str]
    is_background: bool


# ---------------------------------------------------------------------------
# Storage locations (served statically by Apache; see skel/etc/apache/.../00_maps.conf)
# ---------------------------------------------------------------------------


def _images_dir() -> Path:
    d = cmk.utils.paths.omd_root / "var/maps/images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _backgrounds_dir() -> Path:
    d = cmk.utils.paths.omd_root / "var/maps/maps/backgrounds"
    d.mkdir(parents=True, exist_ok=True)
    return d


@lru_cache
def _builtin_names() -> set[str]:
    # The built-in icons ship with the package and never change at runtime.
    if not _BUILTIN_DIR.is_dir():
        return set()
    return {
        p.name for p in _BUILTIN_DIR.iterdir() if p.is_file() and p.suffix.lower() in ICON_SUFFIXES
    }


def _is_builtin(name: str) -> bool:
    return name in _builtin_names()


def seed_builtin_images() -> None:
    """Copy missing built-in icons into the served images dir (non-destructive).

    Called on Maps page load so the icons are present before any map renders,
    without needing a daemon-style startup hook. User customisations/deletions
    are preserved (existing files are never overwritten).

    Writes go through ``store.save_bytes_to_file`` (atomic rename), so two
    concurrent page loads racing on the same missing icon cannot leave a
    half-written file behind — which is why this needs no cross-request guard.
    """
    if not _BUILTIN_DIR.is_dir():
        return
    dest = _images_dir()
    for name in _builtin_names():
        dst = dest / name
        if not dst.exists():
            store.save_bytes_to_file(dst, (_BUILTIN_DIR / name).read_bytes())


# ---------------------------------------------------------------------------
# Usage scan (over the maps the caller may see)
# ---------------------------------------------------------------------------


def find_image_usage(name: str) -> list[ImageUsageEntry]:
    """Maps the caller may see that reference *name* as object icon or background."""
    usage: list[ImageUsageEntry] = []
    for page in get_permitted_maps():
        payload = page.config.map_spec
        object_ids: list[str] = []
        objects = payload.get("objects")
        if isinstance(objects, list):
            for obj in objects:
                if not isinstance(obj, dict):
                    continue
                obj_image = obj.get("image_src")
                display = obj.get("display")
                if isinstance(display, dict) and display.get("image"):
                    obj_image = display.get("image")
                if obj_image == name:
                    oid = obj.get("id")
                    if isinstance(oid, str):
                        object_ids.append(oid)
        is_background = payload.get("background_image") == name
        if object_ids or is_background:
            alias = payload.get("alias")
            usage.append(
                ImageUsageEntry(
                    map_name=page.config.name,
                    alias=str(alias) if isinstance(alias, str) else None,
                    object_ids=object_ids,
                    is_background=is_background,
                )
            )
    return usage


# ---------------------------------------------------------------------------
# Image library
# ---------------------------------------------------------------------------


def require_valid_image_name(name: str) -> None:
    if not is_valid_image_name(name):
        raise MKUserError("name", _("Invalid filename."))


def image_list() -> list[ImageListEntry]:
    """The site's image library: built-in icons plus user uploads."""
    seed_builtin_images()
    builtins = _builtin_names()
    return [
        ImageListEntry(name=f.name, url=f"images/{f.name}", builtin=f.name in builtins)
        for f in sorted(_images_dir().iterdir())
        if f.is_file() and f.suffix.lower() in ICON_SUFFIXES
    ]


class AjaxMapsImageUpload(AjaxPage):
    """Upload an icon into the site-wide image library (operator task)."""

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.configure")
        check_csrf_token(ctx.session, ctx.request, i18n=_)
        filename, content_type, contents = ctx.request.uploaded_file("file")
        if content_type not in ICON_MIME_TYPES:
            raise MKUserError("file", _("Unsupported image type."))
        if len(contents) > _MAX_ICON_BYTES:
            raise MKUserError("file", _("Image file too large (max 2 MB)."))
        # GIF stays out of icons (no animated icons) even if the client fakes the
        # Content-Type — the magic-byte check enforces it too.
        if not is_valid_image(contents, allow_gif=False):
            raise MKUserError("file", _("File content does not match a supported image format."))

        raw_suffix = Path(filename or "").suffix.lower()
        suffix = raw_suffix if raw_suffix in ICON_SUFFIXES else ".png"
        stem = safe_image_stem(filename)
        target_name = stem + suffix
        if _is_builtin(target_name):
            # A built-in icon is referenced across maps; silently replacing it
            # would change every map at once (delete protects them too).
            raise MKUserError("file", _("Built-in images cannot be overwritten."))

        d = _images_dir()
        store.save_bytes_to_file(d / target_name, contents)
        return {"name": target_name, "url": f"images/{target_name}", "builtin": False}


class _ImageUsage(TypedDict):
    """One map that references an image, mirroring ``MapsImageUsage``."""

    map: str
    alias: str | None
    object_ids: list[str]
    is_background: bool


def _usage_payload(usage: list[ImageUsageEntry]) -> list[_ImageUsage]:
    """The usage list in the wire shape, matching the internal REST endpoint's."""
    return [
        {
            "map": entry.map_name,
            "alias": entry.alias,
            "object_ids": entry.object_ids,
            "is_background": entry.is_background,
        }
        for entry in usage
    ]


class AjaxMapsImageDelete(AjaxPage):
    """Delete a user-uploaded image.

    Returns the blocking ``usage`` list when the image is still referenced and
    ``force`` was not set (empty list means the file was deleted) — the SPA shows
    the in-use warning and re-sends with ``force`` on confirmation.
    """

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.configure")
        check_csrf_token(ctx.session, ctx.request, i18n=_)
        name = ctx.request.get_ascii_input_mandatory("name")
        force = ctx.request.get_ascii_input("force") == "true"
        require_valid_image_name(name)
        if _is_builtin(name):
            raise MKUserError("name", _("Built-in images cannot be deleted."))
        d = _images_dir().resolve()
        # Resolve strictly + compare via is_relative_to so a symlink pointing
        # outside the images dir is caught (str.startswith could be tricked).
        try:
            path = (d / name).resolve(strict=True)
        except OSError, RuntimeError:
            raise MKUserError("name", _("Image '%(name)s' not found.") % {"name": name}) from None
        if not path.is_relative_to(d):
            raise MKUserError("name", _("Invalid filename."))
        if not force:
            usage = find_image_usage(name)
            if usage:
                return {"usage": _usage_payload(usage)}
        path.unlink()
        return {"usage": []}


# ---------------------------------------------------------------------------
# Map background endpoints
# ---------------------------------------------------------------------------


def _bg_stem(owner: str, name: str) -> str:
    """Owner-scoped, filesystem-safe prefix grouping a map's background files.

    Two users' same-named maps never share/overwrite one another, and the
    upload/delete paths can find every format variant for one map (``{stem}.*``).

    The owner is *hashed* rather than sanitised: both are safe as a path, but a
    sanitising substitution is not injective, so ``a.b``/``a_b`` — and, since map
    names may contain ``_`` too, ``a`` + ``b__c`` vs ``a__b`` + ``c`` — would
    share one stem. The upload below unlinks every ``{stem}.*`` sibling, so a
    shared stem means one map's upload deletes another map's background and
    leaves it with a dangling ``background_image``. A fixed-length hex prefix
    cannot collide with a different (owner, map) pair.

    ``name`` is pattern-checked in :func:`_editable_map_owner`, which every
    background path resolves through (``[A-Za-z0-9_-]``, so it carries neither a
    ``.`` nor a glob metacharacter the ``{stem}.*`` glob could reach across). The
    served filename adds an unguessable token so the URL is a capability (see
    :class:`AjaxMapsBackgroundUpload`)."""
    owner_key = hashlib.sha256(owner.encode("utf-8")).hexdigest()[:16]
    return f"{owner_key}__{name}"


def _editable_map_owner(name: str) -> str:
    """Resolve the real owner of a map the caller may edit, or raise.

    Mirrors the pagetype permission model: the map's true owner (never a client
    value) so an "edit foreign maps" user can change a foreign map's background,
    and the file is keyed by that owner like everywhere else.

    The name is checked against the map-name pattern here rather than taken on
    trust: it becomes part of the background filename stem, and the upload and
    delete paths glob ``{stem}.*``, so a name carrying a glob metacharacter would
    let one map reach another map's background files. The REST create path
    validates names too, but the invariant :func:`_bg_stem` relies on belongs on
    the resolve every background path goes through."""
    if not is_valid_map_name(name):
        raise MKUserError("name", _("Invalid map name: %(name)s") % {"name": name})
    page = get_permitted_map(name)
    if page is None:
        raise MKUserError("name", _("Unknown map: %(name)s") % {"name": name})
    if not page.may_edit():
        raise MKUserError("name", _("You are not allowed to edit this map."))
    if page.config.map_spec.get("readonly"):
        raise MKUserError("name", _("This map is read-only."))
    return str(page.config.owner)


class AjaxMapsBackgroundUpload(AjaxPage):
    """Store a map's background image; returns the stored filename to adopt.

    Only the image file is stored here — the map's ``background_image`` field is
    persisted by the GUI map save. The filename carries an unguessable token so
    the (Apache-served, static) URL is a capability rather than an enumerable
    ``{owner}__{name}`` path.

    The permission split against the image *library* endpoints is deliberate, not
    an oversight: the library is site-wide shared state, so writing it needs
    ``maps.configure`` (an admin task), while a background belongs to exactly one
    map, so ``maps.use`` plus that map's own edit right (``_editable_map_owner``)
    is the matching authorization — the same right that lets the user change any
    other field of the map.

    There is deliberately no byte quota: the write is bounded per map (one
    background, ``_MAX_BACKGROUND_BYTES``, older variants unlinked), so total
    usage is bounded by how many maps the user may create — the same bound the
    pagetype store itself has.
    """

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.use")
        check_csrf_token(ctx.session, ctx.request, i18n=_)
        name = ctx.request.get_ascii_input_mandatory("name")
        owner = _editable_map_owner(name)
        filename, content_type, contents = ctx.request.uploaded_file("file")
        if content_type not in BACKGROUND_MIME_TYPES:
            raise MKUserError("file", _("Unsupported image type."))
        if len(contents) > _MAX_BACKGROUND_BYTES:
            raise MKUserError("file", _("Background image must not exceed 10 MB."))
        if not is_valid_image(contents):
            raise MKUserError("file", _("File content does not match a supported image format."))

        raw_suffix = Path(filename or "").suffix.lower()
        suffix = raw_suffix if raw_suffix in BACKGROUND_SUFFIXES else ".png"
        bg_dir = _backgrounds_dir()
        stem = _bg_stem(owner, name)
        stored = f"{stem}.{secrets.token_urlsafe(16)}{suffix}"
        dest = bg_dir / stored

        store.save_bytes_to_file(dest, contents)
        # Map config holds only one filename; drop other-format siblings.
        for stale in bg_dir.glob(f"{stem}.*"):
            if stale.resolve() != dest.resolve():
                stale.unlink(missing_ok=True)
        return {"filename": stored}


class AjaxMapsBackgroundDelete(AjaxPage):
    """Remove a map's background image files (the GUI clears the field on save)."""

    @override
    def page(self, ctx: PageContext) -> PageResult:
        user.need_permission("maps.use")
        check_csrf_token(ctx.session, ctx.request, i18n=_)
        name = ctx.request.get_ascii_input_mandatory("name")
        owner = _editable_map_owner(name)
        bg_dir = _backgrounds_dir()
        for f in bg_dir.glob(f"{_bg_stem(owner, name)}.*"):
            f.unlink(missing_ok=True)
        return {}
