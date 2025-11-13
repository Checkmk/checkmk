#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import urllib.parse
from collections.abc import Collection

import cmk.utils.regex


def is_allowed_url(
    url: str, cross_domain: bool = False, schemes: Collection[str] | None = None
) -> bool:
    """Check if url is allowed

    >>> is_allowed_url("http://checkmk.com/")
    False
    >>> is_allowed_url("http://checkmk.com/", cross_domain=True, schemes=["http", "https"])
    True
    >>> is_allowed_url("/checkmk/", cross_domain=True, schemes=["http", "https"])
    True
    >>> is_allowed_url("//checkmk.com/", cross_domain=True)
    True
    >>> is_allowed_url("/foobar")
    True
    >>> is_allowed_url("//user:password@domain/", cross_domain=True)
    True
    >>> is_allowed_url("javascript:alert(1)")
    False
    >>> is_allowed_url("javascript:alert(1)", cross_domain=True, schemes=["javascript"])
    True
    >>> is_allowed_url('someXSSAttempt?"><script>alert(1)</script>')
    False
    """

    try:
        parsed = urllib.parse.urlparse(url)
    except ValueError:
        return False

    if not cross_domain and parsed.netloc != "":
        return False

    if schemes is None and parsed.scheme != "":
        return False
    if schemes is not None and parsed.scheme and parsed.scheme not in schemes:
        return False

    urlchar_regex = cmk.utils.regex.regex(cmk.utils.regex.URL_CHAR_REGEX)
    for part in parsed:
        if not part:
            continue
        if not urlchar_regex.match(part):
            return False

    return True
