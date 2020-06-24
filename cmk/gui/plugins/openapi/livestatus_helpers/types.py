# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import abc
from typing import Literal

from cmk.gui.plugins.openapi.livestatus_helpers.expressions import (
    ScalarExpression,
    ListExpression,
)

LivestatusType = Literal["string", "int", "float", "list", "dict", "time", "blob"]


class Table(abc.ABC):
    """Baseclass of all livestatus tables.

    This class doesn't do much, it just acts as a container for `Column` instances.
    """

    @property
    @abc.abstractmethod
    def __tablename__(self):
        raise NotImplementedError("Please set __tablename__ to the name of the livestatus table")


class NoTable(Table):
    """Like a livestatus table, but not really.

    Can be used in place of an actual table, in order to not have to use `Optional` types when
    something is initialized only later.
    """
    @property
    def __tablename__(self):
        raise AttributeError("This table has no name.")

    def __bool__(self):
        return False


class Column:
    """A representation of a livestatus column.

    This holds the name and type and can be used in comparisons to emit instances of
    `BinaryExpression`.

    The use of the type information can certainly be improved, but the most basic decisions (list
    or scalar) is being done already.

    """

    # I decided to implement this as a Descriptor in order to be able to
    # reference the Table from an actual Column instance and also preserve
    # the ability to tab-complete in various editors.
    # This means that the references will only ever be available after a Column
    # has been accessed via an attribute on the Table class. In terms of
    # implementation-complexity this solution wins though.
    def __init__(
        self,
        name,
        col_type: LivestatusType,
        description,
    ):
        """A representation of a livestatus column.

        Args:
            name:
                The name of the column, as it is supposed to be adressed in livestatus. The
                attribute-name on the Table is not significant for query generation.

            col_type:
                One of livestatus' column types.

            description:
                The documentation for this column. The __doc__ attribute will be populated with
                this text.

        Examples:

            >>> class Hosts(Table):
            ...     __tablename__ = 'hosts'
            ...
            ...     name = Column('name', 'string', 'The host-name')

            >>> Hosts.name.table.__tablename__
            'hosts'

            >>> Hosts.name.contains('heute')
            Filter(name ~ heute)

        Returns:
            object:
        """
        self.name: str = name
        self.type: str = col_type
        self.expr = (ListExpression(name) if col_type == 'list' else ScalarExpression(name))
        self.table: Table = NoTable()

        self.__doc__ = description

    def __get__(self, obj, obj_type):
        # As we don't know on which Table this Column is located, we use
        # the descriptor protocol during attribute access to find out.
        if not self.table:
            self.table = obj_type

        return self

    def __eq__(self, other):
        return self.expr.__eq__(other)

    def __ne__(self, other):
        return self.expr.__ne__(other)

    def __lt__(self, other):
        return self.expr.__lt__(other)

    def __le__(self, other):
        return self.expr.__le__(other)

    def __gt__(self, other):
        return self.expr.__gt__(other)

    def __ge__(self, other):
        return self.expr.__ge__(other)

    def equals(self, other, ignore_case=False):
        return self.expr.equals(other, ignore_case=ignore_case)

    def contains(self, other, ignore_case=False):
        return self.expr.contains(other, ignore_case=ignore_case)

    def disparity(self, other, ignore_case=False):
        return self.expr.disparity(other, ignore_case=ignore_case)

    def empty(self):
        return self.expr.empty()
