#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
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

from abc import abstractmethod

from cmk.utils.macros import MacroMapping

from cmk.bi.lib import (
    ABCBIAction,
    ABCBICompiledNode,
    ABCBISearch,
    ABCBISearcher,
    ABCWithSchema,
    bi_action_registry,
    bi_search_registry,
)
from cmk.bi.type_defs import NodeDict


class ABCBINodeGenerator(ABCWithSchema):
    def __init__(self, node_config: NodeDict) -> None:
        super().__init__()
        self.search: ABCBISearch = bi_search_registry.instantiate(node_config["search"])
        self.action: ABCBIAction = bi_action_registry.instantiate(node_config["action"])

        # Enables the generator only to process rules with the given title
        # Can be used to limit the compilation to a specific branch, e.g. "Aggr HostA"
        self.restrict_rule_title: str | None = None

    @abstractmethod
    def compile(self, macros: MacroMapping, bi_searcher: ABCBISearcher) -> list[ABCBICompiledNode]:
        raise NotImplementedError()
