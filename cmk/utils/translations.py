#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ipaddress
from collections.abc import Iterable
from typing import cast, Literal, NotRequired, TypedDict

from cmk.ccc.hostaddress import HostName

from cmk.utils.regex import regex
from cmk.utils.servicename import ServiceName


# This can probably improved further by making it total and removing the None,
# but that would need some tweaking of "interesting" code. :-/
class TranslationOptions(TypedDict, total=False):
    case: Literal["lower", "upper"] | None
    drop_domain: bool
    mapping: Iterable[tuple[str, str]]
    regex: Iterable[tuple[str, str]]


# Similar to TranslationOptions, but not the same. This aims to
# cover exactly the structure that is configured with the valuespec.
class TranslationOptionsSpec(TypedDict):
    case: Literal["lower", "upper"] | None
    drop_domain: NotRequired[bool]
    mapping: list[tuple[str, str]]
    regex: list[tuple[str, str]]


def translate_hostname(translation: TranslationOptions, hostname: str) -> HostName:
    return HostName(_translate(translation, hostname))


def translate_raw_host_name(translation: TranslationOptions, host_name: str) -> str:
    return _translate(translation, host_name)


def translate_service_description(
    translation: TranslationOptions, service_description: str
) -> ServiceName:
    if service_description.strip() in {
        "Check_MK",
        "Check_MK Agent",
        "Check_MK Discovery",
        "Check_MK inventory",
        "Check_MK HW/SW Inventory",
    }:
        return service_description.strip()
    return ServiceName(_translate(translation, service_description))


def _translate(translation: TranslationOptions, name: str) -> str:
    # 1. Case conversion
    caseconf = translation.get("case")
    if caseconf == "upper":
        name = name.upper()
    elif caseconf == "lower":
        name = name.lower()

    # 2. Drop domain part (not applied to IP addresses!)
    if translation.get("drop_domain"):
        try:
            ipaddress.ip_address(name)
        except ValueError:
            # Drop domain if "name " is not a valid IP address
            name = name.split(".", 1)[0]

    # 3. Multiple regular expression conversion
    r = translation.get("regex", [])
    # TODO: The corresponding ValueSpec should really be a Migrate
    translations = [cast(tuple[str, str], r)] if isinstance(r, tuple) else r

    for expr, subst in translations:
        if not expr.endswith("$"):
            expr += "$"
        rcomp = regex(expr)
        if mo := rcomp.match(name):
            name = subst
            for nr, text in enumerate(mo.groups("")):
                name = name.replace("\\%d" % (nr + 1), text)
            break

    # 4. Explicity mapping
    for from_name, to_name in translation.get("mapping", []):
        if from_name == name:
            name = to_name
            break

    return name.strip()
