#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import urlparse

_EXTENSIONS_TO_IGNORE = {".png", ".svg"}


def parse_gui_crawl_sitemap(path: Path, base_url: str | None = None) -> list[str]:
    root = ET.parse(path).getroot()
    urls = (tc.get("name", "") for tc in root.iter("testcase") if tc.find("skipped") is None)
    return [_repoint_url(url, base_url) if base_url else url for url in urls if _is_valid_url(url)]


def _is_valid_url(url: str) -> bool:
    return url.startswith("http") and not any(url.endswith(ext) for ext in _EXTENSIONS_TO_IGNORE)


def _repoint_url(url: str, base_url: str) -> str:
    parsed = urlparse(url)

    parts = parsed.path.split("/", 2)
    remainder = "/" + parts[2] if len(parts) > 2 else "/"
    new_url = base_url.rstrip("/") + remainder

    if parsed.query:
        new_url += "?" + parsed.query

    return new_url
