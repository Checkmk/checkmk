#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
"""Helper functions for dealing with Checkmk labels of all kind"""

import os
from ast import literal_eval
from typing import Callable, Dict, Final, List, Mapping, Tuple

import cmk.utils.paths
import cmk.utils.store as store
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, RulesetMatchObject
from cmk.utils.site import omd_site
from cmk.utils.type_defs import HostLabelValueDict, HostName, Labels, LabelSources, ServiceName

UpdatedHostLabelsEntry = Tuple[str, float, str]


class LabelManager:
    """Helper class to manage access to the host and service labels"""

    def __init__(
        self,
        explicit_host_labels: Dict,
        host_label_rules: List,
        service_label_rules: List,
        discovered_labels_of_service: Callable[[HostName, ServiceName], Labels],
    ) -> None:
        super().__init__()
        self._explicit_host_labels = explicit_host_labels
        self._host_label_rules = host_label_rules
        self._service_label_rules = service_label_rules
        self._discovered_labels_of_service = discovered_labels_of_service

    def labels_of_host(self, ruleset_matcher: RulesetMatcher, hostname: HostName) -> Labels:
        """Returns the effective set of host labels from all available sources

        1. Discovered labels
        2. Ruleset "Host labels"
        3. Explicit labels (via host/folder config)
        4. Builtin labels

        Last one wins.
        """
        labels: Dict[str, str] = {}
        labels.update(self._discovered_labels_of_host(hostname))
        labels.update(self._ruleset_labels_of_host(ruleset_matcher, hostname))
        labels.update(self._explicit_host_labels.get(hostname, {}))
        labels.update(self._builtin_labels_of_host(hostname))
        return labels

    def label_sources_of_host(
        self, ruleset_matcher: RulesetMatcher, hostname: HostName
    ) -> LabelSources:
        """Returns the effective set of host label keys with their source
        identifier instead of the value Order and merging logic is equal to
        _get_host_labels()"""
        labels: LabelSources = {}
        labels.update({k: "discovered" for k in self._discovered_labels_of_host(hostname).keys()})
        labels.update({k: "discovered" for k in self._builtin_labels_of_host(hostname)})
        labels.update(
            {k: "ruleset" for k in self._ruleset_labels_of_host(ruleset_matcher, hostname)}
        )
        labels.update({k: "explicit" for k in self._explicit_host_labels.get(hostname, {}).keys()})
        return labels

    def _ruleset_labels_of_host(
        self, ruleset_matcher: RulesetMatcher, hostname: HostName
    ) -> Labels:
        match_object = RulesetMatchObject(hostname, service_description=None)
        return ruleset_matcher.get_host_ruleset_merged_dict(match_object, self._host_label_rules)

    def _discovered_labels_of_host(self, hostname: HostName) -> Labels:
        return {
            label_id: label["value"]
            for label_id, label in DiscoveredHostLabelsStore(hostname).load().items()
        }

    def _builtin_labels_of_host(self, hostname: HostName) -> Labels:
        return {
            label_id: label["value"] for label_id, label in BuiltinHostLabelsStore().load().items()
        }

    def labels_of_service(
        self, ruleset_matcher: RulesetMatcher, hostname: HostName, service_desc: ServiceName
    ) -> Labels:
        """Returns the effective set of service labels from all available sources

        1. Discovered labels
        2. Ruleset "Host labels"

        Last one wins.
        """
        labels: Dict[str, str] = {}
        labels.update(self._discovered_labels_of_service(hostname, service_desc))
        labels.update(self._ruleset_labels_of_service(ruleset_matcher, hostname, service_desc))

        return labels

    def label_sources_of_service(
        self, ruleset_matcher: RulesetMatcher, hostname: HostName, service_desc: ServiceName
    ) -> LabelSources:
        """Returns the effective set of host label keys with their source
        identifier instead of the value Order and merging logic is equal to
        _get_host_labels()"""
        labels: LabelSources = {}
        labels.update(
            {k: "discovered" for k in self._discovered_labels_of_service(hostname, service_desc)}
        )
        labels.update(
            {
                k: "ruleset"
                for k in self._ruleset_labels_of_service(ruleset_matcher, hostname, service_desc)
            }
        )

        return labels

    def _ruleset_labels_of_service(
        self, ruleset_matcher: RulesetMatcher, hostname: HostName, service_desc: ServiceName
    ) -> Labels:
        match_object = RulesetMatchObject(hostname, service_description=service_desc)
        return ruleset_matcher.get_service_ruleset_merged_dict(
            match_object, self._service_label_rules
        )


class LabelsSerializer:
    def serialize(self, data: Mapping[str, HostLabelValueDict]) -> bytes:
        return repr(data).encode("utf-8")

    @staticmethod
    def deserialize(raw: bytes) -> Mapping[str, HostLabelValueDict]:
        # Skip labels discovered by the previous HW/SW inventory approach
        # (which was addded+removed in 1.6 beta)
        return {
            str(key): {
                "value": str(val["value"]),
                "plugin_name": str(val["plugin_name"]) if "plugin_name" in val else None,
            }
            for key, val in literal_eval(raw.decode("utf-8")).items()
            if isinstance(val, dict)
        }


class DiscoveredHostLabelsStore:
    """Managing persistence of discovered labels"""

    def __init__(self, hostname: HostName) -> None:
        super().__init__()
        self._store = store.ObjectStore(
            path=cmk.utils.paths.discovered_host_labels_dir / f"{hostname}.mk",
            serializer=LabelsSerializer(),
        )
        self.file_path: Final = self._store.path

    def load(self) -> Mapping[str, HostLabelValueDict]:
        return self._store.read_obj(default={})

    def save(self, labels: Mapping[str, HostLabelValueDict]) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._store.write_obj(labels)


class BuiltinHostLabelsStore:
    def load(self) -> Mapping[str, HostLabelValueDict]:
        return {
            "cmk/site": {"value": omd_site(), "plugin_name": "builtin"},
        }


def get_host_labels_entry_of_host(host_name: HostName) -> UpdatedHostLabelsEntry:
    """Returns the host labels entry of the given host"""
    path = DiscoveredHostLabelsStore(host_name).file_path
    with path.open() as f:
        return (path.name, path.stat().st_mtime, f.read())


def get_updated_host_label_files(newer_than: float) -> List[UpdatedHostLabelsEntry]:
    """Returns the host label file content + meta data which are newer than the given timestamp"""
    updated_host_labels = []
    for path in sorted(cmk.utils.paths.discovered_host_labels_dir.glob("*.mk")):
        mtime = path.stat().st_mtime
        if path.stat().st_mtime <= newer_than:
            continue  # Already known to central site

        with path.open() as f:
            updated_host_labels.append((path.name, mtime, f.read()))
    return updated_host_labels


def save_updated_host_label_files(updated_host_labels: List[UpdatedHostLabelsEntry]) -> None:
    """Persists the data previously read by get_updated_host_label_files()"""
    for file_name, mtime, content in updated_host_labels:
        file_path = cmk.utils.paths.discovered_host_labels_dir / file_name
        store.save_text_to_file(file_path, content)
        os.utime(file_path, (mtime, mtime))
