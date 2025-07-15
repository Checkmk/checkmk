#!/usr/bin/env python3
# Copyright (C) 2020 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast, Literal, TYPE_CHECKING, TypedDict

from marshmallow import post_load, pre_dump, types, validates_schema, ValidationError
from marshmallow_oneofschema import OneOfSchema

from cmk.utils.rulesets.conditions import (
    HostOrServiceConditions,
    HostOrServiceConditionsNegated,
    HostOrServiceConditionsSimple,
)
from cmk.utils.rulesets.ruleset_matcher import (
    TagCondition,
    TagConditionNE,
    TagConditionNOR,
    TagConditionOR,
)
from cmk.utils.tags import TagID

from cmk.gui import fields as gui_fields
from cmk.gui.fields import base
from cmk.gui.openapi.restful_objects import response_schemas

from cmk import fields

LabelConditions = dict[str, str | TagConditionNE]

# Needed for cast()-ing. Do not move into typing.TYPE_CHECKING
ApiExpressionValue = list[str] | str

if TYPE_CHECKING:
    ApiOperator = Literal["is", "is_not", "one_of", "none_of"]
    TagExpr = TagConditionNE | TagConditionOR | TagConditionNOR

    class ApiExpressionSingle(TypedDict, total=True):
        key: str
        operator: ApiOperator
        value: ApiExpressionValue

    ApiExpression = ApiExpressionSingle | list[ApiExpressionSingle]

    class ApiMatchExpression(TypedDict, total=True):
        match_on: list[str]
        operator: ApiOperator


class APILabelCondition(TypedDict):
    operator: Literal["and", "or", "not"]
    label: str


class APILabelGroupCondition(TypedDict):
    operator: Literal["and", "or", "not"]
    label_group: list[APILabelCondition]


RULE_ID: Mapping[str, fields.String] = {
    "rule_id": fields.String(
        description="The ID of the rule.",
        required=True,
        example="0a168697-14a2-48d0-9c3c-ca65569a39e2",
    ),
}


class _BaseMoveTo(base.BaseSchema):
    cast_to_dict = True

    position = fields.String(
        description="""The type of position to move to.
        Note that you cannot move rules before rules managed by a Quick setup. In the case of
        `top_of_folder` your rule will instead be after all managed rules. If you specify a managed
        rule in `after_specific_rule` or `before_specific_rule` you will receive an error.""",
        example="top_of_folder",
    )


class MoveToFolder(_BaseMoveTo):
    folder = gui_fields.FolderField(example="/")


class MoveToSpecificRule(_BaseMoveTo):
    rule_id = fields.String(
        description="The UUID of the rule to move after/before.",
        example="f8b74720-a454-4242-99c4-62994ef0f2bf",
    )


class MoveRuleTo(OneOfSchema):
    """

    Examples:

        >>> from cmk.gui.utils.script_helpers import application_and_request_context

        >>> schema = MoveRuleTo()
        >>> from cmk.gui.livestatus_utils.testing import mock_site
        >>> with mock_site(), application_and_request_context():
        ...     schema.load({"position": "top_of_folder", "folder": "/"})
        {'position': 'top_of_folder', 'folder': Folder('', 'Main')}

        >>> schema.load({"position": "after_specific_rule",
        ...              "rule_id": "f8b74720-a454-4242-99c4-62994ef0f2bf"})
        {'position': 'after_specific_rule', 'rule_id': 'f8b74720-a454-4242-99c4-62994ef0f2bf'}

        >>> schema.load({"position": "foo"})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: {'position': ['Unsupported value: foo']}


    """

    type_field = "position"
    type_field_remove = False
    type_schemas = {
        "top_of_folder": MoveToFolder,
        "bottom_of_folder": MoveToFolder,
        "after_specific_rule": MoveToSpecificRule,
        "before_specific_rule": MoveToSpecificRule,
    }


class LabelConditionSchema(base.BaseSchema):
    """A schema representing a label condition.

    This schema translates to and from Checkmk's internal format.

    Examples:

        >>> l = LabelConditionSchema()
        >>> l.load([{'key': 'os', 'operator': 'is', 'value': 'windows'},
        ...         {'key': 'os', 'operator': 'is_not', 'value': 'windows'}], many=True)  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: ...

        >>> rv = l.load([{'key': 'os', 'operator': 'is', 'value': 'windows'},
        ...         {'key': 'foo', 'operator': 'is_not', 'value': 'bar'}], many=True)  # doctest: +ELLIPSIS
        >>> rv
        [{'operator': 'and', 'label_group': [{'operator': 'and', 'label': 'os:windows'}, {'operator': 'not', 'label': 'foo:bar'}]}]
    """

    cast_to_dict = True

    key = fields.String(
        required=True,
        description="The key of the label. e.g. 'os' in 'os:windows'",
    )
    operator = fields.String(
        enum=["is", "is_not"],
        required=True,
        description="How the label should be matched.",
    )
    value = fields.String(
        required=True,
        description="The value of the label. e.g. 'windows' in 'os:windows'",
    )

    @post_load(pass_many=True)
    def convert_to_checkmk(
        self,
        data: list[ApiExpressionSingle],
        many: bool = False,
        partial: bool = False,
    ) -> list[APILabelGroupCondition]:
        label_group: list[APILabelCondition] = []
        labels_added: list[str] = []
        for entry in data:
            label_str = f"{entry['key']}:{entry['value']}"
            if label_str in labels_added:
                raise ValidationError(
                    f"Keys can only be used once. Duplicate key: {entry['key']!r}"
                )

            label_group.append(
                {"operator": "not" if entry["operator"] == "is_not" else "and", "label": label_str},
            )
            labels_added.append(label_str)

        new_entries: list[APILabelGroupCondition] = [
            {"operator": "and", "label_group": label_group}
        ]

        return new_entries


class TagConditionSchemaBase(base.BaseSchema):
    allowed_operators: tuple[str, str]
    operator_type: str

    key = fields.String(
        required=True,
        description="The name of the tag.",
    )

    @pre_dump(pass_many=False)
    def convert_to_api(
        self,
        data,
        many=False,
        **kwargs,
    ):
        rv = {}
        for key, value in data.items():
            operator = _unpack_operator(value)
            if operator not in self.allowed_operators:
                raise ValidationError(f"Operator {operator!r} not allowed in this context.")
            try:
                unpacked = _unpack_value(value)
            except ValueError as exc:
                raise ValidationError(str(exc), field_name=key) from exc

            if self.operator_type == "collection":
                if not isinstance(unpacked, list):
                    raise ValidationError(f"Invalid type: {unpacked!r}", field_name=key)

            rv.update(
                {
                    "key": key,
                    "operator": operator,
                    "value": unpacked,
                }
            )
            # Just to make the point clear.
            break

        return rv

    @post_load(pass_many=False)
    def convert_back(
        self,
        data,
        many=False,
        **kwargs,
    ):
        value: TagCondition | str
        if self.operator_type == "collection":
            value = _collection_value(data["value"], data["operator"])
        elif self.operator_type == "scalar":
            value = _scalar_value(data["value"], data["operator"])
        else:
            raise RuntimeError(f"Unsupported type: {self.operator_type}")

        return {data["key"]: value}


class TagConditionScalarSchemaBase(TagConditionSchemaBase):
    """

    Examples:

        >>> t = TagConditionScalarSchemaBase()
        >>> t.dump({"criticality": "prod"})
        {'key': 'criticality', 'operator': 'is', 'value': 'prod'}

        >>> t.dump([{"criticality": "prod"}], many=True)
        [{'key': 'criticality', 'operator': 'is', 'value': 'prod'}]

        >>> t.dump([{"criticality": {"$ne": "prod"}}], many=True)
        [{'key': 'criticality', 'operator': 'is_not', 'value': 'prod'}]

        >>> t.dump({"criticality": {"$or": "prod"}})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Operator 'one_of' not allowed in this context.

        >>> t.dump({"criticality": {"$nor": "prod"}})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Operator 'none_of' not allowed in this context.

        >>> t.dump({"criticality": {"foo": "prod"}})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Unknown operator: 'foo'

        Converting it back is also possible:

        >>> t.load({'key': 'criticality', 'operator': 'is_not', 'value': 'prod'})
        {'criticality': {'$ne': 'prod'}}

        >>> t.load([{'key': 'criticality', 'operator': 'is_not', 'value': 'prod'}], many=True)
        [{'criticality': {'$ne': 'prod'}}]

    """

    cast_to_dict = True
    allowed_operators = ("is", "is_not")
    operator_type = "scalar"

    # field defined in superclass
    operator = fields.String(
        required=True,
        description="If the tag's value should match what is given under the field `value`.",
        enum=list(allowed_operators),  # Our serializer only wants to know lists.
    )
    value = fields.String(
        required=True,
        description="The value of a tag.",
    )


class TagConditionConditionSchemaBase(TagConditionSchemaBase):
    """Convert Rulesets to Checkmk structure and back

    Examples:

        >>> tcs = TagConditionConditionSchemaBase()
        >>> tcs.dump([{'hurz': {'$or': ['a', 'b', 'c']}}], many=True)
        [{'key': 'hurz', 'operator': 'one_of', 'value': ['a', 'b', 'c']}]

        >>> tcs.dump({'hurz': {'$or': ['a', 'b', 'c']}})
        {'key': 'hurz', 'operator': 'one_of', 'value': ['a', 'b', 'c']}

        >>> tcs.dump({'hurz': {'$or': 'h'}})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Invalid type: 'h'

    """

    cast_to_dict = True

    allowed_operators = ("one_of", "none_of")
    operator_type = "collection"

    # field defined in superclass
    operator = fields.String(
        required=True,
        description="If the matched tag should be one of the given values, or not.",
        enum=list(allowed_operators),  # Our serializer only wants to know lists.
    )
    value = fields.List(
        fields.String(description="The value of a tag."),
        required=True,
        description="A list of values for the tag.",
    )


# Werk 7352 talks about some of them: https://checkmk.com/werk/7352
# Although all these operators are supported, each one only applies to one or two
# particular locations in the code. There is no one piece of code which understands the
# operators, there are many.
class TagConditionSchema(OneOfSchema):
    """Convert Rulesets to Checkmk Structure and back

    Examples:

        >>> t = TagConditionSchema()
        >>> rv = t.dump({'criticality': {'$ne': 'prod'}, 'foo': {'$ne': 'bar'}}, many=True)
        >>> rv
        [{'key': 'criticality', 'operator': 'is_not', 'value': 'prod'}, \
{'key': 'foo', 'operator': 'is_not', 'value': 'bar'}]

        >>> rv = t.dump({'criticality': {'$ne': 'prod'}, 'foo': {'$ne': 'bar'}}, many=False)
        Traceback (most recent call last):
        ...
        RuntimeError: Can only be used with many=True

        >>> t.dump({'criticality': 'prod', 'foo': 'bar'}, many=True)
        [{'key': 'criticality', 'operator': 'is', 'value': 'prod'}, \
{'key': 'foo', 'operator': 'is', 'value': 'bar'}]

        >>> t.dump({'host_name': {'$nor': ['heute', 'gestern']}}, many=True)
        [{'key': 'host_name', 'operator': 'none_of', 'value': ['heute', 'gestern']}]

        >>> rv = t.dump({'a': 'b', 'c': {'$ne': 'd'}, 'e': {'$nor': ['f']}, 'g': {'$or': ['h']}},
        ...             many=True)
        >>> rv
        [{'key': 'a', 'operator': 'is', 'value': 'b'}, \
{'key': 'c', 'operator': 'is_not', 'value': 'd'}, \
{'key': 'e', 'operator': 'none_of', 'value': ['f']}, \
{'key': 'g', 'operator': 'one_of', 'value': ['h']}]

        >>> t.load(rv, many=True)
        {'a': 'b', 'c': {'$ne': 'd'}, 'e': {'$nor': ['f']}, 'g': {'$or': ['h']}}

    """

    type_schemas: Mapping[
        str,
        type[TagConditionScalarSchemaBase] | type[TagConditionConditionSchemaBase],
    ] = {
        "is": TagConditionScalarSchemaBase,
        "is_not": TagConditionScalarSchemaBase,
        "one_of": TagConditionConditionSchemaBase,
        "none_of": TagConditionConditionSchemaBase,
    }
    type_field = "operator"
    type_field_remove = False

    def get_obj_type(self, obj):
        if isinstance(obj, dict):
            op = _unpack_operator(obj[next(iter(obj))])
        else:
            raise RuntimeError("Can only be used with many=True")

        return op

    # no pre_dump here
    def dump(self, obj, *, many=None, **kwargs):
        if isinstance(obj, dict):
            # We need to split out the keys in individual dicts to make marshmallow happy.
            data = [{key: value} for key, value in obj.items()]
        else:
            raise ValidationError(f"Unsupported type: {obj!r}")
        return super().dump(data, many=many, **kwargs)

    def load(self, data, *, many=None, partial=None, unknown=None, **kwargs):
        entries = super().load(data, many=many, partial=partial, unknown=unknown, **kwargs)
        # We have to merge [{'tag1': 'foo'}, {'tag2': 'bar'}] into [{'tag1': 'foo', 'tag2': 'bar'}]
        # Note that the first list has two dictionaries, while the second has only one.
        rv = {}
        for entry in entries:
            key = next(iter(entry.keys()))
            if key in rv:
                raise ValidationError(f"Key {key!r} may only appear once!", field_name=key)
            rv.update(entry)
        # We never return a list, as Checkmk doesn't understand that internally.
        return rv


class HostOrServiceConditionSchema(base.BaseSchema):
    """

    Examples:

        >>> wor = HostOrServiceConditionSchema()  # without regex
        >>> rv = wor.load({
        ...     'match_on': ['foo'],
        ...     'operator': 'one_of',
        ... })
        >>> rv
        ['foo']

        >>> wor.dump(rv)
        {'match_on': ['foo'], 'operator': 'one_of'}

        >>> wr = HostOrServiceConditionSchema(use_regex="always")  # with regex
        >>> rv = wr.load({
        ...     'match_on': ['abc$', 'xyz$'],
        ...     'operator': 'one_of',
        ... })
        >>> rv
        [{'$regex': 'abc$'}, {'$regex': 'xyz$'}]

        >>> wr.dump(rv)
        {'match_on': ['abc$', 'xyz$'], 'operator': 'one_of'}

        >>> wadr = HostOrServiceConditionSchema(use_regex="adaptive")  #  when prefixed with ~
        >>> rv = wadr.load({
        ...     'match_on': ['~(heute|gestern)$', 'heute', '~[v]orgestern$'],
        ...     'operator': 'one_of',
        ... })
        >>> rv
        [{'$regex': '^(heute|gestern)$'}, 'heute', {'$regex': '^[v]orgestern$'}]

        >>> wadr.dump(rv)
        {'match_on': ['~(heute|gestern)$', 'heute', '~[v]orgestern$'], 'operator': 'one_of'}

    """

    def __init__(
        self,
        *,
        only: types.StrSequenceOrSet | None = None,
        exclude: types.StrSequenceOrSet = (),
        many: bool = False,
        context: dict[object, object] = {},
        load_only: types.StrSequenceOrSet = (),
        dump_only: types.StrSequenceOrSet = (),
        partial: bool | types.StrSequenceOrSet = False,
        unknown: str | None = None,
        use_regex: Literal["always", "never", "adaptive"] = "adaptive",
    ):
        self.use_regex = use_regex
        super().__init__(
            only=only,
            exclude=exclude,
            many=many,
            context=context,
            load_only=load_only,
            dump_only=dump_only,
            partial=partial,
            unknown=unknown,
        )

    cast_to_dict = True

    match_on = fields.List(
        fields.String(minLength=1),
        required=True,
        description="A list of string matching regular expressions.",
    )
    operator = fields.String(
        enum=["one_of", "none_of"],
        required=True,
        description=(
            "How the hosts or services should be matched.\n"
            " * one_of - will match if any of the hosts or services is matched\n"
            " * none_of - will match if none of the hosts are matched. In other words: will match"
            " all hosts or services which are not specified.\n"
        ),
    )

    @pre_dump(pass_many=False)
    def convert_to_api(
        self,
        data: HostOrServiceConditions,
        many: bool = False,
        partial: bool = False,
    ) -> ApiMatchExpression | None:
        if not data:
            return None

        def _remove_regex_dict(_entry):
            if isinstance(_entry, dict) and "$regex" in _entry:
                regex = _entry["$regex"]
                if self.use_regex == "adaptive" and regex:
                    if regex[0] == "^":
                        return "~" + regex[1:]

                    return "~" + regex

                return regex

            if isinstance(_entry, str):
                return _entry

            raise ValidationError(f"Unknown format: {_entry}")

        def _ensure_list(_entry) -> list[str]:  # type: ignore[no-untyped-def]
            if isinstance(_entry, list):
                return _entry

            return [_entry]

        rv: ApiMatchExpression = {
            "match_on": [],
            "operator": "one_of",
        }
        if isinstance(data, dict):
            try:
                entries = _ensure_list(_unpack_value(data))
            except ValueError as exc:
                raise ValidationError(str(exc)) from exc
            rv["operator"] = _unpack_operator(data)
        else:
            entries = _ensure_list(data)

        rv["match_on"] = [_remove_regex_dict(entry) for entry in entries]

        return rv

    @post_load(pass_many=False)
    def convert_to_checkmk(
        self,
        data: ApiMatchExpression,
        many: bool = False,
        partial: bool = False,
    ) -> HostOrServiceConditions:
        def _wrap_entry(_entry):
            if _entry[0] == "~":
                return {"$regex": f"^{_entry[1:]}"}

            return _entry

        match_on: HostOrServiceConditionsSimple
        if self.use_regex == "always":
            match_on = [{"$regex": entry} for entry in data["match_on"]]
        elif self.use_regex == "adaptive":
            match_on = [_wrap_entry(entry) for entry in data["match_on"]]
        elif isinstance(data["match_on"], list):
            match_on = cast(HostOrServiceConditionsSimple, data["match_on"])
        else:
            raise ValidationError(f"Unknown type: {data['match_on']!r}.")

        if data["operator"] == "one_of":
            return match_on
        elif data["operator"] == "none_of":
            return {"$nor": match_on}
        else:
            raise ValidationError(f"Unknown match type: {data['operator']}")


class Properties(base.BaseSchema):
    cast_to_dict = True

    description = fields.String(
        description="A description for this rule to inform other users about its intent.",
        example="This rule is here to foo the bar hosts.",
    )
    comment = fields.String(
        description="Any comment string.",
        example="Created yesterday due to foo hosts behaving weird.",
    )
    documentation_url = fields.URL(
        attribute="docu_url",
        description="An URL (e.g. an internal Wiki entry) which explains this rule.",
        example="http://example.com/wiki/ConfiguringFooBarHosts",
    )
    disabled = fields.Boolean(
        description="When set to False, the rule will be evaluated. Default is False.",
        example=False,
        load_default=False,
    )


class LabelCondition(base.BaseSchema):
    """A schema representing a label condition.
    The label is connected to other labels (within one label group condition) via one of
    the boolean operators {"and", "or", "not"}"""

    operator = fields.String(
        enum=["and", "or", "not"],
        description="Boolean operator that connects the label to other labels within the same "
        "label group condition",
    )
    label = fields.String(
        required=True, description='A label of format "{key}:{value}"', example="os:windows"
    )


class LabelGroupCondition(base.BaseSchema):
    """A schema representing a label group condition.
    The label group (i.e. a list of label conditions) is connected to other label groups via one
    of the boolean operators {"and", "or", "not"}"""

    operator = fields.String(
        enum=["and", "or", "not"],
        description="Boolean operator that connects the label group to other label groups",
        load_default="and",
    )
    label_group = fields.List(
        fields.Nested(LabelCondition),
        minLength=1,
        required=True,
        description="A list of label conditions that form a label group",
        example=[{"operator": "and", "label": "os:linux"}],
    )


class Conditions(base.BaseSchema):
    cast_to_dict = True

    host_name = fields.Nested(
        HostOrServiceConditionSchema,
        many=False,
        description=(
            "Here you can enter a list of explicit host names that the rule should or should "
            "not apply to. "
            "Leave this option disabled if you want the rule to apply for all hosts specified "
            "by the given tags. The names that you enter here are compared with case sensitive "
            "exact matching. Alternatively you can use regular expressions if you enter a "
            "tilde `~` as the first character. That regular expression must match the beginning "
            "of the host names in question."
        ),
        example={"match_on": ["host1", "host2"], "operator": "one_of"},
    )
    host_tags = fields.Nested(
        TagConditionSchema,
        many=True,
        description=(
            "The rule will only be applied to hosts fulfilling all the host tag conditions "
            "listed here, even if they appear in the list of explicit host names."
        ),
        example=[{"key": "criticality", "operator": "is", "value": "prod"}],
    )
    host_label_groups = fields.List(
        fields.Nested(LabelGroupCondition),
        description="Further restrict this rule by applying host label conditions. Although all items in this list"
        " have a default operator value, the operator value for the the first item in the list does not have any effect.",
        example=[
            {
                "label_group": [
                    {
                        "operator": "and",
                        "label": "db:mssql",
                    }
                ],
            },
            {
                "operator": "and",
                "label_group": [
                    {
                        "operator": "and",
                        "label": "os:windows",
                    }
                ],
            },
        ],
    )
    service_label_groups = fields.List(
        fields.Nested(LabelGroupCondition),
        description="Restrict the application of the rule, by checking against service label conditions. Although all items in"
        " this list have a default operator value, the operator value for the the first item in the list does not have any effect.",
        example=[
            {
                "label_group": [
                    {
                        "operator": "and",
                        "label": "db:mssql",
                    }
                ],
            },
            {
                "operator": "and",
                "label_group": [
                    {
                        "operator": "and",
                        "label": "os:windows",
                    }
                ],
            },
        ],
    )
    service_description = fields.Nested(
        HostOrServiceConditionSchema(use_regex="always"),
        many=False,
        description=(
            "Specify a list of service patterns this rule shall apply to.\n"
            " * The patterns must match the beginning of the service in question.\n"
            " * Adding a `$` to the end forces an exact match.\n"
            " * Pattern use regular expressions. e.g. a `.*` will match an arbitrary text.\n"
            " * The text entered here is handled as a regular expression pattern.\n"
            " * The pattern is matched from the beginning.\n"
            " * The match is performed case sensitive.\n"
            "BE AWARE: Depending on the service ruleset the service_description of "
            "the rules is only a check item or a full service name. For "
            "example the check parameters rulesets only use the item, and other "
            "service rulesets like disabled services ruleset use full service"
            "descriptions."
        ),
        example={"match_on": ["foo1", "bar2"], "operator": "none_of"},
    )


class InputConditions(Conditions):
    """Additionally supports the old label format.

    The conversion of the format itself is done in `LabelConditionSchema`.
    """

    host_labels = fields.Nested(
        LabelConditionSchema,
        many=True,
        description=(
            "Further restrict this rule by applying host label conditions."
            " - Deprecated: Use `host_label_groups` instead."
        ),
        example=[{"key": "os", "operator": "is", "value": "windows"}],
        deprecated=True,
    )
    service_labels = fields.Nested(
        LabelConditionSchema,
        many=True,
        description=(
            "Restrict the application of the rule, by checking against service label conditions."
            " - Deprecated: Use `service_label_groups` instead."
        ),
        example=[{"key": "os", "operator": "is", "value": "windows"}],
        deprecated=True,
    )

    @post_load
    def _post_load(self, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        """To maintain backward compatibility. If we receive 'host_labels',
        or 'service_labels' we change the key to 'host_label_groups' or
        'service_label_groups' respectively."""

        if host_labels := data.pop("host_labels", None):
            data["host_label_groups"] = host_labels

        if service_labels := data.pop("service_labels", None):
            data["service_label_groups"] = service_labels

        return data

    @validates_schema
    def _validate_labels(self, data: dict[str, Any], **kwargs: Any) -> None:
        """We allow host_labels (old) or host_label_groups (new), not both.
        We allow service_labels (old) or service_label_groups (new), not both."""

        if data.get("host_labels") and data.get("host_label_groups"):
            raise ValidationError(
                "Please provide the field 'host_labels' OR 'host_label_groups', not both."
            )

        if data.get("service_labels") and data.get("service_label_groups"):
            raise ValidationError(
                "Please provide the field 'service_labels' OR 'service_label_groups', not both."
            )


class RuleExtensions(base.BaseSchema):
    """Serializes the 'extensions' part of the Rule Domain Object.

        Examples:

            >>> ext = RuleExtensions()
            >>> from cmk.gui.utils.script_helpers import application_and_request_context
            >>> from cmk.gui.livestatus_utils.testing import mock_site
            >>> with mock_site(), application_and_request_context():
            ...     ext.load({
            ...        'folder': '/',
            ...     })
            {'folder': Folder('', 'Main')}

            >>> with mock_site(), application_and_request_context():
            ...     rv = ext.load({
            ...        'folder': '/',
            ...        'conditions': {
            ...            'service_description': {'match_on': ['foo'],
            ...                                               'operator': 'none_of',},
            ...            'host_tags': [{'key': 'criticality', 'operator': 'is', 'value': 'prod'}],
            ...        }
            ...     })
            ...     rv
            {'folder': Folder('', 'Main'), \
'conditions': {\
'host_tags': {'criticality': 'prod'},\
 'service_description': {'$nor': [{'$regex': 'foo'}]}\
}}

            >>> ext.dump(rv)
            {'folder': '/', 'conditions': {\
'host_tags': [{'key': 'criticality', 'operator': 'is', 'value': 'prod'}], \
'service_description': {'match_on': ['foo'], 'operator': 'none_of'}}}

        """

    cast_to_dict = True

    ruleset = fields.String(description="The name of the ruleset.")
    folder = gui_fields.FolderField(required=True, example="~router")
    folder_index = fields.Integer(
        description="The position of this rule in the chain in this folder.",
    )
    properties = fields.Nested(
        Properties,
        description="Property values of this rule.",
        example={},
    )
    value_raw = fields.String(
        description="The raw parameter value for this rule.",
        example='{"ignore_fs_types": ["tmpfs"]}',
    )
    conditions = fields.Nested(
        Conditions,
        description="Conditions.",
    )


class RuleObject(response_schemas.DomainObject):
    """The schema for sending data TO the API client.

    For the schema responsible for receiving data, see `InputRuleObject`.
    """

    domainType = fields.Constant(
        "rule",
        description="Domain type of this object.",
        example="rule",
    )
    extensions = fields.Nested(
        RuleExtensions,
        description="Attributes specific to rule objects.",
    )


class RuleCollection(response_schemas.DomainObjectCollection):
    domainType = fields.Constant(
        "rule",
        description="Domain type of this object.",
    )
    value: fields.Field = fields.Nested(
        RuleObject,
        description="The collection itself. Each entry in here is part of the collection.",
        many=True,
    )


class UpdateRuleObject(base.BaseSchema):
    """A schema to validate the values coming from the API clients.

    Examples:

        >>> s = UpdateRuleObject()
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.livestatus_utils.testing import mock_site
        >>> with mock_site(), application_and_request_context():
        ...     rv = s.load({
        ...         'properties': {'disabled': False},
        ...         'conditions': {
        ...              'host_name': {
        ...                  'match_on': ['example.com', 'heute'],
        ...                  'operator': 'one_of',
        ...              },
        ...              'host_label_groups': [
        ...                   {"operator": "and", "label_group": [{"operator": "and", "label": "os:windows"}]},
        ...              ],
        ...              'host_tags': [
        ...                  {'key': 'criticality', 'operator': 'is_not', 'value': 'prod'},
        ...                  {'key': 'foo', 'operator': 'is_not', 'value': 'testing'},
        ...              ],
        ...         },
        ...         'value_raw': '''{"ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"], "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"]}''',
        ...     })
        >>> rv
        {'properties': {'disabled': False}, \
'value_raw': {'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'], 'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']}, \
'conditions': {\
'host_name': ['example.com', 'heute'], \
'host_tags': {'criticality': {'$ne': 'prod'}, 'foo': {'$ne': 'testing'}}, \
'host_label_groups': [{'operator': 'and', 'label_group': [{'operator': 'and', 'label': 'os:windows'}]}]}}

        >>> s.dump(rv)
        {'properties': {'disabled': False}, \
'value_raw': "{'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'], 'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']}", \
'conditions': {\
'host_name': {'match_on': ['example.com', 'heute'], 'operator': 'one_of'}, \
'host_tags': [{'key': 'criticality', 'operator': 'is_not', 'value': 'prod'}, {'key': 'foo', 'operator': 'is_not', 'value': 'testing'}], \
'host_label_groups': [{'operator': 'and', 'label_group': [{'operator': 'and', 'label': 'os:windows'}]}]}}

    """

    cast_to_dict = True

    properties = fields.Nested(
        Properties,
        description="Configuration values for rules.",
        example={"disabled": False},
    )
    value_raw = gui_fields.PythonString(
        description=(
            "The raw parameter value for this rule. To create the correct structure, for now use "
            "the 'export for API' menu item in the Rule Editor of the GUI. The value is expected "
            "to be a valid Python type."
        ),
        example="{'cmk/os_family': 'linux'}",
        required=True,
    )
    conditions = fields.Nested(
        InputConditions,
        description="Conditions.",
        example={
            "host_name": {"match_on": ["host1", "host2"], "operator": "one_of"},
            "host_tags": [{"key": "criticality", "operator": "is", "value": "prod"}],
            "host_labels": [{"key": "os", "operator": "is", "value": "windows"}],
            "service_labels": [{"key": "os", "operator": "is", "value": "windows"}],
            "host_label_groups": [
                {
                    "operator": "and",
                    "label_group": [{"operator": "and", "label": "os:windows"}],
                }
            ],
            "service_label_groups": [
                {
                    "operator": "and",
                    "label_group": [{"operator": "and", "label": "os:windows"}],
                }
            ],
            "service_description": {"match_on": ["foo1", "bar2"], "operator": "none_of"},
        },
    )


class InputRuleObject(UpdateRuleObject):
    """A schema to validate the values coming from the API clients.

    Examples:

        >>> s = InputRuleObject()
        >>> from cmk.gui.utils.script_helpers import application_and_request_context
        >>> from cmk.gui.livestatus_utils.testing import mock_site
        >>> with mock_site(), application_and_request_context():
        ...     rv = s.load({
        ...         'folder': '~',
        ...         'ruleset': 'host',
        ...         'properties': {'disabled': False},
        ...         'conditions': {
        ...              'host_name': {
        ...                  'match_on': ['example.com', 'heute'],
        ...                  'operator': 'one_of',
        ...              },
        ...              'host_label_groups': [
        ...                   {"operator": "and", "label_group": [{"operator": "not", "label": "foo:bar"}]},
        ...              ],
        ...              'host_tags': [
        ...                  {'key': 'criticality', 'operator': 'is_not', 'value': 'prod'},
        ...                  {'key': 'foo', 'operator': 'is_not', 'value': 'testing'},
        ...              ],
        ...         },
        ...         'value_raw': '''{"ignore_fs_types": ["tmpfs", "nfs", "smbfs", "cifs", "iso9660"], "never_ignore_mountpoints": ["~.*/omd/sites/[^/]+/tmp$"]}''',
        ...     })
        >>> rv
        {'properties': {'disabled': False}, \
'value_raw': {'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'], 'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']}, \
'conditions': {\
'host_name': ['example.com', 'heute'], \
'host_tags': {'criticality': {'$ne': 'prod'}, 'foo': {'$ne': 'testing'}}, \
'host_label_groups': [{'operator': 'and', 'label_group': [{'operator': 'not', 'label': 'foo:bar'}]}]}, \
'ruleset': 'host', 'folder': Folder('', 'Main')}
        >>> rv['folder'].path()
        ''

        >>> s.dump(rv)
        {'properties': {'disabled': False}, \
'value_raw': "{'ignore_fs_types': ['tmpfs', 'nfs', 'smbfs', 'cifs', 'iso9660'], 'never_ignore_mountpoints': ['~.*/omd/sites/[^/]+/tmp$']}", \
'conditions': {\
'host_name': {'match_on': ['example.com', 'heute'], 'operator': 'one_of'}, \
'host_tags': [{'key': 'criticality', 'operator': 'is_not', 'value': 'prod'}, {'key': 'foo', 'operator': 'is_not', 'value': 'testing'}], \
'host_label_groups': [{'operator': 'and', 'label_group': [{'operator': 'not', 'label': 'foo:bar'}]}]}, \
'ruleset': 'host', 'folder': '/'}

    """

    cast_to_dict = True

    ruleset = fields.String(
        description="Name of rule set.",
        example="host_label_rules",
        required=True,
    )
    folder = gui_fields.FolderField(required=True, example="~hosts~linux")


def _unpack_value(
    v: str | TagCondition | HostOrServiceConditionsNegated,
) -> ApiExpressionValue | None:
    """Unpacks the value from a condition value

    Examples:

        >>> _unpack_value({'$ne': 'Beavis'})
        'Beavis'

        >>> _unpack_value("Beavis")
        'Beavis'

        >>> _unpack_value(None)


        >>> _unpack_value({'foo': 'bar'})  # type: ignore[arg-type]
        Traceback (most recent call last):
        ...
        ValueError: Unknown operator: {'foo': 'bar'}

    """
    rv: ApiExpressionValue | None
    if isinstance(v, dict):
        if len(v) == 1 and any(op in v for op in ["$ne", "$or", "$nor"]):
            # TODO: un-$regex the value? Not supported?
            # Type is so diverse (Unions) that mypy only has object to fall back to. :-(
            rv = cast(ApiExpressionValue, next(iter(v.values())))
        else:
            raise ValueError(f"Unknown operator: {v}")
    elif isinstance(v, str):
        rv = v
    elif v is None:
        rv = v
    else:
        rv = v

    return rv


def _scalar_value(
    value: ApiExpressionValue,
    operator: ApiOperator,
) -> str | TagConditionNE:
    """Constructs a scalar value or the negation of it

    Examples:

        >>> _scalar_value("foo", "is")
        'foo'

        >>> _scalar_value("foo", "is_not")
        {'$ne': 'foo'}

        Stuff that won't work:

        >>> _scalar_value("foo", "one_of")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Unsupported scalar operator: one_of ...

        >>> _scalar_value(['foo'], "is")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Unsupported data type: ...

    Args:
        value:
        operator:

    Returns:

    """
    if not isinstance(value, str):
        raise ValidationError(f"Unsupported data type: {value!r}")

    if operator == "is":
        return value
    elif operator == "is_not":
        return {"$ne": TagID(value)}
    else:
        raise ValidationError(f"Unsupported scalar operator: {operator} {value!r}")


def _collection_value(
    value: ApiExpressionValue,
    operator: ApiOperator,
) -> TagCondition:
    """Constructs one of Checkmk's condition values

    Examples:

        >>> _collection_value(["Beavis", "Butthead"], "one_of")
        {'$or': ['Beavis', 'Butthead']}

        >>> _collection_value(["Beavis", "Butthead"], "none_of")
        {'$nor': ['Beavis', 'Butthead']}

        Stuff that won't work:

        >>> _collection_value(["Beavis", "Butthead"], "is")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Unsupported list operator: is ...

        >>> _collection_value("Hello", "none_of")  # doctest: +ELLIPSIS
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Unsupported data type: ...

    """
    if not isinstance(value, list):
        raise ValidationError(f"Unsupported data type: {value!r}")

    if operator == "one_of":
        return {"$or": [TagID(v) for v in value]}
    elif operator == "none_of":
        return {"$nor": [TagID(v) for v in value]}
    else:
        raise ValidationError(f"Unsupported list operator: {operator} {value!r}")


class RuleSearchOptions(base.BaseSchema):
    ruleset_name = fields.String(
        description="The name of the ruleset.",
        example="host_groups",
        required=True,
    )


def _unpack_operator(v: HostOrServiceConditions) -> ApiOperator:
    """Unpacks the operator from a condition value

    Examples:

        >>> _unpack_operator({"$nor": ["Beavis", "Butthead"]})
        'none_of'

        >>> _unpack_operator({"$or": ["Beavis", "Butthead"]})
        'one_of'

        >>> _unpack_operator({"$ne": "Beavis"})
        'is_not'

        >>> _unpack_operator("Beavis")
        'is'

        >>> _unpack_operator(None)
        'is'

        >>> _unpack_operator({"foo": "bar"})
        Traceback (most recent call last):
        ...
        marshmallow.exceptions.ValidationError: Unknown operator: 'foo'
    """
    if isinstance(v, dict):
        _key = next(iter(v.keys()))
        # Thank you pylint, but these things need to be returned like this,
        # because otherwise mypy won't recognize the Literal values.
        if _key == "$ne":
            return "is_not"
        elif _key == "$or":
            return "one_of"
        elif _key == "$nor":
            return "none_of"
        else:
            raise ValidationError(f"Unknown operator: {_key!r}")

    return "is"
