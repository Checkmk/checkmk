#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Shared validators for user-supplied URL/color fields on maps/presentations."""

from __future__ import annotations

import re

# Hex (#rgb/#rgba/#rrggbb/#rrggbbaa), a plain CSS named color, or "transparent".
# Strict on purpose — keeps `<script>`, `javascript:`, `expression(...)` and other
# CSS-injection payloads out of stroke/background/fill attributes rendered downstream.
_COLOR_RE = re.compile(r"^(#[0-9a-fA-F]{3,8}|[a-zA-Z]{1,32}|transparent)$")

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
_AUTHORITY_END = re.compile(r"[/?#]")


def _validate_os_handler_authority(rest: str) -> None:
    """Reject an authority a remote-access handler would read as options."""
    authority = _AUTHORITY_END.split(rest.removeprefix("//"), 1)[0]
    userinfo, _, host = authority.rpartition("@")
    if not host:
        raise ValueError("Remote access URL needs a host")
    if userinfo.startswith("-") or host.startswith("-"):
        raise ValueError("Remote access URL must not start its user or host with '-'")
    if any(c.isspace() for c in authority) or "%" in authority:
        raise ValueError("Remote access URL must not escape or split its host")


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
    # off-site — reject them so a relative-looking value can't become an
    # open-redirect / off-site resource load.
    if s.startswith("//"):
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
    through the API still rejects bad input.
    """
    if value is None or value == "":
        return value
    if not isinstance(value, str):
        return None
    try:
        return validate_color(value)
    except ValueError:
        return None
