#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared validators for user-supplied URL/color fields on maps/presentations."""

import re
from collections.abc import Callable, Iterable
from ipaddress import ip_address
from posixpath import normpath
from typing import Annotated, Final
from urllib.parse import unquote, urlsplit

from pydantic import Field

from cmk.ccc.hostaddress import HostName
from cmk.maps.shared.map_name import MAP_NAME_MAX_LENGTH, MAP_NAME_PATTERN
from cmk.maps.shared.map_payload import GRID_ID_PATTERN, GRID_MAX_PER_MAP

# Connections are referenced by this id from maps and stored as a file name part.
CONNECTION_ID_PATTERN: Final = r"^[a-zA-Z0-9_\-]+$"
CONNECTION_ID_MAX_LENGTH: Final = 64
ConnectionId = Annotated[
    str, Field(max_length=CONNECTION_ID_MAX_LENGTH, pattern=CONNECTION_ID_PATTERN)
]

FiniteFloat = Annotated[float, Field(allow_inf_nan=False)]

# font-family reaches an inline style on the frontend; keep CSS-breaking
# characters (;{}()<>/:) out so it can't escape the property like the color
# fields are guarded against.
_FONT_RE = re.compile(r"^[a-zA-Z0-9 ,_'\"\-.]{1,128}$")

# Hex (#rgb/#rgba/#rrggbb/#rrggbbaa), a plain CSS named color, or "transparent".
# Strict on purpose — keeps `<script>`, `javascript:`, `expression(...)` and other
# CSS-injection payloads out of stroke/background/fill attributes rendered downstream.
_COLOR_RE = re.compile(r"^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{1,32}|transparent)$")

# CSS rgb()/rgba(), as legacy maps carry them (NagVis textboxes' inline HTML).
_RGB_RE = re.compile(
    r"rgba?\(\s*(\d{1,3})\s*,\s*(\d{1,3})\s*,\s*(\d{1,3})\s*(?:,\s*([0-9.]+)(%?)\s*)?\)"
)

# Allowlist instead of a scheme blocklist: browsers strip ASCII control
# characters when parsing URLs, so "java\tscript:alert(1)" bypasses any
# startswith("javascript:") check yet still executes on click. Rejecting
# control characters outright and allowlisting schemes closes that class.
# Beyond the web schemes, monitoring maps traditionally link remote-access
# handlers on host objects (NagVis heritage) — those are user-mediated OS
# handlers, not script-capable, so they stay allowed.
# Keep in sync with SAFE_URL_SCHEMES in frontend/src/utils/sanitize.ts.
_ALLOWED_URL_SCHEMES = frozenset(
    {"http", "https", "mailto", "tel", "ssh", "telnet", "rdp", "vnc", "ftp"}
)
_CONTROL_CHARS = re.compile(r"[\x00-\x1f\x7f]")
_URL_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):")

# These four are handed to a local OS handler that splits the URL into command
# arguments, so the authority needs more than a scheme check: a user or host
# starting with "-" arrives as an option (``ssh://-oProxyCommand=…@host`` runs a
# command), and whitespace or a percent escape hides one argument inside another.
_OS_HANDLER_SCHEMES = frozenset({"ssh", "telnet", "rdp", "vnc"})
_OS_HANDLER_URL = re.compile(
    r"(?://)?(?:[A-Za-z0-9_.~][A-Za-z0-9_.~-]*@)?"
    r"(?:[A-Za-z0-9_][A-Za-z0-9_.-]*|\[[0-9A-Fa-f:.]+\])(?::[0-9]{1,5})?"
    r"(?:[/?#][^\s%\\]*)?"
)


def _validate_os_handler_authority(rest: str) -> None:
    """Reject a remote access URL a handler could read as more than [user@]host[:port]."""
    if not _OS_HANDLER_URL.fullmatch(rest):
        raise ValueError("Remote access URL must start with [user@]host[:port]")


def validate_user_url(value: str | None) -> str | None:
    """Allow scheme-less (relative) URLs plus the allowlisted schemes."""
    if not value:
        return value
    if len(value) > 4096:
        raise ValueError("URL too long")
    s = value.strip()
    if _CONTROL_CHARS.search(s):
        raise ValueError("URL must not contain control characters")
    # Protocol-relative URLs (``//host/...``) inherit the page scheme and point
    # off-site.
    # A browser reads a backslash in a web URL as a slash.
    if s.replace("\\", "/").startswith("//"):
        raise ValueError("Protocol-relative URLs are not allowed")
    m = _URL_SCHEME.match(s)
    if m:
        scheme = m.group(1).lower()
        if scheme not in _ALLOWED_URL_SCHEMES:
            raise ValueError(f"URL scheme {m.group(1)!r} is not allowed")
        if scheme in _OS_HANDLER_SCHEMES:
            _validate_os_handler_authority(s[m.end() :])
    return s


def coerce_user_url(value: object) -> object:
    """Sanitize now-invalid URLs to ``None`` so legacy maps still load.

    Read-side companion to ``validate_user_url``, same contract as
    ``coerce_color``: stored JSON may pre-date the allowlist; dropping the
    offending URL keeps the map loadable while API saves stay strict.
    """
    return _coerced(validate_user_url, value)


def _coerced(validate: Callable[[str], str | None], value: object) -> object:
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None
    try:
        return validate(value)
    except ValueError:
        return None


# The browser loads these URLs with the viewer's session as soon as the map is
# shown, so they must not name a page of the site.
_IMAGE_FILE_URL = re.compile(r"[^?#\\]*\.(?:png|gif|jpe?g|svg|webp|bmp|ico)", re.IGNORECASE)
# Read-only pages a graph object may embed from the site itself.
_EMBEDDABLE_SITE_PAGES = frozenset({"graph_image.py", "view.py", "dashboard.py"})


def validate_host_name(value: str) -> str:
    """A host name as Checkmk takes it."""
    if not value:
        raise ValueError("A host name must not be empty")
    return str(HostName(value))


def normalize_host(hostname: str) -> str:
    """One spelling of a host: lowercase, no trailing dot, IP literals canonical."""
    host = hostname.strip().lower().rstrip(".")
    try:
        return str(ip_address(host))
    except ValueError:
        return host


def is_loopback_host(host: str) -> bool:
    """Whether a host spelled as :func:`normalize_host` gives it names this machine."""
    try:
        return host == "localhost" or ip_address(host).is_loopback
    except ValueError:
        return False


def credentialed_url_allowed(url: str, peer_host: str | None) -> bool:
    """Whether a connection's REST credentials may be sent to *url*.

    A path on this site always may. An absolute URL must name the connection's
    Livestatus host, or this machine for a connection without one."""
    url = url.strip()
    if url.startswith("/") and not url.startswith("//"):
        return True
    host = normalize_host(urlsplit(url).hostname or "")
    if peer_host is None:
        return is_loopback_host(host)
    return host == normalize_host(peer_host)


def _is_absolute_http(url: str) -> bool:
    parts = urlsplit(url)
    return parts.scheme.lower() in ("http", "https") and bool(parts.netloc)


def _is_map_background(url: str) -> bool:
    # A background belongs to its map and goes with it; resolved as the browser
    # (backslash as slash) and Apache do.
    path = urlsplit(url.replace("\\", "/")).path
    return "/check_mk/maps/backgrounds/" in normpath(unquote(path))


# Leaflet fills these per tile; any other placeholder it would fill from its options.
_TILE_PLACEHOLDER = re.compile(r"\{(?:s|z|x|y|-y|r)\}")


def validate_tile_url(value: str | None) -> str | None:
    """An absolute http(s) URL of a tile server, with the placeholders of a tile only."""
    url = validate_user_url(value)
    if not url:
        return url
    if not _is_absolute_http(url):
        raise ValueError("A tile server URL must be an absolute http or https URL")
    if set(_TILE_PLACEHOLDER.sub("", url)) & {"{", "}"}:
        raise ValueError(
            "A tile server URL may only hold the placeholders {s}, {z}, {x}, {y}, {-y} and {r}"
        )
    if "{" in urlsplit(url).netloc.replace("{s}", ""):
        raise ValueError("The host of a tile server URL may only hold the placeholder {s}")
    if _is_map_background(_TILE_PLACEHOLDER.sub("", url)):
        raise ValueError("A tile server URL must not point to the background of a map")
    return url


def validate_graph_url(value: str | None) -> str | None:
    """An absolute http(s) URL, or a graph, view or dashboard page of the site."""
    url = validate_user_url(value)
    if not url:
        return url
    if _is_map_background(url):
        raise ValueError("A graph URL must not point to the background of a map")
    if _is_absolute_http(url):
        return url
    parts = urlsplit(url)
    if parts.scheme or "\\" in url or parts.path.rsplit("/", 1)[-1] not in _EMBEDDABLE_SITE_PAGES:
        raise ValueError(
            "A graph URL must be an absolute http or https URL, or a graph, view or"
            " dashboard page of this site"
        )
    return url


def validate_image_url(value: str | None) -> str | None:
    """An image-library filename, or an absolute http(s) URL of an image file
    other than the background of a map."""
    url = validate_user_url(value)
    if not url or not set(url) & {"/", ":", "\\", "?", "#"}:
        return url
    if not (_is_absolute_http(url) and _IMAGE_FILE_URL.fullmatch(url)):
        raise ValueError("An image URL must be an absolute http or https URL of an image file")
    if _is_map_background(url):
        raise ValueError("An image URL must not point to the background of a map")
    return url


def coerce_image_url(value: object) -> object:
    """``None`` for an image URL ``validate_image_url`` refuses, as ``coerce_user_url``."""
    return _coerced(validate_image_url, value)


def coerce_graph_url(value: object) -> object:
    """``None`` for a graph URL ``validate_graph_url`` refuses, as ``coerce_user_url``."""
    return _coerced(validate_graph_url, value)


# A click-through URL's target. Anything other than a new tab or the same frame
# (``_top``/``_parent``/a named frame) would let the URL replace the whole
# Checkmk UI with an external page, turning an object link into a phishing vector.
_ALLOWED_URL_TARGETS = frozenset({"_blank", "_self"})


def coerce_asset_ref(value: object) -> object:
    """Fold an image/background reference that is not a bare filename to ``None``.

    Map icons and backgrounds are uploaded files; the SPA turns the stored value
    into a ``maps/images|backgrounds/<value>`` asset URL. A value carrying a path
    separator, ``..`` or a scheme could climb out of the asset directory into a
    same-origin GET, so anything but a plain filename is dropped (coerces, so a
    stored map with a stale reference still loads without it).
    """
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None
    if _CONTROL_CHARS.search(value) or set(value) & {"/", "\\", ":"} or ".." in value:
        return None
    return value


def coerce_url_target(value: object) -> object:
    """Fold any stored link target other than a new tab / same frame to ``_blank``.

    Coerces rather than rejects (like ``coerce_color``) because the map models are
    dual-use for reads: a stored map may pre-date this allowlist and must stay
    loadable, while the narrowed value still keeps ``_top``/``_parent`` off-limits.
    """
    if value is None or value == "":
        return value
    if isinstance(value, str) and value in _ALLOWED_URL_TARGETS:
        return value
    return "_blank"


# A map name is a URL component and a per-map permission ident (``map.<name>``);
# a rotation pool is named in a URL (``maps.py?rotation=<pool>``) just the same.
_MAP_NAME_RE = re.compile(MAP_NAME_PATTERN)


def is_valid_map_name(name: str) -> bool:
    return len(name) <= MAP_NAME_MAX_LENGTH and bool(_MAP_NAME_RE.fullmatch(name))


MAX_ROTATION_POOLS: Final = 50


def validate_rotation_pool(value: str) -> str:
    if not is_valid_map_name(value):
        raise ValueError(f"invalid rotation pool name: {value!r}")
    return value


def validate_font_family(value: str | None) -> str | None:
    if value is None or value == "":
        return value
    s = value.strip()
    if not _FONT_RE.fullmatch(s):
        raise ValueError(f"invalid font family: {value!r}")
    return s


def validate_color(value: str | None) -> str | None:
    """Accept a hex/named/`transparent` color; reject anything else (API save-side)."""
    if value is None or value == "":
        return value
    s = value.strip()
    if not _COLOR_RE.fullmatch(s):
        raise ValueError(f"invalid color value: {value!r}")
    return s


def coerce_color(value: object) -> object:
    """Sanitize bad colors to ``None`` so legacy maps still load.

    Read-side companion to ``validate_color`` — pre-existing JSON may carry values
    that newer rules reject (e.g. unsupported CSS expressions written before the
    validator existed). Dropping them is the safe fallback; re-saving the map
    through the API still rejects bad input. A CSS ``rgb()``/``rgba()`` color is
    kept, as the hex color it names.
    """
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None
    try:
        return validate_color(rgb_to_hex(value))
    except ValueError:
        return None


def rgb_to_hex(value: str) -> str:
    """``rgb(...)``/``rgba(...)`` as the hex color it names; any other value as is."""
    if (match := _RGB_RE.fullmatch(value.strip())) is None:
        return value
    red, green, blue = (min(int(channel), 255) for channel in match.group(1, 2, 3))
    color = f"#{red:02x}{green:02x}{blue:02x}"
    if (alpha := match.group(4)) is None:
        return color
    opacity = float(alpha) / 100 if match.group(5) else float(alpha)
    return f"{color}{round(min(max(opacity, 0.0), 1.0) * 255):02x}"


def check_grid(object_type: str, object_id: str) -> None:
    if object_type == "grid" and not re.fullmatch(GRID_ID_PATTERN, object_id):
        raise ValueError(f"a grid's id must match {GRID_ID_PATTERN}")


def check_grid_binding(
    object_type: str,
    object_types: str | None,
    *,
    grid_id: str | None,
    recognize_services: bool | None,
    member_patterns: Iterable[str | None],
) -> None:
    """Refuse what a grid would not apply: a grid named by an object no grid
    leaves out, and the host settings on a grid of services."""
    if grid_id is not None and object_type not in ("host", "service"):
        raise ValueError("only a host or a service is pinned out of a grid")
    if object_type != "grid" or object_types != "service":
        return
    if recognize_services:
        raise ValueError("a grid of services does not count services of its members")
    if any(member_patterns):
        raise ValueError("a grid of services leaves out no members of its members")


def check_grids(view_type: str, object_types: Iterable[str]) -> None:
    grids = sum(1 for object_type in object_types if object_type == "grid")
    if grids and view_type != "static":
        raise ValueError("only a static map takes a grid")
    if grids > GRID_MAX_PER_MAP:
        raise ValueError(f"a map takes at most {GRID_MAX_PER_MAP} grids")
