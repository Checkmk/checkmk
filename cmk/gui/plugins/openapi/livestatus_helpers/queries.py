# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import List

from cmk.gui.plugins.openapi.livestatus_helpers.base import BaseQuery
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import (
    And,
    NothingExpression,
    QueryExpression,
)
from cmk.gui.plugins.openapi.livestatus_helpers.types import Column, Table


class Query(BaseQuery):
    """A representation of a Livestatus query.

    This holds all necessary information to generate a valid livestatus query.

    Examples:

        >>> from cmk.gui.plugins.openapi.livestatus_helpers.expressions import Not

        First you have defined Tables, these can be found in the `tables` package.

        >>> class Hosts(Table):
        ...      __tablename__ = 'hosts'
        ...      name = Column('name', 'string', 'The host name')
        ...      parents = Column('parents', 'list', 'The hosts parents')

        >>> class Services(Table):
        ...      __tablename__ = 'services'
        ...      description = Column('description', 'string', 'Service description')
        ...      host_name = Column('host_name', 'string', 'The host name')

        Then you pass the columns and Filters to get a Query instance. Calling `compile` on it,
        will render the actual livestatus query as a string.

        >>> Query([Services.description, Services.host_name],
        ...       And(Services.host_name == "heute",
        ...           Services.description == "CPU")).compile()
        'GET services\\nColumns: description host_name\\nFilter: host_name = heute\\nFilter: \
description = CPU\\nAnd: 2'

        >>> Query([Services.description, Services.host_name],
        ...       And(Services.host_name == "heute",
        ...           Services.description == "CPU",
        ...           Not(Services.host_name.contains("morgen")))).compile()
        'GET services\\nColumns: description host_name\\nFilter: host_name = heute\\nFilter: \
description = CPU\\nFilter: host_name ~ morgen\\nNegate: 1\\nAnd: 3'

        >>> Query([Hosts.name],
        ...       Hosts.parents.empty()).compile()
        'GET hosts\\nColumns: name\\nFilter: parents = '

        >>> Query([Hosts.name],
        ...       Hosts.parents == []).compile()
        'GET hosts\\nColumns: name\\nFilter: parents = '

    """
    def __init__(self, columns: List[Column], filter_expr: QueryExpression = NothingExpression()):
        """A representation of a livestatus query.

        Args:
            columns:
                A list of `Column` instances, these have to be defined as properties on a
                `Table` class.

            filter_expr:
                A filter-expression. These can be created by comparing `Column` instances to
                something or comparing `LiteralExpression` instances to something.

        """
        self.columns = columns
        self.filter_expr = filter_expr
        tables = {column.table for column in columns}
        assert len(tables) == 1
        self.table: Table = tables.pop()

    def filter(self, filter_expr: QueryExpression) -> 'Query':
        """Apply additional filters to an existing query.

        This will return a new `Query` instance. The original one is left untouched."""
        return Query(self.columns, And(self.filter_expr, filter_expr))

    def __str__(self) -> str:
        return self.compile()

    def compile(self) -> str:
        _query = []
        column_names = ' '.join(column.name for column in self.columns)
        _query.append(("Columns", column_names))
        _query.extend(self.filter_expr.render())
        return '\n'.join([
            'GET %s' % self.table.__tablename__,
            *[': '.join(line) for line in _query],
        ])
