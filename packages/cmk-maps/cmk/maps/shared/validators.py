#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared validators for user-supplied URL/color fields on maps/presentations."""

import re
from typing import Final

from cmk.maps.shared.map_name import MAP_NAME_MAX_LENGTH, MAP_NAME_PATTERN

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
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None
    try:
        return validate_user_url(value)
    except ValueError:
        return None


# An image is requested with the viewer's session, so one outside the image
# library must name an image file rather than a page of the site.
_IMAGE_FILE_URL = re.compile(r"[^?#\\]*\.(?:png|gif|jpe?g|svg|webp|bmp|ico)", re.IGNORECASE)


def validate_image_url(value: str | None) -> str | None:
    """An image-library filename, or a URL of an image file."""
    url = validate_user_url(value)
    if url and set(url) & {"/", ":"} and not _IMAGE_FILE_URL.fullmatch(url):
        raise ValueError("An image URL must name an image file")
    return url


def coerce_image_url(value: object) -> object:
    """``None`` for an image URL ``validate_image_url`` refuses, as ``coerce_user_url``."""
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None
    try:
        return validate_image_url(value)
    except ValueError:
        return None


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
