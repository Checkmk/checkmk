#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Image content validation — magic-byte checks and SVG XML sandboxing.

These helpers reject uploads that lie about their Content-Type, and — for SVGs —
block the usual XXE / billion-laughs footguns by parsing with defusedxml.
"""

import codecs
import re
from pathlib import Path

from defusedxml import ElementTree as DefusedET
from defusedxml.common import DefusedXmlException

# Icons are rendered as-is in the map. GIF is intentionally excluded — we
# don't want animated icons flickering in map overviews.
ICON_MIME_TYPES = frozenset({"image/png", "image/jpeg", "image/svg+xml", "image/webp"})
ICON_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".svg", ".webp"})

# Background images of static maps may include GIF — a common legacy
# asset format for imported maps.
BACKGROUND_MIME_TYPES = frozenset(
    {"image/png", "image/jpeg", "image/gif", "image/svg+xml", "image/webp"}
)
BACKGROUND_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"})

# Image names map to files under the site's images dir. The delete/usage
# endpoints reject path separators outright; uploads sanitise the stem to this
# alphabet so a traversal or Windows path can never escape the directory or
# persist a file those endpoints (which reject '\\') can't address again.
_UNSAFE_STEM_CHARS = re.compile(r"[^a-zA-Z0-9_\-]")


def is_valid_image_name(name: str) -> bool:
    """Reject path separators and the traversal specials in a stored image name."""
    return "/" not in name and "\\" not in name and name not in ("", ".", "..")


def safe_image_stem(filename: str | None) -> str:
    """Sanitise an uploaded filename's stem to ``[A-Za-z0-9_-]`` (never empty)."""
    return _UNSAFE_STEM_CHARS.sub("_", Path(filename or "image").stem) or "image"


# Raster magic bytes
_PNG_MAGIC = b"\x89PNG"
_JPEG_MAGIC = b"\xff\xd8\xff"
_GIF_MAGIC = (b"GIF87a", b"GIF89a")
_WEBP_RIFF = b"RIFF"
_WEBP_MARK = b"WEBP"


# Real-world SVGs (Illustrator/Inkscape exports) often carry an XML
# declaration, a DOCTYPE, and licence comments before the root element, so the
# sniff window has to be generous — a 512-byte window missed those exports.
_SVG_SNIFF_BYTES = 65536


def _looks_like_svg_header(content: bytes) -> bool:
    """Quick byte-level sniff — presence of '<svg' in the leading bytes.

    XML must start with markup (after an optional BOM and whitespace), so anything
    else is not an SVG and is rejected without lowercasing the sniff window.
    """
    head = content[:_SVG_SNIFF_BYTES].removeprefix(codecs.BOM_UTF8).lstrip()
    return head.startswith(b"<") and b"<svg" in head.lower()


# SVG elements / attributes that can execute scripts. Rejected even though
# defusedxml accepts them — once an SVG sits under /images and is opened with
# image/svg+xml, scripts run with the application's origin (XSS). ``use`` is
# *not* blanket-rejected (internal `#fragment` references are both safe and
# common); instead its href is constrained below.
# SMIL animation elements are included: <set>/<animate*> can rewrite an href to
# a ``javascript:`` URI at runtime, and <handler> binds script — all SVG XSS
# vectors despite carrying no inline script.
# Lowercase, and matched against a lowercased tag name: XML itself is
# case-sensitive, but an SVG parsed in an HTML context has its tag names
# case-folded (the HTML parser's SVG tag-name adjustment maps e.g.
# ``foreignobject`` back to ``foreignObject``), so a case variant must not slip
# through. Same matching rule as _SVG_LOCAL_HREF_ONLY_TAGS below.
_SVG_FORBIDDEN_TAGS = frozenset(
    {
        "script",
        "foreignobject",
        "set",
        "animate",
        "animatetransform",
        "animatemotion",
        "handler",
    }
)
_SVG_FORBIDDEN_ATTR_PREFIXES = ("on",)

# Schemes that can execute or read local resources — never allowed in any href.
_DANGEROUS_URI_SCHEMES = ("javascript:", "vbscript:", "file:")
# Browsers strip ASCII whitespace and control chars (notably tab, newline, CR)
# from a URL before resolving its scheme, so ``java&#9;script:`` executes as
# ``javascript:``. The XML parser keeps such a character reference as a literal
# control char in the attribute value, and ``str.strip()`` only touches the
# ends — so we drop every C0 control / space before the scheme comparison.
_URL_IGNORED_CHARS = re.compile(r"[\x00-\x20]")
# data: URIs are allowed only for embedded raster images. text/html and
# image/svg+xml data URIs can carry script, so they stay rejected.
_SAFE_DATA_URI_PREFIXES = (
    "data:image/png",
    "data:image/jpeg",
    "data:image/jpg",
    "data:image/gif",
    "data:image/webp",
)

# Elements whose href pulls an *external* subresource: <use> clones a referenced
# fragment, <image>/<feImage> fetch an image. All three are constrained to local
# ``#fragment`` targets (or a safe embedded data: raster) — a remote target turns
# a "sandboxed" icon into a tracker / client-side SSRF and, for <use>, can pull
# in and run external SVG.
_SVG_LOCAL_HREF_ONLY_TAGS = frozenset({"use", "image", "feimage"})

# A <style> block can pull external CSS via @import or url(...), leaking the
# viewer's IP and enabling CSS-based exfiltration. Reject remote references while
# still allowing local url(#gradient) / url(data:...) paints.
_CSS_EXTERNAL_REF = re.compile(r"@import|url\(\s*['\"]?\s*(?:https?:|//|file:)", re.IGNORECASE)

# ElementTree silently drops XML processing instructions, so the element walk
# below never sees a leading ``<?xml-stylesheet ...?>`` PI — yet the original
# bytes we store keep it, and a browser navigating straight to the .svg applies
# the referenced XSLT, which can emit script in our origin. Only the XML
# declaration itself (target ``xml``) is allowed; any other PI target is rejected
# on the raw bytes before the tree is trusted.
_XML_PI_TARGET = re.compile(rb"<\?\s*([^\s?>]+)")


def _href_is_safe(value: str, *, local_only: bool) -> bool:
    """Whether an href / xlink:href value is safe for a sandboxed SVG icon."""
    v = value.strip()
    low = _URL_IGNORED_CHARS.sub("", v).lower()
    if low.startswith(_DANGEROUS_URI_SCHEMES):
        return False
    if low.startswith("data:"):
        # Only embedded rasters; svg+xml/text data URIs could carry script.
        return low.startswith(_SAFE_DATA_URI_PREFIXES)
    if local_only:
        # <use>/<image>/<feImage> may only reference a local fragment — a remote
        # target lets the icon pull in (and run) external content.
        return v.startswith("#")
    return True


def _has_unsafe_processing_instruction(content: bytes) -> bool:
    """True if *content* carries any XML PI other than the ``<?xml?>`` declaration."""
    return any(m.group(1).lower() != b"xml" for m in _XML_PI_TARGET.finditer(content))


def is_safe_svg(content: bytes) -> bool:
    """Parse *content* as SVG with defusedxml; reject script vectors.

    Must be called only after a byte-level ``<svg`` sniff — defusedxml parses any
    well-formed XML, but only a real ``<svg>`` root element is acceptable here.

    A DOCTYPE is permitted (the standard SVG DTD reference is ubiquitous in
    exported assets) but ``forbid_entities``/``forbid_external`` stay on, so
    billion-laughs entity expansion and XXE external entities are still blocked.
    The parsed tree is then walked to reject ``<script>``, on-event attributes,
    ``<foreignObject>``, remote ``<use>`` targets, and script-bearing URIs.
    """
    # defusedxml ships without type stubs in the site environment.
    parser = DefusedET.DefusedXMLParser(  # type: ignore[no-untyped-call]
        forbid_dtd=False, forbid_entities=True, forbid_external=True
    )
    try:
        parser.feed(content)
        root = parser.close()
    except DefusedXmlException, DefusedET.ParseError:
        return False
    if root.tag.rsplit("}", 1)[-1] != "svg":
        return False
    # PIs are invisible to the element walk below (ElementTree drops them), so a
    # smuggled xml-stylesheet/XSLT PI must be caught on the raw bytes.
    if _has_unsafe_processing_instruction(content):
        return False
    for elem in root.iter():
        local_tag = elem.tag.rsplit("}", 1)[-1].lower()
        if local_tag in _SVG_FORBIDDEN_TAGS:
            return False
        # ``itertext()``, not ``.text``: a child inside <style> pushes the rest
        # into its ``tail``, so ``<style><x/>@import url(…)</style>`` would slip
        # past while the browser still applies the rule.
        if local_tag == "style" and _CSS_EXTERNAL_REF.search("".join(elem.itertext())):
            return False
        local_only = local_tag in _SVG_LOCAL_HREF_ONLY_TAGS
        for attr_name, attr_val in elem.attrib.items():
            local_attr = attr_name.rsplit("}", 1)[-1].lower()
            if local_attr.startswith(_SVG_FORBIDDEN_ATTR_PREFIXES):
                return False
            # A `style` attribute carries CSS just like a <style> block, so it can
            # pull an external paint server / @import the same way — check it too.
            if local_attr == "style" and _CSS_EXTERNAL_REF.search(attr_val):
                return False
            if local_attr == "href" and not _href_is_safe(attr_val, local_only=local_only):
                return False
    return True


def is_valid_image(content: bytes, *, allow_svg: bool = True, allow_gif: bool = True) -> bool:
    """True if *content* starts with a recognised raster header or is a safe SVG.

    ``allow_gif=False`` for icon uploads — ICON_MIME_TYPES excludes GIF (no
    animated icons), and without the flag a GIF body with a faked PNG
    Content-Type would slip through the magic-byte check.
    """
    if not content:
        return False
    head = content[:16]
    if head[:4] == _PNG_MAGIC:
        return True
    if head[:3] == _JPEG_MAGIC:
        return True
    if allow_gif and head[:6] in _GIF_MAGIC:
        return True
    if head[:4] == _WEBP_RIFF and content[8:12] == _WEBP_MARK:
        return True
    if allow_svg and _looks_like_svg_header(content):
        return is_safe_svg(content)
    return False
