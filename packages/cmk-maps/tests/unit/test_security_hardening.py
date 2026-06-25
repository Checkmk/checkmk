#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Security validators added before the public release.

Covers the user-supplied-URL allowlist, map-object XSS rejection, dyngroup
Livestatus-filter injection, connection-URL SSRF mitigations, and secret
redaction. SVG safety is covered separately in the GUI's ``test_image_security``
(image handling is GUI-owned now).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from cmk.maps.backend.connections import livestatus
from cmk.maps.backend.core.config import settings
from cmk.maps.backend.integrations import checkmk_sites
from cmk.maps.backend.schemas.connection import (
    _validate_safe_url,
    _validate_socket_path,
    ConnectionConfig,
    REDACTED_SECRET,
    to_list_entry,
)
from cmk.maps.backend.schemas.map import (
    MapElement,
    MapElementUpdate,
)
from cmk.maps.backend.services.state_service import _names_or_filter
from cmk.maps.shared.validators import coerce_user_url, validate_user_url

# --- validate_user_url: scheme allowlist + rejection ---


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("https://example.com/x", id="https"),
        pytest.param("http://example.com/x", id="http"),
        pytest.param("mailto:ops@example.com", id="mailto"),
        pytest.param("tel:+491234567", id="tel"),
        pytest.param("ssh://switch01", id="ssh"),
        pytest.param("telnet://switch01", id="telnet"),
        pytest.param("rdp://winserver", id="rdp"),
        pytest.param("vnc://kvm01", id="vnc"),
        pytest.param("ftp://files.example.com", id="ftp"),
        pytest.param("/relative/path?x=1", id="relative-path"),
        pytest.param("view.py?view_name=host", id="scheme-less-relative"),
    ],
)
def test_validate_user_url_accepts_allowlisted(url: str | None) -> None:
    assert validate_user_url(url) == (url.strip() if url else url)


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("javascript:alert(1)", id="javascript"),
        pytest.param("JavaScript:alert(1)", id="javascript-mixed-case"),
        pytest.param("data:text/html,<script>", id="data"),
        pytest.param("vbscript:msgbox(1)", id="vbscript"),
        pytest.param("file:///etc/passwd", id="file"),
        pytest.param("blob:https://x/y", id="blob"),
        pytest.param("chrome://settings", id="chrome"),
        pytest.param("about:blank", id="about"),
        # Protocol-relative URLs inherit the page scheme and point off-site.
        pytest.param("//cdn.example.com/x", id="protocol-relative"),
        # Browsers strip ASCII control chars when parsing, so these would still
        # execute on click — the validator must reject them outright.
        pytest.param("java\tscript:alert(1)", id="tab-in-scheme"),
        pytest.param("java\nscript:alert(1)", id="newline-in-scheme"),
        pytest.param("java\rscript:alert(1)", id="cr-in-scheme"),
        pytest.param("\x01javascript:alert(1)", id="leading-control"),
        pytest.param("http://example.com/" + "a" * 5000, id="overlong"),
    ],
)
def test_validate_user_url_rejects_dangerous(url: str) -> None:
    with pytest.raises(ValueError):
        validate_user_url(url)


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("ssh://-oProxyCommand=curl+evil@switch01", id="option-as-user"),
        pytest.param("ssh://-oProxyCommand=curl", id="option-as-host"),
        pytest.param("telnet://-evil@switch01", id="telnet-option-as-user"),
        pytest.param("rdp://ops@-evil", id="option-as-host-with-user"),
        pytest.param("vnc://kvm01%20-evil", id="escaped-space"),
        pytest.param("ssh://kvm01 -evil", id="literal-space"),
        pytest.param("ssh://", id="no-host"),
    ],
)
def test_validate_user_url_rejects_remote_handler_arguments(url: str) -> None:
    # A local ssh/telnet/rdp/vnc handler turns the URL into command arguments, so
    # the authority must not be readable as an option or split into several.
    with pytest.raises(ValueError):
        validate_user_url(url)


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("ssh://ops@switch01", id="user-and-host"),
        pytest.param("ssh://ops@switch01:2222/-not-an-option", id="port-and-path"),
        pytest.param("vnc://kvm-01.example.com:1", id="hyphen-inside-host"),
    ],
)
def test_validate_user_url_keeps_ordinary_remote_handler_urls(url: str) -> None:
    assert validate_user_url(url) == url


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        pytest.param(None, None, id="none-passthrough"),
        pytest.param("", "", id="empty-passthrough"),
        pytest.param("https://example.com/x", "https://example.com/x", id="good-passthrough"),
        pytest.param("javascript:alert(1)", None, id="bad-dropped"),
        pytest.param(123, None, id="non-string-dropped"),
    ],
)
def test_coerce_user_url_drops_invalid(value: object, expected: object) -> None:
    assert coerce_user_url(value) == expected


# --- map-object URL validation + XSS rejection ---


@pytest.mark.parametrize("field", ["url", "hover_url", "graph_url"])
@pytest.mark.parametrize(
    "scheme",
    [
        pytest.param("javascript:", id="javascript"),
        pytest.param("data:", id="data"),
        pytest.param("vbscript:", id="vbscript"),
        pytest.param("file:", id="file"),
        pytest.param("JavaScript:", id="javascript-mixed-case"),
        pytest.param("java\tscript:", id="tab-in-scheme"),
        pytest.param("java\nscript:", id="newline-in-scheme"),
        pytest.param("java\rscript:", id="cr-in-scheme"),
        pytest.param("\x01javascript:", id="leading-control"),
        pytest.param("blob:", id="blob"),
        pytest.param("chrome:", id="chrome"),
        pytest.param("about:", id="about"),
    ],
)
def test_map_element_rejects_xss_url_schemes(field: str, scheme: str) -> None:
    with pytest.raises(ValidationError):
        MapElement.model_validate({"id": "o1", "type": "image", field: scheme + "alert(1)"})
    with pytest.raises(ValidationError):
        MapElementUpdate.model_validate({field: scheme + "alert(1)"})


@pytest.mark.parametrize("field", ["url", "hover_url", "graph_url"])
@pytest.mark.parametrize(
    "url",
    [
        pytest.param("https://example.com/x", id="https"),
        pytest.param("http://example.com/x", id="http"),
        pytest.param("mailto:ops@example.com", id="mailto"),
        pytest.param("tel:+491234567", id="tel"),
        pytest.param("ssh://switch01", id="ssh"),
        pytest.param("rdp://winserver", id="rdp"),
        pytest.param("vnc://kvm01", id="vnc"),
        pytest.param("/relative/path?x=1", id="relative-path"),
        pytest.param("view.py?view_name=host", id="scheme-less-relative"),
    ],
)
def test_map_element_accepts_safe_urls(field: str, url: str) -> None:
    MapElement.model_validate({"id": "o1", "type": "image", field: url})


def test_map_element_rejects_protocol_relative_url() -> None:
    # ``//host`` is an off-site open-redirect vector, so the allowlist rejects it.
    with pytest.raises(ValidationError):
        MapElement.model_validate({"id": "o1", "type": "image", "url": "//cdn.example.com/x"})


# --- map-object color validation + CSS-injection rejection ---
# The colors are interpolated into hand-built marker HTML by the worldmap
# renderer; the strict allowlist keeps attribute-breakout payloads out at the
# schema layer (the SPA additionally escapes them at the render sink).


@pytest.mark.parametrize(
    "field",
    ["line_color", "line_color_border", "label_border", "textbox_background", "textbox_border"],
)
def test_map_element_rejects_css_injection_colors(field: str) -> None:
    payload = '#fff" onmouseover="alert(1)'
    with pytest.raises(ValidationError):
        MapElement.model_validate({"id": "o1", "type": "image", field: payload})
    with pytest.raises(ValidationError):
        MapElementUpdate.model_validate({field: payload})


@pytest.mark.parametrize("field", ["color", "background"])
def test_label_config_rejects_css_injection_colors(field: str) -> None:
    with pytest.raises(ValidationError):
        MapElement.model_validate(
            {"id": "o1", "type": "image", "label": {field: '#000" onload="x'}}
        )


@pytest.mark.parametrize("color", ["#fff", "#ffffff", "#ffffffff", "red", "transparent"])
def test_map_element_accepts_safe_colors(color: str) -> None:
    MapElement.model_validate({"id": "o1", "type": "image", "line_color": color})


# --- dyngroup filter injection (LQL / newline smuggling) ---
# The normalize_object_filter allowlist itself is pinned in the shared
# packages/cmk-maps/tests/unit/test_filters.py; here we cover the map-validator
# wiring that runs it during schema validation.


def test_map_element_rejects_filter_injection() -> None:
    with pytest.raises(ValidationError):
        MapElement.model_validate(
            {"id": "d1", "type": "dyngroup", "object_filter": "Filter: a\\nStats: state = 0"}
        )


def test_map_element_update_normalises_filter() -> None:
    obj = MapElementUpdate.model_validate({"object_filter": "Filter: host_name ~ ^web"})
    assert obj.object_filter == "Filter: host_name ~ ^web\n"


# The runtime location-bundle filter (``_names_or_filter``) is built from live
# geo-host names and — unlike a persisted object_filter — skips the schema-layer
# normalize_object_filter. get_dyngroup_state later un-escapes ``\n`` → a real
# newline, so a name carrying a literal backslash-n (or a real newline) must be
# dropped here or it smuggles in extra Livestatus header lines.


def test_names_or_filter_drops_injection_candidates() -> None:
    out = _names_or_filter(
        [
            "good-host",
            "evil\\nStats: state = 0",  # literal backslash-n → un-escaped downstream
            "line\nbreak",  # real newline
        ]
    )
    assert out == "Filter: name = good-host\n"
    assert "Stats:" not in out
    assert "\\n" not in out


def test_names_or_filter_builds_or_for_multiple_safe_names() -> None:
    assert _names_or_filter(["h1", "h2"]) == "Filter: name = h1\nFilter: name = h2\nOr: 2\n"


# --- AuthUser header escaping (the one query value that reaches a header) ---


def test_authuser_header_is_lqencoded(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    # Every Filter: value is lqencode'd; AuthUser flows straight into a header
    # line, so it must be escaped too — a newline-bearing value would otherwise
    # inject arbitrary Livestatus header/query lines.
    monkeypatch.setattr(settings, "checkmk_omd_root", str(tmp_path))
    monkeypatch.setattr(checkmk_sites, "sites_mk_mtime", lambda: 0.0)
    monkeypatch.setattr(checkmk_sites, "load_sites", lambda: None)
    conn = livestatus.LivestatusConnection(
        socket_path=str(tmp_path / "tmp" / "run" / "live"), host=None
    )

    captured: dict[str, str] = {}

    class _FakeClient:
        def query(self, _query: object, add_headers: str = "") -> list[object]:
            captured["headers"] = add_headers
            return []

        def disconnect(self) -> None: ...

    monkeypatch.setattr(conn, "_make_singlesite_connection", _FakeClient)

    token = livestatus._auth_user_ctx.set("evil\nStats: state = 0")  # noqa: SLF001
    try:
        conn._run_singlesite_sync("GET hosts\nColumns: name\n")  # noqa: SLF001
    finally:
        livestatus._auth_user_ctx.reset(token)  # noqa: SLF001

    headers = captured["headers"]
    assert headers.startswith("AuthUser: ")
    # A single header line: the injected newline was neutralised by lqencode.
    assert headers.count("\n") == 1
    assert "\nStats:" not in headers


# --- connection URL validation (SSRF mitigations) ---


@pytest.mark.parametrize(
    "url",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("/CMC/check_mk", id="relative-path"),
        pytest.param("http://localhost/heute", id="http-localhost"),
        pytest.param("https://monitor.example.com/check_mk", id="https-host"),
    ],
)
def test_connection_accepts_safe_urls(url: str | None) -> None:
    ConnectionConfig(id="b1", socket_path="/omd/live", checkmk_url=url)


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("javascript:alert(1)", id="javascript"),
        pytest.param("file:///etc/passwd", id="file"),
        pytest.param("data:text/html,<script>", id="data"),
        pytest.param("ftp://example.com", id="ftp"),
        pytest.param("http://user:pass@example.com", id="userinfo"),
        pytest.param("http://169.254.169.254/latest/meta-data", id="cloud-metadata"),
        pytest.param("/CMC/../../etc/passwd", id="relative-traversal"),
        pytest.param("http://example.com/" + "a" * 3000, id="overlong"),
    ],
)
def test_connection_rejects_dangerous_urls(url: str) -> None:
    with pytest.raises(ValidationError):
        ConnectionConfig(id="b1", host="h", checkmk_url=url)


def test_validate_safe_url_passes_through_safe_value() -> None:
    assert _validate_safe_url("/CMC/check_mk") == "/CMC/check_mk"


@pytest.mark.parametrize(
    "url",
    [
        pytest.param("file:///etc/passwd", id="file"),
        pytest.param("http://metadata.google.internal/x", id="gcp-metadata-host"),
        pytest.param("/CMC/../etc", id="relative-traversal"),
    ],
)
def test_validate_safe_url_rejects_dangerous_value(url: str) -> None:
    with pytest.raises(ValueError):
        _validate_safe_url(url)


# --- connection secret redaction ---


def test_list_entry_replaces_automation_secret() -> None:
    cfg = ConnectionConfig(id="b1", socket_path="/omd/live", automation_secret="real-secret")
    assert to_list_entry(cfg, full=True).automation_secret == REDACTED_SECRET


def test_list_entry_keeps_none_secret() -> None:
    cfg = ConnectionConfig(id="b1", socket_path="/omd/live")
    assert to_list_entry(cfg, full=True).automation_secret is None


def test_list_entry_drops_transport_without_configure() -> None:
    cfg = ConnectionConfig(id="b1", socket_path="/omd/live", automation_user="automation")
    entry = to_list_entry(cfg, full=False)
    assert entry.socket_path is None
    assert entry.automation_user is None


# --- socket-path validation (defense-in-depth against arbitrary-file probing) ---


@pytest.mark.parametrize(
    "path",
    [
        pytest.param(None, id="none"),
        pytest.param("", id="empty"),
        pytest.param("/omd/sites/heute/tmp/run/live", id="absolute"),
        pytest.param("/omd/sites/my.site-1/tmp/run/live", id="absolute-with-punctuation"),
    ],
)
def test_validate_socket_path_accepts_safe(path: str | None) -> None:
    assert _validate_socket_path(path) == path


@pytest.mark.parametrize(
    ("path", "reason"),
    [
        pytest.param("relative/live", "absolute", id="relative"),
        pytest.param("./live", "absolute", id="dot-relative"),
        pytest.param("/omd/../../etc/shadow", "'..'", id="traversal"),
        pytest.param("/live\x00/etc/shadow", "NUL", id="nul-byte"),
    ],
)
def test_validate_socket_path_rejects_dangerous(path: str, reason: str) -> None:
    with pytest.raises(ValueError, match=reason):
        _validate_socket_path(path)


@pytest.mark.parametrize(
    "path",
    [
        pytest.param("relative/live", id="relative"),
        pytest.param("/omd/../../etc/shadow", id="traversal"),
        pytest.param("/live\x00/etc/shadow", id="nul-byte"),
    ],
)
def test_connection_rejects_dangerous_socket_path(path: str) -> None:
    # The same reject branches must fire through the schema's field validator.
    with pytest.raises(ValidationError):
        ConnectionConfig(id="b1", socket_path=path)
