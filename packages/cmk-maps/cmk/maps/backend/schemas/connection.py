#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Pydantic schemas for monitoring connection configuration."""

from __future__ import annotations

from ipaddress import ip_address
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator, model_validator

# Cloud-provider metadata services, which would hand IAM tokens to the
# credentialed outbound HTTP path. A denylist rather than a private-range block
# because a remote Checkmk site legitimately lives on an RFC1918 address — so a
# name resolving (or rebinding) to a metadata address is not covered, which the
# `maps.configure` gate on this field has to carry.
_BLOCKED_HOSTS = frozenset(
    {
        "169.254.169.254",  # AWS / GCP / Azure / OpenStack IMDS v1/v2
        "fd00:ec2::254",  # AWS IMDS over IPv6
        "100.100.100.200",  # Alibaba Cloud
        "192.0.0.192",  # Oracle Cloud
        "metadata.google.internal",
        "metadata.goog",
        "metadata",
    }
)


def _normalize_host(hostname: str) -> str:
    """Canonicalise a URL host before matching :data:`_BLOCKED_HOSTS`.

    ``urlparse().hostname`` lowercases and unwraps IPv6 brackets but keeps a
    trailing dot, and an IP literal has many spellings — both would otherwise
    walk past a string comparison.
    """
    host = hostname.rstrip(".")
    try:
        return str(ip_address(host))
    except ValueError:
        return host


def _validate_socket_path(value: str | None) -> str | None:
    """Reject Unix-socket paths that an admin shouldn't be able to set.

    Defense in depth: the FormSpec / API endpoints are already admin-gated, but
    the path is fed to the Livestatus client without any further check. Without
    these rules a careless admin could probe arbitrary files (``/etc/shadow``)
    via the connection-test endpoint, or break the connection-storage layer
    with a path containing NULs.
    """
    if value is None or value == "":
        return value
    if "\x00" in value:
        raise ValueError("Socket path must not contain NUL byte")
    if not value.startswith("/"):
        raise ValueError("Socket path must be absolute")
    if ".." in value.split("/"):
        raise ValueError("Socket path must not contain '..'")
    return value


def _validate_safe_url(value: str | None) -> str | None:
    """Restrict checkmk_url to safe forms.

    Accepts:
      - empty / None
      - absolute path (``/<site>/check_mk``) — Maps prepends ``http://127.0.0.1``
      - http(s) URL to a non-metadata host
    Rejects ``javascript:``, ``file:``, ``data:``, userinfo (``user:pass@``),
    and known cloud-metadata hosts.
    """
    if not value:
        return value
    if len(value) > 2048:
        raise ValueError("URL too long")
    s = value.strip()
    if s.startswith("/"):
        if ".." in s.split("/"):
            raise ValueError("URL must not contain '..'")
        return s
    parsed = urlparse(s)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme!r}")
    if parsed.username or parsed.password:
        raise ValueError("URL must not contain userinfo")
    host = _normalize_host(parsed.hostname or "")
    if host in _BLOCKED_HOSTS:
        raise ValueError(f"Host {host!r} is blocked")
    return s


# Sentinel returned in API responses in place of real secrets. Frontend echoes
# this back unchanged on edit; the route preserves the existing secret in that
# case (see app.api.v1.connections.update_backend).
REDACTED_SECRET = "***REDACTED***"


class ConnectionConfig(BaseModel):
    id: str = Field(..., max_length=64, pattern=r"^[a-zA-Z0-9_\-]+$")
    type: Literal["livestatus"] = "livestatus"
    label: str = Field(default="", max_length=200)
    # Livestatus connection (Unix socket OR TCP, not both)
    socket_path: str | None = Field(default=None, max_length=512)
    host: str | None = Field(default=None, max_length=255)
    # Optional: unix-socket-only setups have no port; UI also emits null when cleared.
    port: int | None = Field(default=None, ge=1, le=65535)
    # TLS for the TCP livestatus path (OMD's `LIVESTATUS_TLS=on` ships stunnel
    # on the 6557 listener). Ignored for unix-socket connections. Defaults to
    # on because every supported OMD version enables TLS by default in current
    # site setups, and a plain TCP connect against a TLS port looks "open" but
    # silently returns garbage.
    tls: bool = True
    # Default on, matching Checkmk's own distributed-site connection (the site
    # valuespec prefills "Verify server certificate" to True and an AC test flags
    # it when off). Verification uses this site's trusted CA store
    # (var/ssl/ca-certificates.crt); for an external endpoint whose CA this site
    # does not trust yet, the admin adds it to the trusted CAs rather than
    # shipping a credentialed connection that is MITM-open by default.
    tls_verify: bool = True
    timeout: float = Field(default=10.0, ge=0.1, le=300.0)
    checkmk_url: str | None = Field(default=None, description="e.g. /<site>/check_mk")
    automation_user: str | None = Field(default=None, max_length=200)
    automation_secret: str | None = Field(default=None, max_length=512)

    @field_validator("checkmk_url")
    @classmethod
    def _safe_url(cls, v: str | None) -> str | None:
        return _validate_safe_url(v)

    @field_validator("socket_path")
    @classmethod
    def _safe_socket_path(cls, v: str | None) -> str | None:
        return _validate_socket_path(v)

    @model_validator(mode="after")
    def _require_type_targets(self) -> ConnectionConfig:
        _require_type_targets(self)
        return self


def _require_type_targets(cfg: ConnectionConfig) -> None:
    if cfg.type == "livestatus":
        has_socket = bool((cfg.socket_path or "").strip())
        has_host = bool((cfg.host or "").strip())
        if not has_socket and not has_host:
            raise ValueError("Livestatus connection needs either a Unix socket path or a TCP host")


class ConnectionListEntry(BaseModel):
    """Read projection of a connection for the list API.

    Same field names as :class:`ConnectionConfig` so SPA consumers keep working,
    but without its "socket or host" invariant: that is a rule about a *stored*
    connection, and this view may legitimately carry neither once
    :func:`to_list_entry` has blanked them. No defaults either — a response
    always carries every key, so the generated client type has them required.
    """

    id: str
    type: Literal["livestatus"]
    label: str
    socket_path: str | None
    host: str | None
    port: int | None
    tls: bool
    tls_verify: bool
    timeout: float
    checkmk_url: str | None
    automation_user: str | None
    automation_secret: str | None


def to_list_entry(cfg: ConnectionConfig, *, full: bool) -> ConnectionListEntry:
    """Project *cfg* onto the list response; ``full`` requires ``maps.configure``.

    The list is readable with the plain edit grant (map authors pick a connection
    and build links into the target site), which is every ordinary role. The SPA
    consumes only id/label/type/checkmk_url; the endpoint details are Setup-owned.
    """
    return ConnectionListEntry(
        id=cfg.id,
        type=cfg.type,
        label=cfg.label,
        socket_path=cfg.socket_path if full else None,
        host=cfg.host if full else None,
        port=cfg.port if full else None,
        tls=cfg.tls,
        tls_verify=cfg.tls_verify,
        timeout=cfg.timeout,
        checkmk_url=cfg.checkmk_url,
        automation_user=cfg.automation_user if full else None,
        automation_secret=REDACTED_SECRET if cfg.automation_secret else None,
    )
