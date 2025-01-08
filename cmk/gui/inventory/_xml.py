#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import xml.dom.minidom
from collections.abc import Mapping
from typing import Any

import dicttoxml  # type: ignore[import-untyped]


def dict_to_document(data: Mapping[str, Any]) -> xml.dom.minidom.Document:
    # TODO: swap out dicttoxml library with internal implementation.
    rendered_xml = dicttoxml.dicttoxml(data)
    return xml.dom.minidom.parseString(rendered_xml)
