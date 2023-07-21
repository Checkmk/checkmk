#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import abc

from cmk.gui.valuespec import ValueSpec


class VisualInfo(abc.ABC):
    """Base class for all visual info classes"""

    @property
    @abc.abstractmethod
    def ident(self) -> str:
        """The identity of a visual type. One word, may contain alpha numeric characters"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title(self) -> str:
        """The human readable GUI title"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def title_plural(self) -> str:
        """The human readable GUI title for multiple items"""
        raise NotImplementedError()

    @property
    @abc.abstractmethod
    def single_spec(self) -> list[tuple[str, ValueSpec]]:
        """The key / valuespec pairs (choices) to identify a single row"""
        raise NotImplementedError()

    @property
    def multiple_site_filters(self) -> list[str]:
        """Returns a list of filter identifiers.

        When these filters are set, the site hint will not be added to urls
        which link to views using this datasource, because the resuling view
        should show the objects spread accross the sites"""
        return []

    @property
    def single_site(self) -> bool:
        """When there is one non single site info used by a visual
        don't add the site hint"""
        return True

    @property
    def sort_index(self) -> int:
        """Used for sorting when listing multiple infos. Lower is displayed first"""
        return 30
