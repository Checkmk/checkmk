#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Helper functions for dealing with Checkmk labels of all kind"""

import abc
from typing import Dict, Text, List  # pylint: disable=unused-import
from pathlib2 import Path  # pylint: disable=unused-import

import cmk.utils.paths
import cmk.utils.store
from cmk.utils.rulesets.ruleset_matcher import RulesetMatcher, RulesetMatchObject  # pylint: disable=unused-import


class LabelManager(object):
    """Helper class to manage access to the host and service labels"""
    def __init__(self, explicit_host_labels, host_label_rules, service_label_rules):
        # type: (Dict, List, List) -> None
        super(LabelManager, self).__init__()
        self._explicit_host_labels = explicit_host_labels
        self._host_label_rules = host_label_rules
        self._service_label_rules = service_label_rules

    def labels_of_host(self, ruleset_matcher, hostname):
        # type: (RulesetMatcher, str) -> Dict
        """Returns the effective set of host labels from all available sources

        1. Discovered labels
        2. Ruleset "Host labels"
        3. Explicit labels (via host/folder config)

        Last one wins.
        """
        labels = {}
        labels.update(self._discovered_labels_of_host(hostname))
        labels.update(self._ruleset_labels_of_host(ruleset_matcher, hostname))
        labels.update(self._explicit_host_labels.get(hostname, {}))
        return labels

    def label_sources_of_host(self, ruleset_matcher, hostname):
        # type: (RulesetMatcher, str) -> Dict[str, str]
        """Returns the effective set of host label keys with their source
        identifier instead of the value Order and merging logic is equal to
        _get_host_labels()"""
        labels = {}
        labels.update({k: "discovered" for k in self._discovered_labels_of_host(hostname).keys()})
        labels.update(
            {k: "ruleset" for k in self._ruleset_labels_of_host(ruleset_matcher, hostname)})
        labels.update({k: "explicit" for k in self._explicit_host_labels.get(hostname, {}).keys()})
        return labels

    def _ruleset_labels_of_host(self, ruleset_matcher, hostname):
        # type: (RulesetMatcher, str) -> Dict
        match_object = RulesetMatchObject(hostname, service_description=None)
        return ruleset_matcher.get_host_ruleset_merged_dict(match_object, self._host_label_rules)

    def _discovered_labels_of_host(self, hostname):
        # type: (str) -> Dict
        return DiscoveredHostLabelsStore(hostname).load()

    def labels_of_service(self, ruleset_matcher, hostname, service_desc):
        # type: (RulesetMatcher, str, Text) -> Dict
        """Returns the effective set of service labels from all available sources

        1. Discovered labels
        2. Ruleset "Host labels"

        Last one wins.
        """
        labels = {}
        labels.update(self._discovered_labels_of_service(hostname, service_desc))
        labels.update(self._ruleset_labels_of_service(ruleset_matcher, hostname, service_desc))

        return labels

    def label_sources_of_service(self, ruleset_matcher, hostname, service_desc):
        # type: (RulesetMatcher, str, Text) -> Dict[str, str]
        """Returns the effective set of host label keys with their source
        identifier instead of the value Order and merging logic is equal to
        _get_host_labels()"""
        labels = {}
        labels.update(
            {k: "discovered" for k in self._discovered_labels_of_service(hostname, service_desc)})
        labels.update({
            k: "ruleset"
            for k in self._ruleset_labels_of_service(ruleset_matcher, hostname, service_desc)
        })

        return labels

    def _ruleset_labels_of_service(self, ruleset_matcher, hostname, service_desc):
        # type: (RulesetMatcher, str, Text) -> Dict
        match_object = RulesetMatchObject(hostname, service_description=service_desc)
        return ruleset_matcher.get_host_ruleset_merged_dict(match_object, self._service_label_rules)

    def _discovered_labels_of_service(self, hostname, service_desc):
        # type: (str, Text) -> Dict
        # TODO: Bad things here:
        # - Uncached and unoptimized processing of autochecks
        # - import of cmk_base in cmk.utils -> Module scope violation
        import cmk_base.autochecks as autochecks
        for service in autochecks.read_autochecks_of(hostname):
            if service.description == service_desc:
                return service.service_labels.to_dict()
        return {}


class ABCDiscoveredLabelsStore(object):
    """Managing persistance of discovered labels"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractproperty
    def file_path(self):
        # type () -> Path
        raise NotImplementedError()

    def load(self):
        # type: () -> Dict
        return cmk.utils.store.load_data_from_file(str(self.file_path), default={})

    def save(self, labels):
        # type: (Dict) -> None
        if not labels:
            if self.file_path.exists():
                self.file_path.unlink()
            return

        self.file_path.parent.mkdir(parents=True, exist_ok=True)  # pylint: disable=no-member
        cmk.utils.store.save_data_to_file(str(self.file_path), labels)


class DiscoveredHostLabelsStore(ABCDiscoveredLabelsStore):
    def __init__(self, hostname):
        # type: (str) -> None
        super(DiscoveredHostLabelsStore, self).__init__()
        self._hostname = hostname

    @property
    def file_path(self):
        # type () -> Path
        return (cmk.utils.paths.discovered_host_labels_dir / self._hostname).with_suffix(".mk")
