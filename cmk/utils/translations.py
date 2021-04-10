#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict
import ipaddress

from six import ensure_str

from cmk.utils.encoding import ensure_str_with_fallback
from cmk.utils.regex import regex
from cmk.utils.type_defs import HostName, ServiceName

TranslationOptions = Dict  # TODO: Improve this type


def translate_hostname(translation: TranslationOptions, hostname: str) -> str:
    return _translate(translation, hostname)


def translate_service_description(translation: TranslationOptions,
                                  service_description: ServiceName) -> ServiceName:
    if service_description.strip() in \
        ["Check_MK", "Check_MK Agent",
         "Check_MK Discovery", "Check_MK inventory",
         "Check_MK HW/SW Inventory"]:
        return service_description.strip()
    return _translate(translation, service_description)


def translate_piggyback_host(
    backedhost: HostName,
    translation: TranslationOptions,
    *,
    encoding_fallback: str,
) -> HostName:
    # To make it possible to match umlauts we need to change the hostname
    # to a unicode string which can then be matched with regexes etc.
    # We assume the incoming name is correctly encoded in UTF-8
    decoded_backedhost = ensure_str_with_fallback(
        backedhost,
        encoding="utf-8",
        fallback=encoding_fallback,
    )
    return ensure_str(translate_hostname(translation, decoded_backedhost))


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
    if isinstance(translation.get("regex"), tuple):
        translations = [translation["regex"]]
    else:
        translations = translation.get("regex", [])

    for expr, subst in translations:
        if not expr.endswith('$'):
            expr += '$'
        rcomp = regex(expr)
        # re.RegexObject.sub() by hand to handle non-existing references
        mo = rcomp.match(name)
        if mo:
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
