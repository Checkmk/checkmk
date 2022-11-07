#!/usr/bin/env python3
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from collections.abc import Iterable

from cmk.gui.painters.v0.base import Cell
from cmk.gui.sorter import Sorter
from cmk.gui.valuespec import ValueSpec


class DerivedColumnsSorter(Sorter):
    # TODO(ml): This really looks wrong.  `derived_columns` is most certainly
    #           on the wrong class (it should be on `Cell` or `Painter`, just
    #           look at the few places it is implemented) and without this new
    #           method, this class is just a regular `Sorter`.  We should get
    #           rid of this useless piece of code.
    """
    Can be used to transfer an additional parameter to the Sorter instance.

    To transport the additional parameter through the url and other places the
    parameter is added to the sorter name seperated by a colon.

    This mechanism is used by the Columns "Service: Metric History", "Service:
    Metric Forecast": Those columns can be sorted by "Sorting"-section in
    the "Edit View" only after you added the column to the columns list and
    saved the view, or by clicking on the column header in the view.

    It's also used by host custom attributes: Those can be sorted by the
    "Sorting"-section in the "Edit View" options independent of the column
    section.
    """

    # TODO: should somehow be harmonized. this is probably not possible as the
    # metric sorting options can not be serialized into a short/simple string,
    # this is why the uuid option was introduced. Now there are basically three
    # different ways to subselect sorting options:
    # * don't use subselect at all (see Inventory): simply put all the posible
    #   values with a prefix into the sorting list (drawback: long list)
    # * don't use explicit options for sorting (see Metrics): link between
    #   columns and sorting via uuid (drawback: have to display column to
    #   activate sorting)
    # * use explicit options for sorting (see Custom Attributes): Encode the
    #   choosen value in the name (possible because it's only a simple string
    #   instead of complex options as with the metrics) and append it to the
    #   name of the column (drawback: it's the third hack)

    @abc.abstractmethod
    def derived_columns(self, cells: Iterable[Cell], uuid: str | None) -> None:
        # TODO: rename uuid, as this is no longer restricted to uuids
        raise NotImplementedError()

    def get_parameters(self) -> ValueSpec | None:
        """
        If not None, this ValueSpec will be visible after selecting this Sorter
        in the section "Sorting" in the "Edit View" form
        """
        return None
