#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import dataclasses
from collections.abc import Callable, Sequence
from typing import Protocol

from cmk.ccc.site import SiteId


class _SiteCondition(Protocol):
    @property
    def value(self) -> Sequence[SiteId]: ...


class _JunctionNode[N](Protocol):
    @property
    def children(self) -> Sequence[N]: ...


class _NotNode[N](Protocol):
    @property
    def child(self) -> N: ...


@dataclasses.dataclass(frozen=True, kw_only=True)
class SiteScopedFilter[N]:
    node: N | None
    sites: frozenset[SiteId] | None
    exclude_sites: bool

    def site_scope(self, all_site_ids: frozenset[SiteId]) -> list[SiteId] | None:
        """The sites to query, or `None` for every site.

        Named sites are kept even if not in `all_site_ids`; excluded ones are taken from it.
        """
        if self.sites is None:
            return None
        return list(all_site_ids - self.sites if self.exclude_sites else self.sites)


@dataclasses.dataclass(frozen=True, kw_only=True)
class SiteScopeExtractor[N]:
    """Split off a filter tree's 'site_id' condition, if any, as a site scope restriction.

    Site ID isn't a real Livestatus column, so it can't contribute a filter line; it's pushed
    down into which sites get queried instead. Only a single 'site_id' condition is supported,
    optionally wrapped with a 'not' condition. If a site condition is combined with the rest of
    the tree with anything but an 'and' condition, a `ValueError` is raised.

    Additional details:

    - Combining it with an unrelated condition via 'or' would need rows from every other site
      too (e.g. "site A's hosts OR any DOWN host"), which can't be reduced to a site restriction.
    - Negating a mixed (site + non-site) subtree hits the same problem:
      NOT(site_id=A AND cond) = (site_id!=A OR NOT cond), which turns the 'and' into an 'or'.
      So a 'not' passes through unchanged unless a 'site_id' condition turns up further inside,
      which is rejected.
    - An 'or' can never be reduced to a site restriction, so any 'site_id' condition anywhere
      inside it is rejected; nothing is ever extracted there.
    - The only one site condition is done to constrain the current parsing logic. This constraint
      can be lifted when the need arises, but will come with added complexity.

    Each page family has its own filter tree, so it names the node types of its tree here.
    """

    site_condition: type[_SiteCondition]
    and_node: type[_JunctionNode[N]]
    or_node: type[_JunctionNode[N]]
    not_node: type[_NotNode[N]]
    make_and: Callable[[list[N]], N]

    def scope(self, node: N) -> SiteScopedFilter[N]:
        found: list[tuple[_SiteCondition, bool]] = []
        residual = self._walk(node, found, and_only=True)

        if not found:
            return SiteScopedFilter(node=residual, sites=None, exclude_sites=False)

        condition, negated = found[0]
        return SiteScopedFilter(
            node=residual, sites=frozenset(condition.value), exclude_sites=negated
        )

    def _walk(
        self, node: N, found: list[tuple[_SiteCondition, bool]], *, and_only: bool
    ) -> N | None:
        if isinstance(node, self.site_condition):
            self._record(node, found, negated=False, and_only=and_only)
            return None

        if isinstance(node, self.and_node):
            residual_children = [
                residual
                for residual in (
                    self._walk(child, found, and_only=and_only) for child in node.children
                )
                if residual is not None
            ]
            match residual_children:
                case []:
                    return None
                case [single]:
                    return single
                case _:
                    return self.make_and(residual_children)

        if isinstance(node, self.not_node) and isinstance(node.child, self.site_condition):
            self._record(node.child, found, negated=True, and_only=and_only)
            return None

        if isinstance(node, self.not_node):
            self._walk(node.child, found, and_only=False)
        elif isinstance(node, self.or_node):
            for child in node.children:
                self._walk(child, found, and_only=False)

        return node

    @staticmethod
    def _record(
        condition: _SiteCondition,
        found: list[tuple[_SiteCondition, bool]],
        *,
        negated: bool,
        and_only: bool,
    ) -> None:
        if not and_only:
            raise ValueError(
                "'site_id' conditions may only be combined via 'and'; they cannot appear "
                "inside 'or', or inside 'not' together with other conditions."
            )
        if found:
            raise ValueError("Only one 'site_id' condition is allowed per filter.")
        found.append((condition, negated))
