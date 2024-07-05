#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import ast
from collections.abc import Callable, Generator, Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple, Self, TypeVar

from cmk.utils.hostaddress import HostName
from cmk.utils.paths import autochecks_dir
from cmk.utils.rulesets.definition import RuleGroup

from cmk.checkengine.checking import CheckPluginName
from cmk.checkengine.discovery import AutocheckEntry, AutochecksStore
from cmk.checkengine.legacy import LegacyCheckParameters

from cmk.base.api.agent_based import register

from cmk.gui.watolib.rulesets import AllRulesets, Ruleset, RulesetCollection

from cmk.ccc import debug
from cmk.ccc.store import ObjectStore

REPLACED_CHECK_PLUGINS: dict[CheckPluginName, CheckPluginName] = {}

_ALL_REPLACED_CHECK_PLUGINS: Mapping[CheckPluginName, CheckPluginName] = {
    **REPLACED_CHECK_PLUGINS,
    **{
        old_name.create_management_name(): new_name.create_management_name()
        for old_name, new_name in REPLACED_CHECK_PLUGINS.items()
    },
}

TDiscoveredItemsTransforms = Mapping[CheckPluginName, Callable[[str | None], str | None]]

_EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS: TDiscoveredItemsTransforms = {}

_ALL_EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS: TDiscoveredItemsTransforms = {
    **_EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS,
    **{
        name.create_management_name(): transform
        for name, transform in _EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS.items()
    },
}

# some autocheck parameters need transformation even though there is no ruleset.
TDiscoveredParametersTransforms = Mapping[
    CheckPluginName,
    Callable[
        [Any],  # should be LegacyCheckParameters, but this makes writing transforms cumbersome ...
        Mapping[str, object],
    ],
]

_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS: TDiscoveredParametersTransforms = {}

_ALL_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS: TDiscoveredParametersTransforms = {
    **_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS,
    **{
        name.create_management_name(): transform
        for name, transform in _EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS.items()
    },
}


@dataclass(frozen=True)
class RewriteError:
    message: str
    host_name: HostName
    plugin: CheckPluginName | None = None


def rewrite_yielding_errors(*, write: bool) -> Iterable[RewriteError]:
    all_rulesets = AllRulesets.load_all_rulesets()
    for hostname in _autocheck_hosts():
        fixed_autochecks = yield from _get_fixed_autochecks(hostname, all_rulesets)
        if write:
            AutochecksStore(hostname).write(fixed_autochecks)


def _get_fixed_autochecks(
    host_name: HostName, all_rulesets: AllRulesets
) -> Generator[RewriteError, None, list[AutocheckEntry]]:
    try:
        autochecks = _AutochecksStoreV22(host_name).read()
    except Exception as exc:
        if debug.enabled():
            raise
        yield RewriteError(message=f"Failed to load autochecks: {exc}", host_name=host_name)
        return []

    fixed_autochecks: list[AutocheckEntry] = []
    for entry in autochecks:
        try:
            fixed_autochecks.append(_fix_entry(entry, all_rulesets, host_name))
        except Exception as exc:
            if debug.enabled():
                raise
            yield RewriteError(
                message=str(exc), host_name=host_name, plugin=entry.check_plugin_name
            )

    return fixed_autochecks


def _autocheck_hosts() -> Iterable[HostName]:
    for autocheck_file in Path(autochecks_dir).glob("*.mk"):
        yield HostName(autocheck_file.stem)


class _AutocheckEntryV22(NamedTuple):
    check_plugin_name: CheckPluginName
    item: str | None
    parameters: LegacyCheckParameters
    service_labels: Mapping[str, str]

    @staticmethod
    def _parse_parameters(parameters: object) -> LegacyCheckParameters:
        # Make sure it's a 'LegacyCheckParameters' (mainly done for mypy).
        if parameters is None or isinstance(parameters, (dict, tuple, list, str, int, bool)):
            return parameters
        # I have no idea what else it could be (LegacyCheckParameters is quite pointless).
        raise ValueError(f"Invalid autocheck: invalid parameters: {parameters!r}")

    @classmethod
    def load(cls, raw_dict: Mapping[str, Any]) -> Self:
        return cls(
            check_plugin_name=CheckPluginName(raw_dict["check_plugin_name"]),
            item=None if (raw_item := raw_dict["item"]) is None else str(raw_item),
            parameters=cls._parse_parameters(raw_dict["parameters"]),
            service_labels={str(n): str(v) for n, v in raw_dict["service_labels"].items()},
        )


class _AutochecksSerializerV22:
    @staticmethod
    def serialize(entries: Sequence[_AutocheckEntryV22]) -> bytes:
        raise NotImplementedError()

    @staticmethod
    def deserialize(raw: bytes) -> Sequence[_AutocheckEntryV22]:
        """Deserialize "old" autocheck entries, where the parameters might not be a dict.

        >>> _AutochecksSerializerV22.deserialize(
        ...     b"[{'check_plugin_name': 'mounts', 'item': '/', 'parameters': ['errors=remount-ro', 'relatime', 'rw'], 'service_labels': {}},]"
        ... )
        [_AutocheckEntryV22(check_plugin_name=CheckPluginName('mounts'), item='/', parameters=['errors=remount-ro', 'relatime', 'rw'], service_labels={})]
        """
        return [_AutocheckEntryV22.load(d) for d in ast.literal_eval(raw.decode("utf-8"))]


class _AutochecksStoreV22:
    def __init__(self, host_name: HostName) -> None:
        self._host_name = host_name
        self._store = ObjectStore(
            Path(autochecks_dir, f"{host_name}.mk"),
            serializer=_AutochecksSerializerV22(),
        )

    def read(self) -> Sequence[_AutocheckEntryV22]:
        return self._store.read_obj(default=[])


def _fix_entry(
    entry: _AutocheckEntryV22,
    all_rulesets: RulesetCollection,
    hostname: str,
) -> AutocheckEntry:
    """Change names of removed plugins to the new ones and transform parameters"""
    new_plugin_name = _ALL_REPLACED_CHECK_PLUGINS.get(
        entry.check_plugin_name, entry.check_plugin_name
    )

    explicit_item_transform = _ALL_EXPLICIT_DISCOVERED_ITEMS_TRANSFORMS.get(
        new_plugin_name, lambda x: x
    )
    explicit_parameters_transform = _ALL_EXPLICIT_DISCOVERED_PARAMETERS_TRANSFORMS.get(
        new_plugin_name, lambda x: x
    )

    return AutocheckEntry(
        check_plugin_name=new_plugin_name,
        item=explicit_item_transform(entry.item),
        parameters=_transformed_params(
            new_plugin_name or entry.check_plugin_name,
            explicit_parameters_transform(entry.parameters),
            all_rulesets,
            hostname,
        ),
        service_labels=entry.service_labels,
    )


T = TypeVar("T", bound=LegacyCheckParameters)


def _transformed_params(
    plugin_name: CheckPluginName,
    params: T,
    all_rulesets: RulesetCollection,
    host: str,
) -> Mapping[str, object]:
    if (ruleset := _get_ruleset(plugin_name, all_rulesets)) is None:
        if not params:
            return {}
        if isinstance(params, dict):
            return {str(k): v for k, v in params.items()}
        raise TypeError(
            f"Migration missing: {params=} for plug-in '{str(plugin_name)}' (expected type dict)"
        )

    try:
        new_params = _apply_rulesets_migration(params, ruleset, plugin_name)
        assert new_params or not params, "non-empty params vanished"
    except Exception as exc:
        raise ValueError(
            f"Migration failed: {params=} for plug-in '{str(plugin_name)}': {exc}"
        ) from exc

    return new_params


def _get_ruleset(
    plugin_name: CheckPluginName,
    all_rulesets: RulesetCollection,
) -> Ruleset | None:
    if (
        check_plugin := register.get_check_plugin(plugin_name)
    ) is None or check_plugin.check_ruleset_name is None:
        return None

    return all_rulesets.get_rulesets().get(
        RuleGroup.CheckgroupParameters(f"{check_plugin.check_ruleset_name}")
    )


def _apply_rulesets_migration(
    params: LegacyCheckParameters, ruleset: Ruleset, plugin_name: CheckPluginName
) -> Mapping[str, object]:
    new_params = ruleset.valuespec().transform_value(params) if params else {}

    if not (isinstance(new_params, dict) and all(isinstance(k, str) for k in new_params)):
        raise TypeError(
            f"Migration invalid: {new_params=} for '{str(plugin_name)}' (expected type dict)"
        )

    return new_params
