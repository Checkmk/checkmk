#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2020 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from contextlib import contextmanager
from typing import Any, cast, Dict, Generator, List, Optional, Tuple, Type

from cmk.utils.livestatus_helpers import tables
from cmk.utils.livestatus_helpers.base import BaseQuery
from cmk.utils.livestatus_helpers.expressions import (
    And,
    BinaryExpression,
    Not,
    NothingExpression,
    Or,
    QueryExpression,
)
from cmk.utils.livestatus_helpers.types import Column, expr_to_tree, Table

# TODO: Support Stats headers in Query() class


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


def _get_column(table_class: Type[Table], col: str) -> Column:
    """Strip prefixes from column names and return the correct column

    Examples:

        >>> from cmk.utils.livestatus_helpers.tables import Hosts, Services
        >>> _get_column(Hosts, "host_name")
        Column(hosts.name: string)

        >>> _get_column(Services, "host_name")
        Column(services.host_name: string)

        >>> _get_column(Services, "service_description")
        Column(services.description: string)

    Args:
        table_class:
            A predefined Livestatus table class
        col:
            A string, giving the name of the wanted column

    Returns:
        A column instance

    """
    if hasattr(table_class, col):
        return getattr(table_class, col)

    table_name = cast(str, table_class.__tablename__)
    prefix = table_name.rstrip("s") + "_"
    while col.startswith(prefix):
        col = col[len(prefix) :]
    return getattr(table_class, col)


class Query(BaseQuery):
    """A representation of a Livestatus query.

    This holds all necessary information to generate a valid livestatus query.

    This class provides a number of convenience metehods to query data from Livestatus.

    These are:

      * fetch_values - returns list of tuples
      * to_dict - converts a list of 2-tuples into a dict

      * fetchone - returns a dict, first entry
      * first - returns a dict, first entry or None
      * iterate - returns a list of dicts

      * value - returns a scalar
      * first_value - returns a scalar or None

    All methods honor the "set_prepend_site" setting of livestatus.py and prepend the site
    on each row or add the site into the dictionary with the key "site".

    Examples:

        >>> from cmk.utils.livestatus_helpers.expressions import Not

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

    def __init__(
        self,
        columns: List[Column],
        filter_expr: QueryExpression = NothingExpression(),
    ):
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
        _tables = {column.table for column in columns}
        if len(_tables) != 1:
            raise ValueError(f"Query doesn't specify a single table: {_tables!r}")

        self.table: Type[Table] = _tables.pop()

    def filter(self, filter_expr: QueryExpression) -> "Query":
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

    def first_value(self, sites) -> Optional[Any]:
        """Fetch one cell from the result.

        If no result could be found, None is returned.

        When a result could be found however, the result must have exactly one column. Any other
        combination will lead to a ValueError

        Args:
            sites:
                A LiveStatus connection object.

        Returns:
            The queried value or None.

        Raises:
            ValueError: When the column-count is not 1.

        Examples:

            >>> class Hosts(Table):
            ...      __tablename__ = 'hosts'
            ...      name = Column('name', 'string', 'The host name')
            ...      parents = Column('parents', 'list', 'The hosts parents')

            >>> from cmk.gui.livestatus_utils.testing import simple_expect
            >>> with simple_expect() as live:
            ...    _ = live.expect_query("GET hosts\\nColumns: parents\\nFilter: name = heute")
            ...    Query([Hosts.parents], Hosts.name == "heute").first_value(live)
            ['example.com']

            >>> Query([Hosts.name, Hosts.name], Hosts.name == "heute").first_value(live)
            Traceback (most recent call last):
            ...
            ValueError: Number of columns need to be exactly 1 to give a value.

        """
        if len(self.columns) != 1:
            raise ValueError("Number of columns need to be exactly 1 to give a value.")
        entry = self.first(sites)
        if entry is not None:
            return list(entry.values())[0]
        return None

    def fetchall(self, sites) -> List[ResultRow]:
        return list(self.iterate(sites))

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

        Examples:

            >>> class Hosts(Table):
            ...      __tablename__ = 'hosts'
            ...      name = Column('name', 'string', 'The host name')
            ...      parents = Column('parents', 'list', 'The hosts parents')

            >>> from cmk.gui.livestatus_utils.testing import simple_expect

            >>> with simple_expect() as live:
            ...    _ = live.expect_query("GET hosts\\nColumns: name\\nFilter: name = heute")
            ...    Query([Hosts.name], Hosts.name == "heute").fetchone(live)
            {'name': 'heute'}

            >>> with simple_expect() as live:
            ...    _ = live.expect_query("GET hosts\\nColumns: name\\nFilter: name = heute")
            ...    live.set_prepend_site(True)
            ...    Query([Hosts.name], Hosts.name == "heute").fetchone(live)
            {'site': 'NO_SITE', 'name': 'heute'}

            >>> with simple_expect() as live:
            ...    _ = live.expect_query("GET hosts\\nColumns: name")
            ...    Query([Hosts.name]).fetchone(live)
            Traceback (most recent call last):
            ...
            ValueError: Expected one row, got 2 row(s).

        """
        result = list(self.iterate(sites))
        if len(result) != 1:
            raise ValueError(f"Expected one row, got {len(result)} row(s).")
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

        Examples:

            >>> class Hosts(Table):
            ...      __tablename__ = 'hosts'
            ...      name = Column('name', 'string', 'The host name')
            ...      parents = Column('parents', 'list', 'The hosts parents')

            >>> from cmk.gui.livestatus_utils.testing import simple_expect
            >>> with simple_expect() as live:
            ...    _ = live.expect_query("GET hosts\\nColumns: parents\\nFilter: name = heute")
            ...    Query([Hosts.parents], Hosts.name == "heute").value(live)
            ['example.com']

            >>> Query([Hosts.name, Hosts.name], Hosts.name == "heute").value(live)
            Traceback (most recent call last):
            ...
            ValueError: Number of columns need to be exactly 1 to give a value.

        """
        if len(self.columns) != 1:
            raise ValueError("Number of columns need to be exactly 1 to give a value.")
        return list(self.fetchone(sites).values())[0]

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

        Examples:

            >>> class Hosts(Table):
            ...      __tablename__ = 'hosts'
            ...      name = Column('name', 'string', 'The host name')
            ...      parents = Column('parents', 'list', 'The hosts parents')

            >>> from cmk.gui.livestatus_utils.testing import simple_expect
            >>> with simple_expect() as live:
            ...    _ = live.expect_query("GET hosts\\nColumns: name parents")
            ...    list(Query([Hosts.name, Hosts.parents]).iterate(live))
            [{'name': 'heute', 'parents': ['example.com']}, {'name': 'example.com', 'parents': []}]

            >>> with simple_expect() as live:
            ...    _ = live.expect_query("GET hosts\\nColumns: name parents")
            ...    live.set_prepend_site(True)
            ...    list(Query([Hosts.name, Hosts.parents]).iterate(live))
            [{'site': 'NO_SITE', 'name': 'heute', 'parents': ['example.com']}, \
{'site': 'NO_SITE', 'name': 'example.com', 'parents': []}]

        """
        if sites.prepend_site:
            if "site" in self.column_names:
                raise ValueError("Conflict: site both as column in a table and via prepend_site")
            names = ["site", *self.column_names]
        else:
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

        Raises:
            ValueError: when more than 2 columns are in the query.

        Examples:

            >>> class Hosts(Table):
            ...      __tablename__ = 'hosts'
            ...      name = Column('name', 'string', 'The host name')
            ...      parents = Column('parents', 'list', 'The hosts parents')

            >>> from cmk.gui.livestatus_utils.testing import simple_expect
            >>> with simple_expect() as live:
            ...    _ = live.expect_query("GET hosts\\nColumns: name parents")
            ...    Query([Hosts.name, Hosts.parents]).to_dict(live)
            {'heute': ['example.com'], 'example.com': []}

            When more than 2 columns are given, an error is raised.

            >>> Query([Hosts.name, Hosts.name, Hosts.parents]).to_dict(live)
            Traceback (most recent call last):
            ...
            ValueError: Number of columns need to be exactly 2 to create a dict.

        """
        result = {}
        if len(self.columns) != 2:
            raise ValueError("Number of columns need to be exactly 2 to create a dict.")
        for key, value in self.fetch_values(sites):
            result[key] = value
        return result

    def compile(self) -> str:
        """Compile the current query and return it in string-form.

        Returns:
            The LiveStatus-Query as a string.

        """
        _query: List[Tuple[str, str]] = []
        column_names = " ".join(column.name for column in self.columns)
        _query.append(("Columns", column_names))
        _query.extend(self.filter_expr.render())
        return "\n".join(
            [
                "GET %s" % self.table.__tablename__,
                *[": ".join(line) for line in _query],
            ]
        )

    def dict_repr(self):
        return expr_to_tree(self.table, self.filter_expr)

    @classmethod
    def from_string(  # pylint: disable=too-many-branches
        cls,
        string_query: str,
    ) -> "Query":
        """Constructs a Query instance from a string based LiveStatus-Query

        Args:
            string_query:
                A LiveStatus query as a string.

        Examples:

            >>> q = Query.from_string('GET services\\n'
            ...                       'Columns: service_service_description\\n'
            ...                       'Filter: service_service_description = \\n')

            >>> query_text = ('''GET services
            ... Columns: host_address host_check_command host_check_type host_custom_variable_names host_custom_variable_values host_downtimes_with_extra_info host_file name host_has_been_checked host_name host_scheduled_downtime_depth host_state service_accept_passive_checks service_acknowledged service_action_url_expanded service_active_checks_enabled service_cache_interval service_cached_at service_check_command service_check_type service_comments_with_extra_info service_custom_variable_names service_custom_variable_values service_custom_variables service_description service_downtimes service_downtimes_with_extra_info service_has_been_checked service_host_name service_icon_image service_in_check_period service_in_notification_period service_in_passive_check_period service_in_service_period service_is_flapping service_last_check service_last_state_change service_modified_attributes_list service_notes_url_expanded service_notifications_enabled service_perf_data service_plugin_output service_pnpgraph_present service_scheduled_downtime_depth service_service_description service_staleness service_state
            ... Filter: service_state = 0
            ... Filter: service_has_been_checked = 1
            ... And: 2
            ... Negate:
            ... Filter: service_has_been_checked = 1
            ... Filter: service_scheduled_downtime_depth = 0
            ... Filter: host_scheduled_downtime_depth = 0
            ... And: 2
            ... Filter: service_acknowledged = 0
            ... Filter: host_state = 1
            ... Filter: host_has_been_checked = 1
            ... And: 2
            ... Negate:
            ... Filter: host_state = 2
            ... Filter: host_has_been_checked = 1
            ... And: 2
            ... Negate:
            ... ''')
            >>> q = Query.from_string(query_text)

            We can faithfully recreate this query as a dict-representation.

            >>> q.dict_repr()
            {'op': 'and', 'expr': [\
{'op': 'not', 'expr': \
{'op': 'and', 'expr': [\
{'op': '=', 'left': 'services.state', 'right': '0'}, \
{'op': '=', 'left': 'services.has_been_checked', 'right': '1'}\
]}}, \
{'op': '=', 'left': 'services.has_been_checked', 'right': '1'}, \
{'op': 'and', 'expr': [\
{'op': '=', 'left': 'services.scheduled_downtime_depth', 'right': '0'}, \
{'op': '=', 'left': 'services.host_scheduled_downtime_depth', 'right': '0'}\
]}, \
{'op': '=', 'left': 'services.acknowledged', 'right': '0'}, \
{'op': 'not', 'expr': \
{'op': 'and', 'expr': [\
{'op': '=', 'left': 'services.host_state', 'right': '1'}, \
{'op': '=', 'left': 'services.host_has_been_checked', 'right': '1'}\
]}}, \
{'op': 'not', 'expr': \
{'op': 'and', 'expr': [\
{'op': '=', 'left': 'services.host_state', 'right': '2'}, \
{'op': '=', 'left': 'services.host_has_been_checked', 'right': '1'}\
]}}\
]}

            >>> q.columns
            [Column(services.host_address: string), Column(services.host_check_command: string), Column(services.host_check_type: int), Column(services.host_custom_variable_names: list), Column(services.host_custom_variable_values: list), Column(services.host_downtimes_with_extra_info: list), Column(services.host_has_been_checked: int), Column(services.host_name: string), Column(services.host_scheduled_downtime_depth: int), Column(services.host_state: int), Column(services.accept_passive_checks: int), Column(services.acknowledged: int), Column(services.action_url_expanded: string), Column(services.active_checks_enabled: int), Column(services.cache_interval: int), Column(services.cached_at: time), Column(services.check_command: string), Column(services.check_type: int), Column(services.comments_with_extra_info: list), Column(services.custom_variable_names: list), Column(services.custom_variable_values: list), Column(services.custom_variables: dict), Column(services.description: string), Column(services.downtimes: list), Column(services.downtimes_with_extra_info: list), Column(services.has_been_checked: int), Column(services.host_name: string), Column(services.icon_image: string), Column(services.in_check_period: int), Column(services.in_notification_period: int), Column(services.in_passive_check_period: int), Column(services.in_service_period: int), Column(services.is_flapping: int), Column(services.last_check: time), Column(services.last_state_change: time), Column(services.modified_attributes_list: list), Column(services.notes_url_expanded: string), Column(services.notifications_enabled: int), Column(services.perf_data: string), Column(services.plugin_output: string), Column(services.pnpgraph_present: int), Column(services.scheduled_downtime_depth: int), Column(services.description: string), Column(services.staleness: float), Column(services.state: int)]

            >>> q = Query.from_string('GET hosts\\n'
            ...                       'Columns: name service_description\\n'
            ...                       'Filter: service_description = ')
            Traceback (most recent call last):
            ...
            ValueError: Table 'hosts': Could not decode line 'Filter: service_description = '

            All unknown columns are ignored, as there are many places in Checkmk where queries
            specify wrong or unnecessary columns. Livestatus would normally ignore them.

            >>> _ = Query.from_string('GET hosts\\n'
            ...                       'Columns: service_service_description\\n'
            ...                       'Filter: service_description = ')
            Traceback (most recent call last):
            ...
            ValueError: Table 'hosts': Could not decode line 'Filter: service_description = '

            >>> _ = Query.from_string('GET foobazbar\\n'
            ...                       'Columns: name service_description\\n'
            ...                       'Filter: service_description = ')
            Traceback (most recent call last):
            ...
            ValueError: Table foobazbar was not defined in the tables module.


            >>> q = Query.from_string('GET hosts\\n'
            ...                       'Columns: name\\n'
            ...                       'Filter: name = heute\\n'
            ...                       'Filter: alias = heute\\n'
            ...                       'Or: 2')


            >>> q.table.__name__
            'Hosts'

            >>> q.columns
            [Column(hosts.name: string)]

            >>> q.filter_expr
            Or(Filter(name = heute), Filter(alias = heute))

            >>> print(q)
            GET hosts
            Columns: name
            Filter: name = heute
            Filter: alias = heute
            Or: 2

            So in essence this says that round trips work

                >>> assert str(q) == str(Query.from_string(str(q)))

        Returns:
            A Query instance.

        Raises:
            A ValueError if no Query() instance could be created.

        """
        lines = string_query.split("\n")
        for line in lines:
            if line.startswith("GET "):
                parts = line.split()
                if len(parts) < 2:
                    raise ValueError(f"No table found in line: {line!r}")

                table_name = parts[1]
                try:
                    table_class: Type[Table] = getattr(tables, table_name.title())
                except AttributeError:
                    raise ValueError(f"Table {table_name} was not defined in the tables module.")
                break
        else:
            raise ValueError("No table found")

        for line in lines:
            if line.startswith("Columns: "):
                column_names = line.split(": ", 1)[1].lstrip().split()
                columns: List[Column] = []
                for col in column_names:
                    try:
                        columns.append(_get_column(table_class, col))
                    except AttributeError:
                        pass
                break
        else:
            raise ValueError("No columns found")

        filters: List[QueryExpression] = []
        for line in lines:
            if line.startswith("Filter: "):
                try:
                    filters.append(_parse_line(table_class, line))
                except AttributeError:
                    raise ValueError(f"Table {table_name!r}: Could not decode line {line!r}")
            elif line.startswith("Or: ") or line.startswith("And: "):
                op, _count = line.split(": ")
                count = int(_count)
                # I'm sorry. :)
                # We take the last `count` filters and pass them into the BooleanExpression
                try:
                    expr = {"or": Or, "and": And}[op.lower()](*filters[-count:])
                except ValueError:
                    raise ValueError(f"Could not parse {op} for {filters!r}")
                filters = filters[:-count]
                filters.append(expr)
            elif line.startswith("Negate:") or line.startswith("Not:"):
                filters[-1] = Not(filters[-1])

        if len(filters) > 1:
            filters = [And(*filters)]

        return cls(
            columns=columns,
            filter_expr=filters[0] if filters else NothingExpression(),
        )


def _parse_line(
    table: Type[Table],
    filter_string: str,
) -> BinaryExpression:
    """Parse a single filter line into a BinaryExpression

    Args:
        table:
            A Table instance.

        filter_string:
            One "Filter:" line. Has to start with "Filter:". Other expressions are
            not yet supported.

    Examples:

        >>> from cmk.utils.livestatus_helpers.tables import Hosts
        >>> _parse_line(Hosts, "Filter: name !>= value")
        Filter(name !>= value)

        >>> _parse_line(Hosts, "Filter: name =")
        Filter(name = )

        >>> _parse_line(Hosts, "Filter: foo !>= value")
        Traceback (most recent call last):
        ...
        AttributeError: type object 'Hosts' has no attribute 'foo'

    Returns:
        A BinaryExpression

    Raises:
        An AttributeError if the Table has no such column.
    """
    if not filter_string.startswith("Filter:"):
        raise ValueError(f"Illegal filter string: {filter_string!r}")
    _, column_name, op, *value = filter_string.split(None, 3)
    column = _get_column(table, column_name)
    return column.op(op, value)


@contextmanager
def detailed_connection(connection):
    prev = connection.prepend_site
    connection.set_prepend_site(True)
    try:
        yield connection
    finally:
        connection.set_prepend_site(prev)
