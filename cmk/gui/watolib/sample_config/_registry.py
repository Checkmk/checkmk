#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc
from typing import override

import cmk.ccc.plugin_registry
from cmk.gui.watolib.hosts_and_folders import FolderTree


class SampleConfigGenerator(abc.ABC):
    @classmethod
    def ident(cls) -> str:
        """Unique key which can be used to identify a generator"""
        raise NotImplementedError

    # TODO: @abc.abstractmethod
    @classmethod
    def sort_index(cls) -> int:
        """The generators are executed in this order (low to high)"""
        raise NotImplementedError

    @abc.abstractmethod
    def generate(self, tree: FolderTree) -> None:
        """Execute the sample configuration creation step"""
        raise NotImplementedError


class SampleConfigGeneratorRegistry(cmk.ccc.plugin_registry.Registry[type[SampleConfigGenerator]]):
    @override
    def plugin_name(self, instance: type[SampleConfigGenerator]) -> str:
        return instance.ident()

    def get_generators(self) -> list[SampleConfigGenerator]:
        """Return the generators in the order they are expected to be executed"""
        return sorted([g_class() for g_class in self.values()], key=lambda e: e.sort_index())


sample_config_generator_registry = SampleConfigGeneratorRegistry()
