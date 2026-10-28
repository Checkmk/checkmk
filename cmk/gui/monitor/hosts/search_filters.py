#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""Turn a global search spec (see ``cmk.gui.search.spec``) into the All hosts filter tree

Each clause of the spec becomes one condition on the top level of the tree, so the column filters
show it. Labels and tags are the exception: a column filter shows only one condition per field, so
their clauses become a single "all_of" condition per field, which filters the same.

The Folder column filters by folder title, while ``hf:`` names a folder path. A path is therefore
turned into the title of one of the folders it selects, and only if that title selects exactly
these folders too: ``hf:linux`` becomes "Linux servers" when that is the title of ``linux`` and no
other folder carries it. Otherwise the query is rejected rather than shown as a title that finds
more or fewer folders.
"""

from collections.abc import Callable, Mapping, Sequence

from cmk.gui.i18n import _
from cmk.gui.monitor.shared import (
    AndNode,
    FilterNode,
    FolderCondition,
    folders_below,
    folders_titled,
    LabelChoiceCondition,
    LabelField,
    NameChoiceCondition,
    StringCondition,
    StringField,
)
from cmk.gui.search.spec import (
    HostAddress,
    HostAlias,
    HostFolder,
    HostGroup,
    HostLabel,
    HostName,
    HostTag,
    prefix_of,
    PrefixedSearch,
    Term,
    UnsupportedSearchError,
)
from cmk.ruleset_matcher.tags import TagConfig

_MAX_TITLES_SHOWN = 5


def host_search_filter(
    spec: PrefixedSearch, tags: TagConfig, folders: Callable[[], Mapping[str, str]]
) -> FilterNode:
    """The All hosts filter tree for the spec

    A tag given without its group is resolved to its group via the tag config. A folder path is
    resolved to a folder title via ``folders``, Setup's folder titles by path, which are only asked
    for when the spec has a folder.

    Raises:
        UnsupportedSearchError: if All hosts can't filter on the spec.
    """
    # A label or tag field stands in for its condition, built once all its pairs are known.
    conditions: list[FilterNode | LabelField] = []
    pairs: dict[LabelField, dict[str, None]] = {}
    for clause in spec.clauses:
        match clause:
            case [HostLabel(key=key, value=value)]:
                field: LabelField = "labels"
                pair = key if value is None else f"{key}:{value}"
            case [HostTag(group=group, tag=tag)]:
                field = "tags"
                pair = f"{group or _tag_group(tag, tags)}:{tag}"
            case _:
                conditions.append(_condition(clause, folders))
                continue
        if field not in pairs:
            conditions.append(field)
        # A dict, as the page rejects a pair given twice, e.g. "hl:os:linux hl:os:linux".
        pairs.setdefault(field, {})[pair] = None

    nodes = [
        LabelChoiceCondition(type="condition", field=node, op="all_of", value=list(pairs[node]))
        if isinstance(node, str)
        else node
        for node in conditions
    ]
    return nodes[0] if len(nodes) == 1 else AndNode(type="and", children=nodes)


def _condition(clause: Sequence[Term], folders: Callable[[], Mapping[str, str]]) -> FilterNode:
    match clause:
        case [HostName(), *_]:
            return _contains("name", clause)
        case [HostAlias(), *_]:
            return _contains("alias", clause)
        case [HostAddress(), *_]:
            return _contains("address", clause)
        case [HostGroup(), *_]:
            return NameChoiceCondition(
                type="condition",
                field="groups",
                op="one_of",
                value=list(
                    dict.fromkeys(term.name for term in clause if isinstance(term, HostGroup))
                ),
            )
        case [HostFolder(), *_]:
            return FolderCondition(
                type="condition",
                field="folder",
                op="contains",
                value=_folder_title(
                    [term.path for term in clause if isinstance(term, HostFolder)], folders()
                ),
            )
        case _:
            raise UnsupportedSearchError(
                _(
                    "All hosts can only be searched by host name, alias, address, group, label,"
                    " tag and folder."
                ),
                reason=f"All hosts has no filter for {prefix_of(clause[0])}:",
            )


def _folder_title(paths: Sequence[str], titles: Mapping[str, str]) -> str:
    named = ", ".join(f'"{path}"' for path in paths)
    if not (wanted := folders_below(paths, titles)):
        raise UnsupportedSearchError(
            _("No folder matches %(paths)s.") % {"paths": named}, reason="unknown folder"
        )
    wanted_titles = [titles[path].lower() for path in wanted]
    candidates = (
        titles[path]
        for path in sorted(wanted, key=lambda path: len(titles[path]))
        if all(titles[path].lower() in other for other in wanted_titles)
    )
    for title in candidates:
        if folders_titled(title, titles) == wanted:
            return title
    shown = [titles[path] for path in wanted[:_MAX_TITLES_SHOWN]]
    if len(wanted) > _MAX_TITLES_SHOWN:
        shown.append("...")
    raise UnsupportedSearchError(
        _(
            "The folders matching %(paths)s (%(titles)s) cannot be shown as one folder title."
            " Please give a more specific folder path."
        )
        % {"paths": named, "titles": ", ".join(shown)},
        reason="folders without one title",
    )


def _tag_group(tag: str, tags: TagConfig) -> str:
    if tag.endswith("*"):
        raise UnsupportedSearchError(
            _('Please specify the tag group of "%(tag)s", e.g. "tg:criticality:%(tag)s".')
            % {"tag": tag},
            reason="tag prefix without group",
        )
    groups = [
        str(group.id)
        for group in tags.get_tag_groups()
        if any(grouped_tag.id == tag for grouped_tag in group.tags)
    ] + [str(aux_tag.id) for aux_tag in tags.get_aux_tags() if aux_tag.id == tag]
    if not groups:
        raise UnsupportedSearchError(
            _('Unknown host tag "%(tag)s".') % {"tag": tag}, reason="unknown tag"
        )
    if len(groups) > 1:
        raise UnsupportedSearchError(
            _(
                'The host tag "%(tag)s" is in several tag groups: %(groups)s. Please specify'
                ' one, e.g. "tg:%(group)s:%(tag)s".'
            )
            % {"tag": tag, "groups": ", ".join(groups), "group": groups[0]},
            reason="tag in several groups",
        )
    return groups[0]


def _contains(field: StringField, clause: Sequence[Term]) -> StringCondition:
    # The terms of a clause are or-ed. Unanchored, "a|b" matches the same as an "or" node, which
    # no column filter shows.
    patterns = [
        term.pattern for term in clause if isinstance(term, HostName | HostAlias | HostAddress)
    ]
    return StringCondition(type="condition", field=field, op="contains", value="|".join(patterns))
