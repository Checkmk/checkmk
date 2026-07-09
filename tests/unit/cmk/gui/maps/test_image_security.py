#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Upload content validation — magic-byte sniffing and SVG XSS sandboxing.

These are the daemon's only defence against an upload lying about its
Content-Type or smuggling script into an SVG that is later served (and opened)
as ``image/svg+xml`` under the application origin.
"""

import re

import pytest

from cmk.maps.gui._image_security import (
    is_safe_svg,
    is_valid_image,
    is_valid_image_name,
    safe_image_stem,
)

_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 12
_GIF = b"GIF89a" + b"\x00" * 10
_WEBP = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 4

_SVG_OK = b'<svg xmlns="http://www.w3.org/2000/svg"><rect width="10" height="10"/></svg>'


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(_PNG, id="png"),
        pytest.param(_JPEG, id="jpeg"),
        pytest.param(_WEBP, id="webp"),
        pytest.param(_SVG_OK, id="svg"),
    ],
)
def test_is_valid_image_accepts_known_formats(content: bytes) -> None:
    assert is_valid_image(content)


def test_is_valid_image_rejects_empty() -> None:
    assert not is_valid_image(b"")


def test_is_valid_image_rejects_unknown_bytes() -> None:
    assert not is_valid_image(b"this is not an image")


def test_is_valid_image_gif_gated_by_flag() -> None:
    assert is_valid_image(_GIF, allow_gif=True)
    # An icon upload (allow_gif=False) must reject a GIF body even if a caller
    # claimed image/png — the magic byte is the truth, not the Content-Type.
    assert not is_valid_image(_GIF, allow_gif=False)


def test_is_valid_image_svg_gated_by_flag() -> None:
    assert not is_valid_image(_SVG_OK, allow_svg=False)


def test_is_valid_image_rejects_script_bearing_svg() -> None:
    evil = b'<svg xmlns="http://www.w3.org/2000/svg"><script>alert(1)</script></svg>'
    assert not is_valid_image(evil)


def test_is_safe_svg_accepts_plain_svg() -> None:
    assert is_safe_svg(_SVG_OK)


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b"<svg><script>alert(1)</script></svg>", id="script"),
        pytest.param(b"<svg><foreignObject><body/></foreignObject></svg>", id="foreign-object"),
        pytest.param(b'<svg onload="alert(1)"><rect/></svg>', id="on-event-attr"),
        # SMIL: <set>/<animate*> can rewrite an href to javascript: at runtime.
        pytest.param(b'<svg><set attributeName="href" to="javascript:alert(1)"/></svg>', id="set"),
        pytest.param(b'<svg><animate attributeName="x"/></svg>', id="animate"),
        pytest.param(b'<svg><animateTransform attributeName="transform"/></svg>', id="animatexf"),
        pytest.param(b'<svg><a href="javascript:alert(1)"><rect/></a></svg>', id="js-href"),
        # Whitespace character references stay literal in the parsed attribute
        # value; browsers strip them before resolving the scheme, so these are
        # live "javascript:" despite the embedded tab/newline.
        pytest.param(
            b'<svg><a href="java&#9;script:alert(1)"><rect/></a></svg>', id="js-href-tab-ref"
        ),
        pytest.param(
            b'<svg><a href="java&#10;script:alert(1)"><rect/></a></svg>', id="js-href-newline-ref"
        ),
        pytest.param(b'<svg><use href="https://evil.example/x.svg#i"/></svg>', id="remote-use"),
        pytest.param(
            b'<svg><image href="data:image/svg+xml;base64,AAAA"/></svg>', id="svg-datauri"
        ),
        # An xml-stylesheet PI is dropped by the element walk, so it is caught on
        # the raw bytes — a browser navigating to the .svg applies the XSLT.
        pytest.param(
            b'<?xml-stylesheet type="text/xsl" href="https://evil.example/x.xsl"?>'
            b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>',
            id="xslt-pi",
        ),
        # External subresource loads from a "sandboxed" icon: <image> fetch and
        # CSS @import / url() to a remote host (tracking / client-side SSRF).
        pytest.param(
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b'<image href="https://evil.example/track.png"/></svg>',
            id="remote-image",
        ),
        pytest.param(
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b"<style>@import url(https://evil.example/x.css)</style></svg>",
            id="css-import",
        ),
        pytest.param(
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b"<style>rect{fill:url(https://evil.example/x.png)}</style></svg>",
            id="css-remote-url",
        ),
        pytest.param(
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b"<style><x/>@import url(https://evil.example/x.css)</style></svg>",
            id="css-import-in-child-tail",
        ),
        pytest.param(
            b'<svg xmlns="http://www.w3.org/2000/svg">'
            b"<style><x><y/></x>rect{fill:url(https://evil.example/x.png)}</style></svg>",
            id="css-remote-url-in-nested-tail",
        ),
        pytest.param(b"<html><body/></html>", id="non-svg-root"),
        pytest.param(b"<svg><rect></svg", id="malformed-xml"),
    ],
)
def test_is_safe_svg_rejects_xss_vectors(content: bytes) -> None:
    assert not is_safe_svg(content)


@pytest.mark.parametrize(
    "content",
    [
        pytest.param(b'<svg><use href="#icon"/></svg>', id="local-fragment-use"),
        pytest.param(b'<svg><image href="data:image/png;base64,AAAA"/></svg>', id="raster-datauri"),
        # The XML declaration itself is a PI, but a legitimate one.
        pytest.param(
            b'<?xml version="1.0" encoding="UTF-8"?>'
            b'<svg xmlns="http://www.w3.org/2000/svg"><rect/></svg>',
            id="xml-declaration",
        ),
        # Local paint references in a <style> block stay allowed.
        pytest.param(
            b'<svg xmlns="http://www.w3.org/2000/svg"><style>rect{fill:url(#grad)}</style></svg>',
            id="css-local-url",
        ),
    ],
)
def test_is_safe_svg_accepts_safe_references(content: bytes) -> None:
    assert is_safe_svg(content)


@pytest.mark.parametrize("name", ["icon.png", "my-logo_2.svg", "a"])
def test_is_valid_image_name_accepts_plain_names(name: str) -> None:
    assert is_valid_image_name(name)


@pytest.mark.parametrize("name", ["../escape", "a/b.png", "a\\b.png", "", ".", ".."])
def test_is_valid_image_name_rejects_traversal_and_separators(name: str) -> None:
    assert not is_valid_image_name(name)


@pytest.mark.parametrize("raw", ["../../etc/passwd", "a/b\\c", "evil name!.png", "x;rm -rf", None])
def test_safe_image_stem_neutralises_everything_dangerous(raw: str | None) -> None:
    stem = safe_image_stem(raw)
    # Only the safe alphabet survives, and the result is never empty.
    assert re.fullmatch(r"[A-Za-z0-9_\-]+", stem)
    assert "/" not in stem and "\\" not in stem
