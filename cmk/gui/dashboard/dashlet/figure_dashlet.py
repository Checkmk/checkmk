#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="no-untyped-def"
# mypy: disable-error-code="type-arg"

import abc

from cmk.gui.dashboard.type_defs import DashletSize
from cmk.gui.figures import FigureResponseData
from cmk.gui.i18n import _
from cmk.gui.type_defs import SingleInfos
from cmk.gui.valuespec import Dictionary, DictionaryElements, MigrateNotUpdated

from .base import Dashlet, T

__all__ = ["ABCFigureDashlet"]


class ABCFigureDashlet(Dashlet[T], abc.ABC):
    """Base class for cmk_figures based graphs
    Only contains the dashlet spec, the data generation is handled in the
    DataGenerator classes, to split visualization and data
    """

    @classmethod
    def type_name(cls) -> str:
        return "figure_dashlet"

    @classmethod
    def sort_index(cls) -> int:
        return 95

    @classmethod
    def initial_size(cls) -> DashletSize:
        return (56, 40)

    def infos(self) -> SingleInfos:
        return ["host", "service"]

    @classmethod
    def single_infos(cls) -> SingleInfos:
        return []

    @classmethod
    def has_context(cls) -> bool:
        return True

    @property
    def instance_name(self) -> str:
        # Note: This introduces the restriction one graph type per dashlet
        return f"{self.type_name()}_{self._dashlet_id}"

    @classmethod
    def vs_parameters(cls) -> MigrateNotUpdated:
        return MigrateNotUpdated(
            valuespec=Dictionary(
                title=_("Properties"),
                render="form",
                optional_keys=cls._vs_optional_keys(),
                elements=cls._vs_elements(),
            ),
            migrate=cls._migrate_vs,
        )

    @staticmethod
    def _vs_optional_keys() -> bool | list[str]:
        return False

    @staticmethod
    def _migrate_vs(valuespec_result):
        if "svc_status_display" in valuespec_result:
            # now as code is shared between host and service (svc) dashlet,
            # the `svc_` prefix is removed.
            valuespec_result["status_display"] = valuespec_result.pop("svc_status_display")
        return valuespec_result

    @staticmethod
    def _vs_elements() -> DictionaryElements:
        return []

    @abc.abstractmethod
    def generate_response_data(self) -> FigureResponseData: ...
