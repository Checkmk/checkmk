#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from typing import Any, Dict, Generator, List, Optional

from cmk.gui.plugins.openapi.livestatus_helpers.base import BaseQuery
from cmk.gui.plugins.openapi.livestatus_helpers.expressions import (
    And,
    NothingExpression,
    QueryExpression,
)
from cmk.gui.plugins.openapi.livestatus_helpers.types import Column, Table


class ResultRow(dict):
    """This one collects heterogenous data.

    We only accept str-keys as the names of our columns are str as well. Answers must be Any
    because the values can be anything that LiveStatus will emit. Strings, Numbers, Lists,
    you name it.

    Sadly the values can't really be checked by mypy, but this won't be possible with dict-lookups
    as well.

    >>> from typing import Dict
    >>> result: Dict[str, Any] = {'a': 'b', 'b': 5, 'c': [1, 2, 3]}
    >>> d = ResultRow(result)
    >>> str_value = d.a  # is of type Any
    >>> str_value
    'b'

    >>> int_value = d.b  # is of type Any
    >>> int_value
    5

    >>> list_value = d.c  # is of type Any
    >>> list_value
    [1, 2, 3]

    >>> row = ResultRow(list(zip(['a', 'b', 'c'], ['1', 2, [3.0]])))
    >>> dict(row)
    {'a': '1', 'b': 2, 'c': [3.0]}

    The right exception type will be raised on missing keys:

        >>> row.foo
        Traceback (most recent call last):
        ...
        AttributeError: 'foo'

        >>> row['foo']
        Traceback (most recent call last):
        ...
        KeyError: 'foo'

    And because programmers sometimes have "creative" ideas:

        >>> row.foo = 'bar'
        Traceback (most recent call last):
        ...
        AttributeError: foo: Setting of attributes not allowed.

        >>> row['foo'] = 'bar'
        Traceback (most recent call last):
        ...
        KeyError: 'foo: Setting of keys not allowed.'

    """
    def __getattr__(self, item: str) -> Any:
        try:
            return self[item]
        except KeyError as exc:
            raise AttributeError(str(exc))

    def __setitem__(self, key, value):
        raise KeyError(f"{key}: Setting of keys not allowed.")

    def __setattr__(self, key, value):
        raise AttributeError(f"{key}: Setting of attributes not allowed.")


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

        >>> q = Query([Hosts.name, Hosts.name.label('id')],
        ...       Hosts.parents == [])

        >>> q.compile()
        'GET hosts\\nColumns: name name\\nFilter: parents = '

        >>> q.column_names
        ['name', 'id']

        >>> id(Hosts.name) == id(Hosts.name.label('id'))
        False

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
        self.column_names = [col.query_name for col in columns]
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

    def first(self, sites) -> Optional[ResultRow]:
        """Fetch the first row of the result.

        If the result is empty, `None` will be returned.

        Args:
            sites:
                A LiveStatus-connection object.

        Returns:
            Optionally a ResultRow

        """
        return next(self.iterate(sites), None)

    def fetchone(self, sites) -> ResultRow:
        """Fetch one row of the result.

        If the result from livestatus is more or less than exactly one row long it
        will throw an Exception.

        Args:
            sites:

        Returns:
            One ResultRow entry.

        Raises:
            ValueError: When the row-count is not equal to 1.

        """
        result = list(self.iterate(sites))
        if len(result) != 1:
            raise ValueError(f"Expected one row, got {len(result)} row.")
        return result[0]

    def value(self, sites) -> Any:
        """Fetch one cell from the result.

        For this to work, the result must be exactly one row long and this row needs to have
        exactly one column. Any other combination will lead to a ValueError

        Args:
            sites:
                A LiveStatus connection object.

        Returns:
            The queried value.

        Raises:
            ValueError: When the row-count is not 1 and the column-count is not 1.

        """
        result = self.fetchone(sites)
        if len(result) != 1:
            raise ValueError(f"Expected only one column, got {len(result)} columns.")
        return list(result.values())[0]

    def fetch_values(self, sites) -> List[List[Any]]:
        """Return the result coming from LiveStatus.

        This returns a list with each row being a list of len(number of columns requested).

        Args:
            sites:
                A LiveStatus connection object.

        Returns:
            The response as a list of lists.
        """
        return sites.query(self.compile())

    def iterate(self, sites) -> Generator[ResultRow, None, None]:
        """Return a generator of the result.

        Args:
            sites:
                A LiveStatus connection object.

        Returns:
            The generator which yields one ResultRow per row.

        """
        names = self.column_names
        for entry in self.fetch_values(sites):
            # This is Dict[str, Any], just with Attribute based access. Can't do much about this.
            yield ResultRow(list(zip(names, entry)))

    def to_dict(self, sites) -> Dict[Any, Any]:
        """Return a dict from the result set.

        The first column will be the mapping key, the second one the value.

        Args:
            sites:
                A LiveStatus connection object.

        Returns:
            The finished dictionary.

        """
        result = {}
        if len(self.columns) != 2:
            raise ValueError("Number of columns need to be exactly 2 to create a dict.")
        for key, value in self.iterate(sites):
            result[key] = value
        return result

    def compile(self) -> str:
        """Compile the current query and return it in string-form.

        Returns:
            The LiveStatus-Query as a string.

        """
        _query = []
        column_names = ' '.join(column.name for column in self.columns)
        _query.append(("Columns", column_names))
        _query.extend(self.filter_expr.render())
        return '\n'.join([
            'GET %s' % self.table.__tablename__,
            *[': '.join(line) for line in _query],
        ])
