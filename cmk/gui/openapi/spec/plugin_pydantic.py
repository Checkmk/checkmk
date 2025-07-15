#!/usr/bin/env python3
# Copyright (C) 2021 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import contextlib
import hashlib
import warnings
from collections.abc import Callable, Iterator, Sequence
from dataclasses import is_dataclass
from typing import Any, cast, ClassVar, is_typeddict, Literal

import apispec
import pydantic_core
from apispec import APISpec
from apispec.exceptions import DuplicateComponentNameError
from pydantic import BaseModel, PydanticInvalidForJsonSchema, TypeAdapter
from pydantic.json_schema import GenerateJsonSchema, JsonSchemaValue, PydanticJsonSchemaWarning
from pydantic_core import core_schema, PydanticOmit, PydanticSerializationError

from cmk.utils.object_diff import make_diff

from cmk.gui.openapi.framework.model.omitted import ApiOmitted

type Direction = Literal["inbound", "outbound"]

# these two are not publicly exported by pydantic, so we redefine them here
type _CoreSchemaField = (
    core_schema.ModelField
    | core_schema.DataclassField
    | core_schema.TypedDictField
    | core_schema.ComputedField
)
type _CoreSchemaOrField = core_schema.CoreSchema | _CoreSchemaField


def _try_get_title(schema: core_schema.CoreSchema) -> str | None:
    if schema["type"] == "definitions":
        return _try_get_title(schema["schema"])
    if "config" in schema and "title" in schema["config"]:
        return schema["config"]["title"]
    if "cls_name" in schema:
        return schema["cls_name"]
    if "cls" in schema and isinstance(schema["cls"], type):
        return schema["cls"].__name__
    if "name" in schema:
        return schema["name"]

    return None


def _register_schema(spec: APISpec, name: str, schema: dict[str, object]) -> None:
    """Register a schema in the APISpec components.

    Adds some context in case there is a difference between the schemas.
    """
    if spec.components.schemas.get(name) != schema:
        try:
            spec.components.schema(name, schema)
        except DuplicateComponentNameError as e:
            diff = make_diff(spec.components.schemas[name], schema)
            raise DuplicateComponentNameError(f"{e}\nNew: {schema!r}\nDiff:\n{diff}") from None


def _get_json_schema(
    spec: APISpec, adapter: TypeAdapter, direction: Direction
) -> dict[str, object]:
    # There's a difference in pydantic between inbound and outbound schemas. Validators only affect
    # inbound schemas, and often the serialization won't even be supported by the custom types.
    # At the same time, we don't want to specify validators for outbound schemas (or vice versa).
    # So we need to know the direction every time we generate a schema.
    # If there are inconsistencies between the inbound and outbound schemas, an error will be raised
    # when the schema is registered (in this function). Shared schemas should allow for round trip
    # serialization, so the inbound and outbound schemas should be the same. The most likely fix is
    # to either add a validator or `WithJsonSchema(..., mode="serialization")` to the field.
    try:
        with warnings.catch_warnings(action="error", category=PydanticJsonSchemaWarning):
            json_schema = adapter.json_schema(
                by_alias=True,
                ref_template="#/components/schemas/{model}",
                schema_generator=CheckmkGenerateJsonSchema,
                mode="serialization" if direction == "outbound" else "validation",
            )
    except PydanticJsonSchemaWarning as e:
        title = _try_get_title(adapter.core_schema) or "<unknown>"
        raise PydanticJsonSchemaWarning(f"{title}: {e}") from None

    # The schema names must be unique, otherwise an error will be raised on registration. This is
    # good, because we don't want to have references to the wrong schema elsewhere. The solution
    # should be to rename the classes so that they are unique, not to suppress the error.
    # It is possible that a (different) plugin modifies the schema after registration, which would
    # cause the newly generated schema to be different from the one that was registered. This
    # shouldn't be a problem from a spec perspective, but would mean we somehow need to know that
    # they came from the same type adapter.

    if defs := json_schema.pop("$defs", None):
        assert isinstance(defs, dict)
        for k, v in defs.items():
            _register_schema(spec, k, v)

    name = json_schema.get("title")
    assert isinstance(name, str), f"Expected title for schema: {json_schema!r}"
    _register_schema(spec, name, json_schema)

    return json_schema


class CheckmkGenerateJsonSchema(GenerateJsonSchema):
    """Customized JSON schema generator.

    In order to generate the correct schema, we need to:
     * mark fields as optional if they contain `ApiOmitted` as an option
     * update default handling, by:
       * supporting `default_factory`
       * handling `ApiOmitted` as a default value
    """

    def __init__(self, by_alias: bool, ref_template: str) -> None:
        super().__init__(by_alias, ref_template)
        # track the current path in the schema, so that we can raise helpful errors
        self._path: list[str] = []

    ignored_warning_kinds = set()  # we don't want to ignore any warnings

    def handle_invalid_for_json_schema(
        self, schema: _CoreSchemaOrField, error_info: str
    ) -> JsonSchemaValue:
        # include the model/field name in the error message
        raise PydanticInvalidForJsonSchema(
            f"Cannot generate a JsonSchema for {'.'.join(self._path)}: {error_info}"
        )

    def _contains_omitted(self, schema: core_schema.CoreSchema) -> bool:
        match schema["type"]:
            case "is-instance":
                return schema["cls"] is ApiOmitted
            case "default" | "nullable":
                return self._contains_omitted(schema["schema"])
            case "union":
                return any(self._contains_omitted(inner) for inner in schema["choices"])
            case "tagged-union":
                return any(self._contains_omitted(inner) for inner in schema["choices"].values())

        return False

    def field_is_required(
        self,
        field: core_schema.ModelField | core_schema.DataclassField | core_schema.TypedDictField,
        total: bool,
    ) -> bool:
        if self._contains_omitted(field["schema"]):
            if field["schema"]["type"] != "default":
                # This only really matters for inputs, but there is no way to know for what this
                # will be used. So we just forbid it completely.
                raise ValueError(f"Omittable field without default value: {field}")

            return False

        return super().field_is_required(field, total)

    def default_schema(self, schema: core_schema.WithDefaultSchema) -> JsonSchemaValue:
        """Generates a JSON schema that matches a schema with a default value.

        This is mostly copied from the base class, changes are marked with comments."""
        json_schema = self.generate_inner(schema["schema"])

        # changed: we also check default_factory
        if "default" in schema:
            default = schema["default"]
        elif "default_factory" in schema:
            if schema.get("default_factory_takes_data"):
                default = cast(Callable[[dict[str, Any]], Any], schema["default_factory"])({})
            else:
                default = cast(Callable[[], Any], schema["default_factory"])()
        else:
            return json_schema

        # changed: we return early if the default is ApiOmitted, as it cannot be serialized
        if isinstance(default, ApiOmitted):
            return json_schema

        # we reflect the application of custom plain, no-info serializers to defaults for
        # JSON Schemas viewed in serialization mode:
        if (
            self.mode == "serialization"
            and (ser_schema := schema["schema"].get("serialization"))
            and (ser_func := ser_schema.get("function"))
            and ser_schema.get("type") == "function-plain"
            and not ser_schema.get("info_arg")
            and not (
                default is None
                and ser_schema.get("when_used") in ("unless-none", "json-unless-none")
            )
        ):
            try:
                default = ser_func(default)
            except Exception:
                # It might be that the provided default needs to be validated (read: parsed) first
                # (assuming `validate_default` is enabled). However, we can't perform
                # such validation during JSON Schema generation so we don't support
                # this pattern for now.
                # (One example is when using `foo: ByteSize = '1MB'`, which validates and
                # serializes as an int. In this case, `ser_func` is `int` and `int('1MB')` fails).
                self.emit_warning(
                    "non-serializable-default",
                    f"Unable to serialize value {default!r} with the plain serializer; excluding default from JSON schema",
                )
                return json_schema

        try:
            encoded_default = self.encode_default(default)
        except PydanticSerializationError:
            self.emit_warning(
                "non-serializable-default",
                f"Default value {default} is not JSON serializable; excluding default from JSON schema",
            )
            # Return the inner schema, as though there was no default
            return json_schema

        json_schema["default"] = encoded_default
        return json_schema

    def encode_default(self, dft: Any) -> Any:
        type_ = type(dft)
        config = self._config
        adapter = TypeAdapter(  # nosemgrep: type-adapter-detected
            type_,
            config=(
                None  # can't set config if the type itself supports configs
                if issubclass(type_, BaseModel) or is_dataclass(type_) or is_typeddict(type_)
                else config.config_dict
            ),
        )

        # We exclude defaults, because that's how omitted values are removed.
        return pydantic_core.to_jsonable_python(
            adapter.dump_python(dft, mode="json", by_alias=True, exclude_defaults=True),
            timedelta_mode=config.ser_json_timedelta,
            bytes_mode=config.ser_json_bytes,
        )

    def _named_required_fields_schema(
        self, named_required_fields: Sequence[tuple[str, bool, _CoreSchemaField]]
    ) -> JsonSchemaValue:
        # NOTE: the only change here is that we modify self._path
        properties: dict[str, JsonSchemaValue] = {}
        required_fields: list[str] = []
        for name, required, field in named_required_fields:
            self._path.append(name)
            if self.by_alias:
                name = self._get_alias_name(field, name)
            try:
                field_json_schema = self.generate_inner(field).copy()
            except PydanticOmit:
                self._path.pop()
                continue
            self._path.pop()
            if "title" not in field_json_schema and self.field_title_should_be_set(field):
                title = self.get_title_from_name(name)
                field_json_schema["title"] = title
            field_json_schema = self.handle_ref_overrides(field_json_schema)
            properties[name] = field_json_schema
            if required:
                required_fields.append(name)

        json_schema = {"type": "object", "properties": properties}
        if required_fields:
            json_schema["required"] = required_fields
        return json_schema

    @contextlib.contextmanager
    def _replace_path(self, schema: core_schema.CoreSchema) -> Iterator[None]:
        """Replace the current path with the schema title or class name.

        This is used to provide better error messages when generating JSON schemas.
        """
        old_path = self._path
        self._path = [_try_get_title(schema) or "<unknown>"]
        yield
        self._path = old_path

    def typed_dict_schema(self, schema: core_schema.TypedDictSchema) -> JsonSchemaValue:
        with self._replace_path(schema):
            return super().typed_dict_schema(schema)

    def model_schema(self, schema: core_schema.ModelSchema) -> JsonSchemaValue:
        with self._replace_path(schema):
            return super().model_schema(schema)

    def dataclass_schema(self, schema: core_schema.DataclassSchema) -> JsonSchemaValue:
        with self._replace_path(schema):
            return super().dataclass_schema(schema)


class CheckmkPydanticResolver:
    """SchemaResolver is responsible for modifying a schema.

    This class relies heavily on the fact that dictionaries are mutable,
    so rather than catching a return value, we can often modify the object without
    a return statement.
    """

    # (TypeAdapter id, direction) -> (schema_name, schema)
    refs: ClassVar[dict[tuple[int, Direction], tuple[str, dict[str, object]]]] = {}

    def __init__(self, spec: apispec.APISpec) -> None:
        self.spec = spec

    def resolve_nested_schema(
        self, maybe_adapter: TypeAdapter | object, direction: Direction
    ) -> object:
        if isinstance(maybe_adapter, TypeAdapter):
            schema_name, _ = self.get_cached_adapter_schema(maybe_adapter, direction)
            return {"$ref": f"#/components/schemas/{schema_name}"}

        # do not touch other cases, as they should in most cases be Marshmallow schemas
        return maybe_adapter

    def get_cached_adapter_schema(
        self, adapter: TypeAdapter, direction: Direction
    ) -> tuple[str, dict[str, object]]:
        key = id(adapter), direction
        if key not in self.refs:
            json_schema = _get_json_schema(self.spec, adapter, direction)
            if "title" in json_schema:
                title = json_schema["title"]
                assert isinstance(title, str)
                schema_name = title
            else:
                sha = hashlib.sha256()
                sha.update(str(json_schema).encode("utf-8"))
                schema_name = sha.hexdigest()
                warnings.warn("Pydantic plugin got schema without title, using hash of schema")

            self.refs[key] = schema_name, json_schema

        return self.refs[key]

    def resolve_schema(self, data: dict[str, Any] | Any, direction: Direction) -> None:
        """Resolves a Pydantic model in an OpenAPI component or header.

        This method modifies the input dictionary, data, to translate
        Pydantic models to OpenAPI schema objects or reference objects.
        """
        if not isinstance(data, dict):
            return

        # OAS 2 component or OAS 3 parameter or header
        if "schema" in data:
            data["schema"] = self.resolve_schema_dict(data["schema"], direction)

        # OAS 3 component except header
        if self.spec.openapi_version.major >= 3 and "content" in data:
            for content in data["content"].values():
                if "schema" in content:
                    content["schema"] = self.resolve_schema_dict(content["schema"], direction)

    def resolve_operations(
        self,
        operations: dict[str, object] | None,
        **kwargs: Any,
    ) -> None:
        """Resolves an operations dictionary into an OpenAPI operations object.

        https://spec.openapis.org/oas/v3.1.0#operation-object

        Args:
            operations (dict[str, Any] | None): The operations for a specific route,
                if documented.

                Example:
                {
                    'get': {
                        'description': 'Create a network quiet time announcement',
                        'tags': ['Announcements'],
                        'requestBody': {
                            'description': 'The details of the Network Quiet Time',
                            'content': {
                                'application/json': {
                                    'schema': 'CreateNetworkQuietTimeRequest'
                                }
                            }
                        },
                        'responses': {
                            '200': {
                                'description': 'Announcement successfully created.',
                                'content': {
                                    'application/json': {
                                        'schema': 'SerializedAnnouncement'
                                    }
                                }
                            },
                            '400': {
                                'description': 'An invalid request was received.',
                                'content': {'application/json': { 'schema': 'Problem'}}
                            },
                            '403': {
                                'description': 'The user was not authorized to perform this action.',
                                'content': {'application/json': {'schema': 'Problem'}}
                            },
                            '500': {
                                'description': 'An unexpected error occurred while retrieving the announcements',
                                'content': {'application/json': {'schema': 'Problem'}}
                            }
                        }
                    }
                }
        """
        if operations is None:
            return

        for operation in operations.values():
            if not isinstance(operation, dict):
                continue

            if "parameters" in operation:
                operation["parameters"] = self.resolve_parameters(operation["parameters"])
            if self.spec.openapi_version.major >= 3:
                self.resolve_callback(operation.get("callbacks", {}))
                if "requestBody" in operation:
                    self.resolve_schema(operation["requestBody"], direction="inbound")
            for response in operation.get("responses", {}).values():
                self.resolve_response(response)

    def resolve_parameters(
        self, parameters: Sequence[dict[str, object]]
    ) -> Sequence[dict[str, object]]:
        for parameter in parameters:
            if "schema" in parameter:
                schema = parameter["schema"]
                if isinstance(schema, TypeAdapter):
                    _, parameter["schema"] = self.get_cached_adapter_schema(
                        schema, direction="inbound"
                    )

            # TODO: might need to do this, when we remove the marshmallow plugin
            #       but while we still have marshmallow this might break the plugin
            # wrap object parameters in content.application/json to keep them as str/json in swagger
            # see: https://swagger.io/docs/specification/describing-parameters/#schema-vs-content
            # if "type" not in parameter["schema"]:
            #     content = parameter.setdefault("content", {}).setdefault("application/json", {})
            #     content["schema"] = parameter.pop("schema")

        return parameters

    def resolve_callback(self, callbacks: Any) -> None:
        for callback in callbacks.values():
            if isinstance(callback, dict):
                for path in callback.values():
                    self.resolve_operations(path)

    def resolve_response(self, response: Any) -> None:
        self.resolve_schema(response, direction="outbound")
        if "headers" in response:
            for header in response["headers"].values():
                self.resolve_schema(header, direction="outbound")

    def resolve_schema_dict(
        self, schema: dict | TypeAdapter | object, direction: Direction
    ) -> object:
        """Resolve the schemas and ignore anything which is not related to the Pydantic plugin
        such as Marshmallow schemas, etc.
        """
        if not isinstance(schema, dict):
            return self.resolve_nested_schema(schema, direction)

        if schema.get("type") == "array" and "items" in schema:
            schema["items"] = self.resolve_schema_dict(schema["items"], direction)
        if schema.get("type") == "object" and "properties" in schema:
            schema["properties"] = {
                k: self.resolve_schema_dict(v, direction) for k, v in schema["properties"].items()
            }
        for keyword in ("oneOf", "anyOf", "allOf"):
            if keyword in schema:
                schema[keyword] = [self.resolve_schema_dict(s, direction) for s in schema[keyword]]
        if "not" in schema:
            schema["not"] = self.resolve_schema_dict(schema["not"], direction)
        return schema


class CheckmkPydanticPlugin(apispec.BasePlugin):
    """APISpec plugin for translating pydantic models to OpenAPI/JSONSchema format."""

    spec: apispec.APISpec | None
    resolver: CheckmkPydanticResolver | None

    def __init__(self) -> None:
        self.spec = None
        self.resolver = None

    def init_spec(self, spec: apispec.APISpec) -> None:
        """Initialize plugin with APISpec object

        Args:
            spec: APISpec object this plugin instance is attached to
        """
        super().init_spec(spec=spec)
        self.spec = spec
        self.resolver = CheckmkPydanticResolver(spec=self.spec)

    def operation_helper(
        self,
        path: str | None = None,
        operations: dict[str, object] | None = None,
        **kwargs: Any,
    ) -> None:
        if self.resolver is None:
            raise ValueError("SchemaResolver was not initialized")
        self.resolver.resolve_operations(operations=operations, kwargs=kwargs)
