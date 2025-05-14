#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
#
# This file is auto-generated via the cmk-shared-typing package.
# Do not edit manually.
#
# fmt: off


from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class AgentDownloadI18n:
    dialog_title: str
    dialog_message: str
    slide_in_title: str
    slide_in_button_title: str
    docs_button_title: str


@dataclass(kw_only=True)
class AgentDownload:
    url: str
    i18n: AgentDownloadI18n


@dataclass(kw_only=True)
class DialogWithSlideinTypeDefs:
    agent_download: Optional[AgentDownload] = None
