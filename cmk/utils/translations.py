#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from typing import Dict, Text  # pylint: disable=unused-import
from cmk.utils.regex import regex
from cmk.utils.type_defs import ServiceName  # pylint: disable=unused-import

TranslationOptions = Dict  # TODO: Improve this type


def translate_hostname(translation, hostname):
    # type: (TranslationOptions, Text) -> Text
    return _translate(translation, hostname)


def translate_service_description(translation, service_description):
    # type: (TranslationOptions, ServiceName) -> ServiceName
    if service_description.strip() in \
        ["Check_MK", "Check_MK Agent",
         "Check_MK Discovery", "Check_MK inventory",
         "Check_MK HW/SW Inventory"]:
        return service_description.strip()
    return _translate(translation, service_description)


def _translate(translation, name):
    # type: (TranslationOptions, Text) -> Text
    # 1. Case conversion
    caseconf = translation.get("case")
    if caseconf == "upper":
        name = name.upper()
    elif caseconf == "lower":
        name = name.lower()

    # 2. Drop domain part (not applied to IP addresses!)
    if translation.get("drop_domain") and not name[0].isdigit():
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
