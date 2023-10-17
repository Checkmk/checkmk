#!/usr/bin/env python3
# Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import itertools
from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from typing import NewType, TypeAlias

__all__ = ["HostAddress", "Hosts", "HostName"]

HostAddress = NewType("HostAddress", str)
# Let us be honest here, we do not actually make a difference
# between HostAddress and HostName in our code.
HostName: TypeAlias = HostAddress


@dataclass(frozen=True)
class Hosts:
    hosts: Sequence[HostName]
    clusters: Sequence[HostName]
    shadow_hosts: Sequence[HostName]

    def duplicates(self, /, pred: Callable[[HostName], bool]) -> Iterable[HostName]:
        return (
            hn
            for hn, count in Counter(
                hn
                for hn in itertools.chain(self.hosts, self.clusters, self.shadow_hosts)
                if pred(hn)
            ).items()
            if count > 1
        )
