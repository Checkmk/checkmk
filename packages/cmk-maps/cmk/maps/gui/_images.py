#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""GUI-owned image library and map backgrounds (upload / list / delete / usage).

The daemon owns only live state now, so image and map-background management —
plain file I/O plus validation — is a GUI concern. Files are written under
``var/maps/{images,backgrounds}`` and served statically by Apache (the
daemon no longer proxies or gates them). Built-in icons ship with this package
(``builtin_icons/``) and are seeded into the served images dir on page load.

Usage scans run over the maps the caller may see (the pagetype store), so unlike
the old daemon endpoint they never disclose maps outside the caller's scope.
"""

import hashlib
import re
import secrets
from collections.abc import Container, Iterable, Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import cmk.utils.paths
from cmk.ccc import store
from cmk.ccc.user import UserId
from cmk.gui.config import Config
from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.maps.gui._image_security import (
    BACKGROUND_MIME_TYPES,
    BACKGROUND_SUFFIXES,
    ICON_MIME_TYPES,
    ICON_SUFFIXES,
    is_valid_image,
    is_valid_image_name,
    safe_image_stem,
)
from cmk.maps.gui.pagetype import MapPage
from cmk.maps.gui.store import all_maps, get_permitted_map, get_permitted_maps, user_maps_path
from cmk.maps.shared.validators import is_valid_map_name

MAX_ICON_BYTES = 2 * 1024 * 1024
MAX_BACKGROUND_BYTES = 10 * 1024 * 1024
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


@dataclass(frozen=True, kw_only=True)
class ImageUsage:
    """The maps the caller sees that reference an image, and how many others do."""

    maps: list[ImageUsageEntry]
    hidden_maps: int

    @property
    def in_use(self) -> bool:
        return bool(self.maps or self.hidden_maps)


# ---------------------------------------------------------------------------
# Storage locations (served statically by Apache; see skel/etc/apache/.../00_maps.conf)
# ---------------------------------------------------------------------------


def _images_dir() -> Path:
    d = cmk.utils.paths.omd_root / "var/maps/images"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _backgrounds_dir() -> Path:
    d = cmk.utils.paths.omd_root / "var/maps/backgrounds"
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


@lru_cache
def _shipped_bytes(name: str) -> bytes:
    return (_BUILTIN_DIR / name).read_bytes()


def _is_shipped(name: str, contents: bytes) -> bool:
    return _is_builtin(name) and _shipped_bytes(name) == contents


def _holds_builtin(path: Path) -> bool:
    """Whether the stored file is the shipped icon, not an upload that took its name
    before the icon shipped.

    A copy seeded from an icon a later release changed counts as no built-in
    either: deleting it seeds the current icon on the next page load. Its name
    stays reserved for uploads.
    """
    if not _is_builtin(path.name):
        return False
    stat = path.stat()
    return _stored_is_shipped(path, stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=1024)
def _stored_is_shipped(path: Path, _mtime: int, size: int) -> bool:
    return size == len(_shipped_bytes(path.name)) and _is_shipped(path.name, path.read_bytes())


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
# Usage scan
# ---------------------------------------------------------------------------


def _image_refs(payload: Mapping[str, object], name: str) -> tuple[list[str], bool]:
    """The ids of the objects and slide elements showing *name*, and whether the
    map or slide has it as its background."""
    object_ids: list[str] = []
    objects = payload.get("objects")
    for obj in objects if isinstance(objects, list) else ():
        if not isinstance(obj, dict):
            continue
        display = obj.get("display")
        image = display.get("image") if isinstance(display, dict) else None
        if (image or obj.get("image_src")) == name and isinstance(oid := obj.get("id"), str):
            object_ids.append(oid)
    view = payload.get("view")
    view = view if isinstance(view, dict) else {}
    elements = view.get("elements")
    for element in elements if isinstance(elements, list) else ():
        if (
            isinstance(element, dict)
            and element.get("kind") == "image"
            and element.get("src") == name
            and isinstance(eid := element.get("id"), str)
        ):
            object_ids.append(eid)
    is_background = name in (payload.get("background_image"), view.get("background_image"))
    return object_ids, is_background


def find_image_usage(name: str) -> ImageUsage:
    """Every map that shows *name*: those the caller sees, and how many others."""
    visible = {(page.owner(), page.name()) for page in get_permitted_maps()}
    usage: list[ImageUsageEntry] = []
    hidden_maps = 0
    for page in all_maps():
        object_ids, is_background = _image_refs(page.config.map_spec, name)
        if not (object_ids or is_background):
            continue
        if (page.owner(), page.name()) not in visible:
            hidden_maps += 1
            continue
        alias = page.config.map_spec.get("alias")
        usage.append(
            ImageUsageEntry(
                map_name=page.config.name,
                alias=str(alias) if isinstance(alias, str) else None,
                object_ids=object_ids,
                is_background=is_background,
            )
        )
    return ImageUsage(maps=usage, hidden_maps=hidden_maps)


# ---------------------------------------------------------------------------
# Image library
# ---------------------------------------------------------------------------


def require_valid_image_name(name: str) -> None:
    if not is_valid_image_name(name):
        raise MKUserError("name", _("Invalid filename."))


def image_list() -> list[ImageListEntry]:
    """The site's image library: built-in icons plus user uploads."""
    seed_builtin_images()
    return [
        ImageListEntry(name=f.name, url=f"images/{f.name}", builtin=_holds_builtin(f))
        for f in sorted(_images_dir().iterdir())
        if f.is_file() and f.suffix.lower() in ICON_SUFFIXES
    ]


def _accepted_suffix(
    filename: str,
    content_type: str,
    contents: bytes,
    *,
    mime_types: Container[str],
    suffixes: Container[str],
    max_bytes: int,
    too_large: str,
    allow_gif: bool = True,
) -> str:
    """Refuse an upload that is not a supported image, and name its suffix.

    ``content_type`` is only what the browser claimed; the magic-byte check is
    what actually decides, so a faked header buys nothing. An unsupported (or
    absent) suffix falls back to ``.png`` rather than being refused — the
    content has already been vouched for.
    """
    if content_type not in mime_types:
        raise MKUserError("content_type", _("Unsupported image type."))
    if len(contents) > max_bytes:
        raise MKUserError("content", too_large)
    if not is_valid_image(contents, allow_gif=allow_gif):
        raise MKUserError("content", _("File content does not match a supported image format."))
    suffix = Path(filename or "").suffix.lower()
    return suffix if suffix in suffixes else ".png"


def upload_image(filename: str, content_type: str, contents: bytes) -> ImageListEntry:
    """Store an icon in the site-wide image library (operator task)."""
    # GIF stays out of icons: no animated icons.
    suffix = _accepted_suffix(
        filename,
        content_type,
        contents,
        mime_types=ICON_MIME_TYPES,
        suffixes=ICON_SUFFIXES,
        max_bytes=MAX_ICON_BYTES,
        too_large=_("Image file too large (max 2 MB)."),
        allow_gif=False,
    )
    # Maps refer to an image by its name, so an upload never replaces one: a
    # different file under a taken name gets a free variant of it.
    name = import_icon(safe_image_stem(filename) + suffix, contents)
    return ImageListEntry(name=name, url=f"images/{name}", builtin=_is_builtin(name))


def import_icon(name: str, contents: bytes) -> str:
    """Add an already vetted icon to the image library; returns the name it has there.

    An icon identical to the built-in of its name, or to the file already under it, is
    reused. A different file is never replaced, and a built-in's name never taken,
    seeded yet or not: the icon gets a free variant of the name instead.
    """
    with adding_icons():
        stored = icon_name_for(name, contents)
        store_icon(stored, contents)
    return stored


@contextmanager
def adding_icons() -> Iterator[None]:
    """Held while icons are added, so no two of them get one name."""
    # Outside the served directory.
    with store.locked(cmk.utils.paths.omd_root / "var/maps/images.lock"):
        yield


class IconNameTakenError(Exception):
    """Another file got the name an icon was to be added under."""


def icon_name_for(name: str, contents: bytes, planned: Mapping[str, bytes] | None = None) -> str:
    """The name :func:`import_icon` gives the icon, without adding it yet.

    ``planned`` holds icons, by name, that are to be added and count as in the library.
    """
    if _is_shipped(name, contents):
        return name
    images_dir = _images_dir()
    stem, suffix = Path(name).stem, Path(name).suffix
    candidate, n = name, 1
    while True:
        if not _is_builtin(candidate):
            if (existing := (planned or {}).get(candidate)) is None:
                target = images_dir / candidate
                if not target.exists():
                    return candidate
                existing = target.read_bytes()
            if existing == contents:
                return candidate
        n += 1
        candidate = f"{stem}-{n}{suffix}"


def store_icon(name: str, contents: bytes) -> bool:
    """Add the icon under the name :func:`icon_name_for` gave it, unless it is there;
    returns whether it was added. To be called while :func:`adding_icons`."""
    if _is_builtin(name):
        return False
    target = _images_dir() / name
    try:
        existing = target.read_bytes()
    except FileNotFoundError:
        store.save_bytes_to_file(target, contents)
        return True
    if existing != contents:
        raise IconNameTakenError(name)
    return False


def delete_image(name: str, force: bool) -> ImageUsage | None:
    """Delete a user-uploaded image, unless it is still in use.

    Returns the blocking usage when the image is referenced and ``force`` was not
    set (None means the file is gone) — the SPA shows the in-use warning and asks
    again with ``force``.
    """
    require_valid_image_name(name)
    d = _images_dir().resolve()
    # Resolve strictly + compare via is_relative_to so a symlink pointing
    # outside the images dir is caught (str.startswith could be tricked).
    try:
        path = (d / name).resolve(strict=True)
    except OSError, RuntimeError:
        raise MKUserError("name", _("Image '%(name)s' not found.") % {"name": name}) from None
    if not path.is_relative_to(d):
        raise MKUserError("name", _("Invalid filename."))
    if _holds_builtin(path):
        raise MKUserError("name", _("Built-in images cannot be deleted."))
    if not force and (usage := find_image_usage(name)).in_use:
        return usage
    path.unlink()
    return None


# ---------------------------------------------------------------------------
# Map backgrounds
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

    ``name`` is pattern-checked in :func:`_editable_map`, which every
    background path resolves through (``[A-Za-z0-9_-]``, so it carries neither a
    ``.`` nor a glob metacharacter the ``{stem}.*`` glob could reach across). The
    served filename adds an unguessable token so the URL is a capability (see
    :func:`upload_background`)."""
    return f"{_owner_key(owner)}__{name}"


def _owner_key(owner: str) -> str:
    return hashlib.sha256(owner.encode("utf-8")).hexdigest()[:16]


_OWNER_KEY_OF_BACKGROUND = re.compile(r"([0-9a-f]{16})__")


def _backgrounds_without_owner(backgrounds: Iterable[str], owners: Iterable[str]) -> list[str]:
    """The background files of maps whose owner is none of ``owners``."""
    kept = {_owner_key(owner) for owner in owners}
    return [
        name
        for name in backgrounds
        if (match := _OWNER_KEY_OF_BACKGROUND.match(name)) and match.group(1) not in kept
    ]


def remove_backgrounds_of_removed_users(profile_dir: Path, backgrounds_dir: Path) -> None:
    """Remove the background files of the maps of users whose profile is gone.

    Checkmk keeps the profile of a deleted user, and the maps in it, until it
    removes the profile 30 days later (``cmk.gui.userdb._user_profile_cleanup``),
    so the backgrounds of those maps stay as long."""
    try:
        # Listed before the owners: the profile of a user exists before any upload.
        backgrounds = [entry.name for entry in backgrounds_dir.iterdir()]
        owners = [entry.name for entry in profile_dir.iterdir() if entry.is_dir()]
    except FileNotFoundError:
        return
    if not owners:
        # As the profile cleanup: no profile at all is no reason to remove everything.
        return
    for name in _backgrounds_without_owner(backgrounds, owners):
        (backgrounds_dir / name).unlink(missing_ok=True)


def execute_background_cleanup_job(config: Config) -> None:  # noqa: ARG001
    remove_backgrounds_of_removed_users(cmk.utils.paths.profile_dir, _backgrounds_dir())


def _editable_map(name: str) -> MapPage:
    """Resolve the map the caller may edit, with its real owner, or raise.

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
    return page


def upload_background(map_name: str, filename: str, content_type: str, contents: bytes) -> str:
    """Store a map's background image; returns the stored filename to adopt.

    Only the image file is stored here — the map's ``background_image`` field is
    persisted by the GUI map save. The filename carries an unguessable token so
    the (Apache-served, static) URL is a capability rather than an enumerable
    ``{owner}__{name}`` path.

    The permission split against the image *library* is deliberate, not an
    oversight: the library is site-wide shared state, so writing it needs
    ``maps.configure`` (an admin task), while a background belongs to exactly one
    map, so ``maps.use`` plus that map's own edit right (``_editable_map``)
    is the matching authorization — the same right that lets the user change any
    other field of the map.

    There is deliberately no byte quota: the write is bounded per map (the saved
    background and one uploaded since, ``MAX_BACKGROUND_BYTES`` each), so total
    usage is bounded by how many maps the user may create — the same bound the
    pagetype store itself has.
    """
    page = _editable_map(map_name)
    suffix = _accepted_suffix(
        filename,
        content_type,
        contents,
        mime_types=BACKGROUND_MIME_TYPES,
        suffixes=BACKGROUND_SUFFIXES,
        max_bytes=MAX_BACKGROUND_BYTES,
        too_large=_("Background image must not exceed 10 MB."),
    )
    return store_background(
        str(page.config.owner),
        map_name,
        suffix,
        contents,
        saved=page.config.map_spec.get("background_image"),
    )


def store_background(
    owner: str, map_name: str, suffix: str, contents: bytes, *, saved: object
) -> str:
    """Store already vetted ``contents`` as the background of ``owner``'s map.

    Returns the filename the map's ``background_image`` refers to. ``map_name`` must
    be a valid map name (see :func:`_bg_stem`). The ``saved`` background stays
    until a save takes over the new one, so the map as saved keeps its file.
    """
    with store.locked(user_maps_path(UserId(owner))):
        stored = _write_background(owner, map_name, suffix, contents)
        prune_backgrounds(owner, map_name, stored, saved)
    return stored


def _write_background(owner: str, map_name: str, suffix: str, contents: bytes) -> str:
    stored = f"{_bg_stem(owner, map_name)}.{secrets.token_urlsafe(16)}{suffix}"
    with store.locked(user_maps_path(UserId(owner))):
        store.save_bytes_to_file(_backgrounds_dir() / stored, contents)
    return stored


def prune_backgrounds(owner: str, map_name: str, *keep: object) -> None:
    """Remove the background files of ``owner``'s map other than ``keep``."""
    with store.locked(user_maps_path(UserId(owner))):
        for f in _backgrounds_dir().glob(f"{_bg_stem(owner, map_name)}.*"):
            if f.name not in keep:
                f.unlink(missing_ok=True)


class ForeignBackground(Exception):
    """The background is neither of the map nor of a map the user sees."""


def adopt_background(owner: str, map_name: str, ref: str, previous: object) -> str | None:
    """The background ``ref`` as one of the files of ``owner``'s map.

    The stored background and the map's own files stay as they are. The background
    of another map the user sees, as a clone carries it, is copied for the map, so
    deleting either map keeps the other's; None if that map has lost the file. Any
    other file raises :class:`ForeignBackground`. The map's other files stay until
    :func:`prune_backgrounds` after the save."""
    own = _bg_stem(owner, map_name) + "."
    source = _backgrounds_dir() / ref
    if ref == previous:
        return ref
    if ref.startswith(own):
        if source.is_file():
            return ref
        # An editor may still hold the name the background had before a save
        # stored it anew (see :func:`rotate_background`).
        if isinstance(previous, str) and previous.startswith(own):
            return previous
        raise ForeignBackground
    for page in get_permitted_maps():
        if ref.startswith(_bg_stem(str(page.config.owner), page.config.name) + "."):
            try:
                contents = source.read_bytes()
            except FileNotFoundError:
                return None
            return _write_background(owner, map_name, source.suffix.lower(), contents)
    raise ForeignBackground


def rotate_background(owner: str, map_name: str, ref: str) -> str:
    """Store the background ``ref`` of ``owner``'s map anew under a new name, so its
    old URL stops working once :func:`prune_backgrounds` ran after the save; another
    map's file stays as it is."""
    if not ref.startswith(_bg_stem(owner, map_name) + "."):
        return ref
    source = _backgrounds_dir() / ref
    try:
        contents = source.read_bytes()
    except FileNotFoundError:
        return ref
    return _write_background(owner, map_name, source.suffix.lower(), contents)


def import_background(owner: str, map_name: str, ref: str, contents: bytes) -> str | None:
    """Store the image file ``ref`` as the background of ``owner``'s map, if it is one.

    For a migration, which brings its files without an upload: the same name and
    content checks, but no size limit. Returns what :func:`store_background` does,
    but keeps the map's other background files: the migration drops them once the
    map is stored, so a map it fails to replace keeps its background.
    """
    suffix = Path(ref).suffix.lower()
    if not (
        is_valid_image_name(ref) and suffix in BACKGROUND_SUFFIXES and is_valid_image(contents)
    ):
        return None
    return _write_background(owner, map_name, suffix, contents)


def delete_background(map_name: str) -> None:
    """Remove a map's background image files (the GUI clears the field on save)."""
    delete_background_files(str(_editable_map(map_name).config.owner), map_name)


def delete_background_files(owner: str, map_name: str, *, keep: str | None = None) -> None:
    """Remove every background file of ``owner``'s map but ``keep`` (owner already
    resolved).

    For callers that have already resolved the real owner (e.g. deleting a foreign
    map, where the caller may delete but not edit it, so ``_editable_map``
    would refuse). The name is still pattern-checked because it feeds the
    ``{stem}.*`` glob that must not reach across maps."""
    if is_valid_map_name(map_name):
        prune_backgrounds(owner, map_name, keep)
