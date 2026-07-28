#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# mypy: disable-error-code="explicit-any"


import abc
from typing import Any, Literal, override

from .expressions import (
    BinaryExpression,
    BoolExpression,
    ListExpression,
    LqSafe,
    Not,
    NothingExpression,
    Primitives,
    QueryExpression,
    ScalarExpression,
    UnaryExpression,
)

LivestatusType = Literal["string", "int", "float", "list", "dict", "dictdouble", "time", "blob"]
ExpressionDict = dict[str, Any]


class Table(abc.ABC):
    """Baseclass of all livestatus tables.

    This class doesn't do much, it just acts as a container for `Column` instances.
    """

    __tablename__: str

    @classmethod
    def __columns__(cls) -> list[str]:
        """Gives a list of all columns which are defined on the Table."""
        columns = []
        for key, value in cls.__dict__.items():
            if isinstance(value, Column):
                columns.append(key)
        return columns


class NoTable(Table):
    """Like a livestatus table, but not really.

    Can be used in place of an actual table, in order to not have to use `Optional` types when
    something is initialized only later.
    """

    @classmethod
    @override
    def __columns__(cls) -> list[str]:
        raise NotImplementedError("NoTable instances have no columns.")


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
        name: str,
        col_type: LivestatusType,
        description: str | None = None,
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
        self.name = name
        self.label_name: str | None = None
        self.type: LivestatusType = col_type
        self.expr = ListExpression(name) if col_type == "list" else ScalarExpression(name)
        self.table: type[Table] = NoTable

        self.__doc__ = description

    @property
    def full_name(self) -> str:
        # This needs to be a @property, due to the descriptor magic mentioned elsewhere.
        return f"{self.table.__tablename__}.{self.name}"

    @override
    def __str__(self) -> str:
        return self.name

    @override
    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}({self.full_name}: {self.type})"

    @property
    def query_name(self) -> str:
        """This represents the name to be used in the Response.

        In case you want to use `iterate` to get a sequence of dicts, you can set the key within
        this dict by calling `label(label_name)`. The supplied name will be emitted here for use
        in response generation.

        Returns:
            The name to be used in the query response.
        """
        return self.label_name if self.label_name is not None else self.name

    def label(self, label_name: str) -> Column:
        """Set the label for use in the response.

        Args:
            label_name:
                The name which the column should have in the response.

        Returns:
            A copy of this column, with the label set.

        """
        copy = Column(self.name, self.type, self.__doc__)
        copy.table = self.table
        copy.label_name = label_name
        return copy

    def __get__(self, obj: object, obj_type: type[Table]) -> Column:
        # As we don't know on which Table this Column is located, we use
        # the descriptor protocol during attribute access to find out.
        if self.table is NoTable:
            self.table = obj_type

        return self

    @override
    def __eq__(self, other: Primitives | LqSafe) -> BinaryExpression:  # type: ignore[override]
        return self.expr.__eq__(other)

    @override
    def __ne__(self, other: Primitives | LqSafe) -> Not:  # type: ignore[override]
        return self.expr.__ne__(other)

    def __lt__(self, other: Primitives | LqSafe) -> BinaryExpression:
        return self.expr.__lt__(other)

    def __le__(self, other: Primitives | LqSafe) -> BinaryExpression:
        return self.expr.__le__(other)

    def __gt__(self, other: Primitives | LqSafe) -> BinaryExpression:
        return self.expr.__gt__(other)

    def __ge__(self, other: Primitives | LqSafe) -> BinaryExpression:
        return self.expr.__ge__(other)

    def equals(self, other: Primitives | LqSafe, ignore_case: bool = False) -> BinaryExpression:
        return self.expr.equals(other, ignore_case=ignore_case)

    def contains(self, other: Primitives | LqSafe, ignore_case: bool = False) -> BinaryExpression:
        return self.expr.contains(other, ignore_case=ignore_case)

    def disparity(self, other: Primitives | LqSafe, ignore_case: bool = False) -> BinaryExpression:
        return self.expr.disparity(other, ignore_case=ignore_case)

    def op(self, op_str: str, other: UnaryExpression | Primitives | LqSafe) -> BinaryExpression:
        return self.expr.op(op_str, other)

    def empty(self) -> BinaryExpression:
        return self.expr.empty()


class DynamicColumn:
    """A representation of a livestatus dynamic column.

    Dynamic columns are registered in the core via `addDynamicColumn` and take
    runtime parameters which are appended to the column name, separated by
    colons (e.g. ``prediction_file:file:some/path``). A `DynamicColumn` can
    therefore not be used in a `Query` directly: calling `dynamic` with the
    runtime parameters yields a regular `Column` which can.

    Examples:

        >>> class Services(Table):
        ...     __tablename__ = 'services'
        ...
        ...     prediction_file = DynamicColumn(
        ...         'prediction_file', 'blob', 'Fetch prediction data')

        >>> Services.prediction_file
        DynamicColumn(services.prediction_file: blob)

        >>> Services.prediction_file.dynamic('file', 'metric/day-123-upper')
        Column(services.prediction_file:file:metric/day-123-upper: blob)

        The parameters are validated to prevent query injection:

        >>> Services.prediction_file.dynamic('file', 'foo\\nbar')
        Traceback (most recent call last):
        ...
        ValueError: Invalid Livestatus Query string: 'foo\\nbar'

        >>> Services.prediction_file.dynamic('file', 'foo bar')
        Traceback (most recent call last):
        ...
        ValueError: Invalid dynamic column parameter (contains whitespace): 'foo bar'
    """

    def __init__(
        self,
        name: str,
        col_type: LivestatusType,
        description: str | None = None,
    ):
        """A representation of a livestatus dynamic column.

        Args:
            name:
                The name under which the dynamic column is registered in the
                core, e.g. `prediction_file`.

            col_type:
                The livestatus column type of the columns created by the core
                at runtime.

            description:
                The documentation for this column. The __doc__ attribute will
                be populated with this text.
        """
        self.name = name
        self.type: LivestatusType = col_type
        self.table: type[Table] = NoTable
        self.__doc__ = description

    def __get__(self, obj: object, obj_type: type[Table]) -> DynamicColumn:
        # Same descriptor logic as in `Column`: bind the table on attribute
        # access.
        if self.table is NoTable:
            self.table = obj_type

        return self

    @property
    def full_name(self) -> str:
        return f"{self.table.__tablename__}.{self.name}"

    @override
    def __repr__(self) -> str:
        class_name = self.__class__.__name__
        return f"{class_name}({self.full_name}: {self.type})"

    def dynamic(
        self,
        column_title: str | LqSafe,
        *arguments: str | int | float | LqSafe,
    ) -> Column:
        """Parametrize this dynamic column for use in a `Query`.

        Args:
            column_title:
                The name under which the core registers the created column,
                e.g. `file`. Must not contain colons.

            arguments:
                The runtime parameters of the column, e.g. the file path for
                `prediction_file`. Multiple arguments are joined with colons.

        Returns:
            A `Column` named `<name>:<column_title>:<argument>[:<argument>...]`.

        Raises:
            ValueError: If a parameter would break the query, i.e. it contains
                whitespace (column names are whitespace-separated in the
                `Columns:` header) or the title contains a colon.
        """
        if not arguments:
            raise ValueError(f"Dynamic column {self.name!r} requires at least one argument")
        title = _validate_lq_safe(column_title)
        args = [_validate_lq_safe(argument) for argument in arguments]
        if not title or ":" in title:
            raise ValueError(f"Invalid dynamic column title: {title!r}")
        for part in (title, *args):
            if any(char.isspace() for char in part):
                raise ValueError(
                    f"Invalid dynamic column parameter (contains whitespace): {part!r}"
                )
        column = Column(":".join([self.name, title, *args]), self.type, self.__doc__)
        column.table = self.table
        # Use the (unique) column title as the response key, so consumers of
        # `iterate`/`fetchone` get a sane key instead of the composed wire name.
        column.label_name = title
        return column


def _validate_lq_safe(part: str | int | float | LqSafe) -> str:
    return str(part if isinstance(part, LqSafe) else LqSafe(part))


def escape_filename(file_name: str) -> str:
    """Escape a file name for use as a dynamic file column argument.

    This is the inverse of the core's ``mk::unescape_filename``, which decodes
    ``\\s`` to a space and ``\\<char>`` to ``<char>``. The backslash must be
    escaped before the space. Escaping is required because the ``Columns:``
    header is whitespace-separated, so a raw space would end the column name
    (`DynamicColumn.dynamic` rejects such arguments).
    """
    return file_name.replace("\\", "\\\\").replace(" ", "\\s")


def expr_to_tree(
    table: type[Table],
    query_expr: QueryExpression,
) -> ExpressionDict | None:
    """Transform the query-expression to a dict-tree.

    Examples:

        >>> from cmk.livestatus_client.expressions import And
        >>> from cmk.livestatus_client.tables import Hosts
        >>> expr_to_tree(Hosts, Not(And(Hosts.name == 'heute', Hosts.alias == 'heute')))
        {'op': 'not', 'expr': {'op': 'and', 'expr': [\
{'op': '=', 'left': 'hosts.name', 'right': 'heute'}, \
{'op': '=', 'left': 'hosts.alias', 'right': 'heute'}]}}

    Args:
        table:
        query_expr:

    Returns:
        A nested dictionary tree, which uniquely represents the given query-expression.

    """
    if isinstance(query_expr, BinaryExpression):
        return {
            "op": query_expr.operator,
            "left": getattr(table, query_expr.left.value).full_name,
            "right": query_expr.right.value,
        }

    if isinstance(query_expr, BoolExpression):
        return {
            "op": query_expr.__class__.__name__.lower(),
            "expr": [expr_to_tree(table, arg) for arg in query_expr.args],
        }

    if isinstance(query_expr, Not):
        return {"op": "not", "expr": expr_to_tree(table, query_expr.other)}

    if isinstance(query_expr, NothingExpression):
        return None

    raise ValueError(f"Unsupported expression: {query_expr!r}")
