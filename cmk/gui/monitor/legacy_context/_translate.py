#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Translate the filter context of the legacy visuals into the filter tree of a monitoring page.

A filter context is a ``VisualContext`` as the legacy views and the dashboards keep it. Each page
maps the legacy filters of the catalog it can express to the page field they target. The legacy
filters produce the pages' wire format, which the page then validates with its own filter model,
together with what was translated before: a field, an operator or a combination the page does not
accept is reported like any other filter without an equivalent.

A filter that is set but cannot be applied is reported instead of dropped, so that a caller never
shows more objects than the user asked for without knowing it.
"""

from collections.abc import Callable, Mapping, Sequence, Set
from dataclasses import dataclass

from pydantic import TypeAdapter

from cmk.gui.type_defs import FilterHTTPVariables, FilterName, VisualContext

from ._catalog import legacy_filters, SITE_FILTERS
from ._filters import (
    all_of,
    FilterJSON,
    IGNORED_TRISTATE,
    LegacyFilter,
    MultiFieldFilter,
    PageField,
    UntranslatableFilterError,
)


@dataclass(frozen=True)
class ContextFilterTranslation[F]:
    filter: F | None
    unapplied: Sequence[FilterName]


@dataclass(frozen=True)
class PageFilterModel[N, F]:
    """The filter model of a page: the tree it accepts, and ``check``, which turns the tree into
    the filter the page queries with and raises a ``ValueError`` for a tree the page cannot use,
    e.g. one with more than one site condition."""

    tree: TypeAdapter[N]
    check: Callable[[N], F]

    def validate(self, node: FilterJSON) -> F:
        try:
            return self.check(self.tree.validate_python(node))
        # A pydantic ValidationError is a ValueError, too.
        except ValueError as exc:
            raise UntranslatableFilterError from exc


def translate_context[N, F](
    context: VisualContext,
    fields: Mapping[FilterName, PageField],
    page: PageFilterModel[N, F],
    *,
    tag_groups: Set[str] = frozenset(),
) -> ContextFilterTranslation[F]:
    """Translate the legacy filters in ``fields`` to conditions on the page field each is mapped
    to, in the order of ``fields``: where the page cannot take two filters together, the one
    listed first is applied. A filter that spans several fields is mapped to the field of each of
    its roles. Raises a ``ValueError`` for a filter missing from the catalog, or mapped to fields
    that do not fit it. ``tag_groups`` are the IDs of the configured tag groups, which the filter
    for tags needs."""
    catalog = legacy_filters(tag_groups=tag_groups)
    if unknown := fields.keys() - catalog.keys():
        raise ValueError(f"Not in the catalog of legacy filters: {sorted(unknown)}")
    for name, field in fields.items():
        # Fields that do not fit their filter raise, whether or not the context sets it. A filter
        # that is not set restricts nothing, so this does not translate anything.
        _translate_filter(catalog[name], {}, field)
    nodes: list[FilterJSON] = []
    page_filter: F | None = None
    # Like the legacy views, only the first site filter that restricts the sites applies. If the
    # page does not map it, it is reported, and still keeps the others from querying sites the
    # user did not pick.
    site_filters = _site_filters(context)
    applied_site_filter = next(iter(site_filters), None)
    unapplied = {
        name
        for name, value in context.items()
        if name not in fields and name not in SITE_FILTERS and _restricts(catalog, name, value)
    }
    if applied_site_filter is not None and applied_site_filter not in fields:
        unapplied.add(applied_site_filter)
    for name, field in fields.items():
        if name in SITE_FILTERS and name != applied_site_filter:
            continue
        try:
            node = _translate_filter(catalog[name], context.get(name, {}), field)
            if node is None:
                continue
            candidate = [*nodes, node]
            tree = all_of(candidate)
            assert tree is not None
            candidate_filter = page.validate(tree)
        except UntranslatableFilterError:
            unapplied.add(name)
            continue
        nodes, page_filter = candidate, candidate_filter

    # The other site filters are reported, unless they name every site that is queried: applying
    # them as well would not change the result.
    applied_sites = (
        None
        if applied_site_filter is None or applied_site_filter in unapplied
        else site_filters[applied_site_filter]
    )
    unapplied.update(
        name
        for name, sites in list(site_filters.items())[1:]
        if applied_sites is None or sites is None or not applied_sites <= sites
    )

    return ContextFilterTranslation(
        filter=page_filter,
        unapplied=[name for name in context if name in unapplied],
    )


def _site_filters(context: VisualContext) -> dict[FilterName, frozenset[str] | None]:
    """The site filters that restrict the sites, in the order in which they apply, with the sites
    they name, or None if they name a site ID no page can take."""
    site_filters: dict[FilterName, frozenset[str] | None] = {}
    for name, ids in SITE_FILTERS.items():
        try:
            sites = ids(context.get(name, {}))
        except UntranslatableFilterError:
            # It names sites, just none a page can take: it is reported, not passed over.
            site_filters[name] = None
            continue
        if sites:
            site_filters[name] = frozenset(sites)
    return site_filters


def _translate_filter(
    legacy_filter: LegacyFilter | MultiFieldFilter, value: FilterHTTPVariables, field: PageField
) -> FilterJSON | None:
    """The condition the variables of a legacy filter mean on the field of the page, or the field
    of each of its roles. Raises a ``ValueError`` for fields that do not fit the filter."""
    if isinstance(legacy_filter, MultiFieldFilter):
        if isinstance(field, str) or field.keys() != legacy_filter.roles:
            raise ValueError(
                f"Expected the page fields of the roles {sorted(legacy_filter.roles)}, got {field!r}"
            )
        return legacy_filter.translate(value, field)
    if not isinstance(field, str):
        raise ValueError(f"Expected a single page field, got {field!r}")
    return legacy_filter(value, field)


def _restricts(
    catalog: Mapping[FilterName, LegacyFilter | MultiFieldFilter],
    name: FilterName,
    value: FilterHTTPVariables,
) -> bool:
    """Whether a filter the page does not map restricts anything, i.e. has to be reported."""
    if (legacy_filter := catalog.get(name)) is None:
        # Its kind is unknown, so "-1" is taken for an ignored tri-state flag.
        return any(text and text != IGNORED_TRISTATE for text in value.values())
    try:
        # Whether it restricts anything does not depend on the fields it would be mapped to.
        if isinstance(legacy_filter, MultiFieldFilter):
            no_fields = dict.fromkeys(legacy_filter.roles, "")
            return legacy_filter.translate(value, no_fields) is not None
        return legacy_filter(value, "") is not None
    except UntranslatableFilterError:
        return True
