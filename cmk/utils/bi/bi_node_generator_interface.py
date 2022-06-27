#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

#   .--NodeGen.------------------------------------------------------------.
#   |              _   _           _       ____                            |
#   |             | \ | | ___   __| | ___ / ___| ___ _ __                  |
#   |             |  \| |/ _ \ / _` |/ _ \ |  _ / _ \ '_ \                 |
#   |             | |\  | (_) | (_| |  __/ |_| |  __/ | | |_               |
#   |             |_| \_|\___/ \__,_|\___|\____|\___|_| |_(_)              |
#   |                                                                      |
#   +----------------------------------------------------------------------+

import abc
from typing import List, Optional

from cmk.utils.bi.bi_lib import (
    ABCBIAction,
    ABCBICompiledNode,
    ABCBISearch,
    ABCBISearcher,
    ABCWithSchema,
    bi_action_registry,
    bi_search_registry,
)
from cmk.utils.bi.type_defs import NodeDict
from cmk.utils.macros import MacroMapping


class ABCBINodeGenerator(ABCWithSchema):
    def __init__(self, node_config: NodeDict) -> None:
        super().__init__()
        self.search: ABCBISearch = bi_search_registry.instantiate(node_config["search"])
        self.action: ABCBIAction = bi_action_registry.instantiate(node_config["action"])

        # Enables the generator only to process rules with the given title
        # Can be used to limit the compilation to a specific branch, e.g. "Aggr HostA"
        self.restrict_rule_title: Optional[str] = None

    @abc.abstractmethod
    def compile(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> List[ABCBICompiledNode]:
        raise NotImplementedError()
