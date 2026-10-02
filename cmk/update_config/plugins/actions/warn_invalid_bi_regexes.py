#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import re
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from logging import Logger
from typing import Final, override

from cmk.ccc import store
from cmk.gui.config import active_config
from cmk.gui.site_config import is_distributed_setup_remote_site
from cmk.update_config.lib import ExpiryVersion, format_warning
from cmk.update_config.registry import update_action_registry, UpdateAction
from cmk.utils.paths import default_config_dir

_REGEX_FIELDS: Final = frozenset(
    {"host_regex", "service_regex", "host_name_regex", "host_alias_regex"}
)


@dataclass(frozen=True)
class InvalidBIRegex:
    pack_id: str
    element: str
    field: str
    pattern: str
    error: str


def _regex_error(pattern: str) -> str | None:
    try:
        re.compile(pattern)
    except re.error as e:
        return str(e)
    return None


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> Sequence[object]:
    return value if isinstance(value, list) else []


def _node_patterns(node: object) -> list[tuple[str, str]]:
    conditions = _mapping(_mapping(_mapping(node).get("search")).get("conditions"))
    host_choice = _mapping(conditions.get("host_choice"))
    return [
        (field, value)
        for source in (
            _mapping(_mapping(node).get("action")),
            conditions,
            {str(host_choice.get("type")): host_choice.get("pattern")},
        )
        for field, value in source.items()
        if field in _REGEX_FIELDS and isinstance(value, str)
    ]


def invalid_bi_regexes(packs: Iterable[object]) -> list[InvalidBIRegex]:
    return [
        InvalidBIRegex(str(pack.get("id")), element, field, pattern, error)
        for pack in map(_mapping, packs)
        for element, nodes in [
            *(
                (f"rule '{rule.get('id')}'", _list(rule.get("nodes")))
                for rule in map(_mapping, _list(pack.get("rules")))
            ),
            *(
                (f"aggregation '{aggr.get('id')}'", [aggr.get("node")])
                for aggr in map(_mapping, _list(pack.get("aggregations")))
            ),
        ]
        for node in nodes
        for field, pattern in _node_patterns(node)
        if (error := _regex_error(pattern)) is not None
    ]


def warn_invalid_bi_regexes(packs: Iterable[object], logger: Logger) -> None:
    for hit in invalid_bi_regexes(packs):
        logger.warning(
            format_warning(
                f"BI pack '{hit.pack_id}', {hit.element}: invalid regular expression "
                f"'{hit.pattern}' in '{hit.field}' ({hit.error}). The affected node stays "
                "empty, and Setup refuses to save it until the pattern is fixed."
            )
        )


class WarnInvalidBIRegexes(UpdateAction):
    @override
    def __call__(self, logger: Logger) -> None:
        if is_distributed_setup_remote_site(active_config.sites):
            return
        config = store.load_object_from_file(
            default_config_dir / "multisite.d/wato/bi_config.bi", default=None
        )
        warn_invalid_bi_regexes(_list(_mapping(config).get("packs")), logger)


update_action_registry.register(
    WarnInvalidBIRegexes(
        name="warn_invalid_bi_regexes",
        title="Checking BI rules and aggregations for invalid regular expressions",
        sort_index=100,  # pure read-only check, no ordering constraints
        expiry_version=ExpiryVersion.CMK_260,
    )
)
