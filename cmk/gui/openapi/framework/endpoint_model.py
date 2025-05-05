#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import dataclasses
import inspect
from collections.abc import Callable, Mapping, Sequence
from typing import (
    Annotated,
    cast,
    get_args,
    get_origin,
    Literal,
    Self,
    TypedDict,
)

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError, with_config
from pydantic_core import InitErrorDetails

from cmk.gui.openapi.framework._types import (
    DataclassInstance,
    HeaderParam,
    PathParam,
    QueryParam,
    RawRequestData,
)
from cmk.gui.openapi.framework.content_types import convert_request_body
from cmk.gui.openapi.framework.model.api_field import api_field
from cmk.gui.openapi.framework.model.response import ApiResponse, TypedResponse
from cmk.gui.openapi.restful_objects.validators import RequestDataValidator

type ApiInputModel[T: type[DataclassInstance]] = T
"""Dataclass with optional fields: body, path, query, headers
This is an implementation detail of the endpoint wrapping, and should not be used elsewhere."""


@dataclasses.dataclass(frozen=True, slots=True)
class Parameter:
    annotation: type
    default: object  # dataclasses.MISSING if there is no default
    description: str
    example: str


@dataclasses.dataclass(frozen=True, slots=True)
class _QueryParameter(Parameter):
    is_list: bool = False


@dataclasses.dataclass(frozen=True, slots=True)
class Parameters:
    path: dict[str, Parameter] = dataclasses.field(default_factory=dict)
    query: dict[str, _QueryParameter] = dataclasses.field(default_factory=dict)
    headers: dict[str, Parameter] = dataclasses.field(default_factory=dict)
    query_aliases: dict[str, str] = dataclasses.field(default_factory=dict)
    header_aliases: dict[str, str] = dataclasses.field(default_factory=dict)


def _request_body_type(signature: inspect.Signature) -> type | None:
    if "body" not in signature.parameters:
        return None
    parameter = signature.parameters["body"]
    if parameter.annotation is inspect.Parameter.empty:
        return None
    return parameter.annotation


def _return_type(signature: inspect.Signature) -> type | None:
    if signature.return_annotation is inspect.Signature.empty:
        return None
    annotation = signature.return_annotation
    if get_origin(annotation) in (TypedResponse, ApiResponse):
        return get_args(annotation)[0]
    return annotation


def _parameter_default(parameter: inspect.Parameter) -> object:
    if parameter.default is inspect.Parameter.empty:
        return dataclasses.MISSING
    return parameter.default


SourceAnnotation = PathParam | HeaderParam | QueryParam


@dataclasses.dataclass(frozen=True, slots=True)
class ParameterInfo:
    annotation: type
    default: object
    kind: inspect._ParameterKind
    sources: Sequence[SourceAnnotation]


def _collect_sources(type_: type) -> Sequence[SourceAnnotation]:
    if get_origin(type_) is Annotated:
        return [
            annotation
            for annotation in get_args(type_)
            if isinstance(annotation, (PathParam | HeaderParam | QueryParam))
        ]
    return []


class SignatureParametersProcessor:
    @staticmethod
    def extract_annotated_parameters(signature: inspect.Signature) -> Mapping[str, ParameterInfo]:
        parsed_params: dict[str, ParameterInfo] = {}

        for name, parameter in signature.parameters.items():
            if name == "body":
                continue

            param_info = ParameterInfo(
                kind=parameter.kind,
                annotation=parameter.annotation,
                default=_parameter_default(parameter),
                sources=_collect_sources(parameter.annotation),
            )
            parsed_params[name] = param_info
        return parsed_params

    @staticmethod
    def validate_parameters(parsed_params: Mapping[str, ParameterInfo]) -> None:
        header_names = set()
        query_names = set()
        header_aliases = set()
        query_aliases = set()

        for name, param_info in parsed_params.items():
            if param_info.annotation is inspect.Parameter.empty:
                raise ValueError(f"Missing parameter annotation for parameter '{name}'")

            if param_info.kind not in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            ):
                raise ValueError(f"Invalid parameter kind for parameter '{name}'")

            if not param_info.sources:
                raise ValueError(f"Parameter '{name}' is missing a source annotation")

            if len(param_info.sources) > 1:
                raise ValueError(f"Multiple sources for parameter '{name}'")

            source = param_info.sources[0]

            if isinstance(source, HeaderParam):
                # headers are case-insensitive, so we need to normalize the name and alias
                header_name = name.casefold()
                if header_name in header_names:
                    raise ValueError(
                        f"Duplicate header parameter (case-insensitive): {header_name}"
                    )
                header_names.add(header_name)

                if source.alias:
                    header_aliases.add(source.alias.casefold())

            elif isinstance(source, QueryParam):
                query_names.add(name)

                if source.alias:
                    query_aliases.add(source.alias)

        if duplicate := query_names & query_aliases:
            raise ValueError(f"Alias conflict in query parameters: {', '.join(duplicate)}")

        if duplicate := header_names & header_aliases:
            raise ValueError(f"Alias conflict in header parameters: {', '.join(duplicate)}")

    @staticmethod
    def parse_parameters(parsed_params: Mapping[str, ParameterInfo]) -> Parameters:
        path = {}
        query = {}
        headers = {}
        query_aliases = {}
        header_aliases = {}

        for name, param_info in parsed_params.items():
            source = param_info.sources[0]
            default = param_info.default
            match source:
                case PathParam(description=description, example=example):
                    path[name] = Parameter(
                        annotation=param_info.annotation,
                        default=default,
                        description=description,
                        example=example,
                    )
                case HeaderParam(alias=alias, description=description, example=example):
                    # headers are case-insensitive, so we need to normalize the name and alias
                    header_name = name.casefold()
                    headers[header_name] = Parameter(
                        annotation=param_info.annotation,
                        default=default,
                        description=description,
                        example=example,
                    )

                    if alias:
                        header_aliases[header_name] = alias.casefold()
                case QueryParam(
                    alias=alias, description=description, example=example, is_list=is_list
                ):
                    query[name] = _QueryParameter(
                        annotation=param_info.annotation,
                        default=default,
                        description=description,
                        example=example,
                        is_list=is_list,
                    )

                    if alias:
                        query_aliases[name] = alias
                case _:
                    raise ValueError(
                        f"Invalid parameter source type ({type(source)}) for parameter '{name}'"
                    )

        return Parameters(
            path=path,
            query=query,
            headers=headers,
            query_aliases=query_aliases,
            header_aliases=header_aliases,
        )


def _make_parameter_model(
    class_name: str,
    parameters: Mapping[str, Parameter],
    bases: tuple[type, ...],
) -> type:
    fields = [
        (
            name,
            parameter.annotation,
            api_field(
                default=parameter.default,
                description=parameter.description,
                example=parameter.example,
            ),
        )
        for name, parameter in parameters.items()
    ]
    cls = dataclasses.make_dataclass(
        class_name, fields=fields, bases=bases, frozen=True, slots=True
    )
    return cls


@with_config(ConfigDict(extra="forbid"))
@dataclasses.dataclass(frozen=True, slots=True)
class _ForbidExtra:
    """Empty dataclass that includes `extra="forbid"` in the pydantic config."""


@with_config(ConfigDict(extra="ignore"))
@dataclasses.dataclass(frozen=True, slots=True)
class _IgnoreExtra:
    """Empty dataclass that includes `extra="ignore"` in the pydantic config."""


def _build_input_model(parameters: Parameters, request_body_type: type | None) -> ApiInputModel:
    """Build the input model for the endpoint.

    This model will be used to validate the request data and extract the parameters for the handler.
    The model will have optional fields for the body, path, query, and headers.
    Extra fields within the body, path and query parameters are forbidden and will raise a
    validation error. Headers can have extra fields, but they will be ignored.
    Other fields will also be ignored.
    """
    if request_body_type is not None:
        if isinstance(request_body_type, BaseModel):
            request_body_type.model_config.setdefault("extra", "forbid")
        else:
            config = getattr(request_body_type, "__pydantic_config__", ConfigDict())
            config.setdefault("extra", "forbid")
            request_body_type.__pydantic_config__ = config  # type: ignore[attr-defined]
        body_type = request_body_type
    else:
        body_type = None

    # we're using _ForbidExtra here to make sure that no parameters are passed in the request
    path_type: type = _ForbidExtra
    query_type: type = _ForbidExtra
    # same thing here, just that we don't care about extra headers
    header_type: type = _IgnoreExtra
    if parameters.path:
        path_type = _make_parameter_model("_PathParameters", parameters.path, bases=(_ForbidExtra,))
    if parameters.query:
        query_type = _make_parameter_model(
            "_QueryParameters", parameters.query, bases=(_ForbidExtra,)
        )
    if parameters.headers:
        header_type = _make_parameter_model(
            "_HeaderParameters", parameters.headers, bases=(_IgnoreExtra,)
        )

    cls = dataclasses.make_dataclass(
        "_RequestData",
        fields=[
            ("body", body_type),
            ("path", path_type),
            ("query", query_type),
            ("headers", header_type),
        ],
        bases=(_IgnoreExtra,),
        frozen=True,
        slots=True,
    )
    return cast(type[DataclassInstance], cls)


class _PreparedRequestData(TypedDict):
    """Converted form of `RawRequestData`."""

    body: object | None
    path: dict[str, str]
    query: dict[str, str | list[str]]
    headers: dict[str, str]


class EndpointModel[**P, T]:
    __slots__ = (
        "_handler",
        "_signature",
        "_parameters",
        "_input_model",
        "request_body_type",
        "response_body_type",
    )

    def __init__(
        self,
        handler: Callable[P, T],
        signature: inspect.Signature,
        parameters: Parameters,
        input_model: ApiInputModel,
        request_body_type: type | None,
        response_body_type: type[T] | None,
    ) -> None:
        self._handler = handler
        self._signature = signature
        self._parameters = parameters
        self._input_model = input_model
        self.request_body_type = request_body_type
        self.response_body_type = response_body_type

    @classmethod
    def build(cls, handler: Callable[P, T]) -> Self:
        # TODO: "validate_implementation=False" run more complex validations that only verify the implementation (in unit tests)
        signature = inspect.signature(handler, eval_str=True)
        annotated_parameters = SignatureParametersProcessor.extract_annotated_parameters(signature)
        SignatureParametersProcessor.validate_parameters(annotated_parameters)
        parameters = SignatureParametersProcessor.parse_parameters(annotated_parameters)
        response_body_type = _return_type(signature)
        request_body_type = _request_body_type(signature)
        input_model = _build_input_model(parameters, request_body_type)
        return cls(
            handler,
            signature,
            parameters,
            input_model,
            request_body_type,
            response_body_type,
        )

    @property
    def path_parameters(self) -> Mapping[str, Parameter]:
        return self._parameters.path

    @property
    def has_path_parameters(self) -> bool:
        return bool(self.path_parameters)

    @property
    def has_query_parameters(self) -> bool:
        return bool(self._parameters.query)

    @property
    def has_request_schema(self) -> bool:
        return self.request_body_type is not None

    @property
    def has_response_schema(self) -> bool:
        return self.response_body_type is not None

    def _handle_query_args_list(
        self, query_args: dict[str, list[str]]
    ) -> dict[str, str | list[str]]:
        """Convert lists of query args to single values."""
        query_args = query_args.copy()  # prevent modification of the original request data
        out: dict[str, str | list[str]] = {}
        # handle the aliasing
        if self._parameters.query_aliases:
            for name, alias in self._parameters.query_aliases.items():
                if alias in query_args:
                    query_args[name] = query_args.pop(alias)

        for query_key, query_parameter in self._parameters.query.items():
            if query_value := query_args.pop(query_key, None):
                if query_parameter.is_list:
                    out[query_key] = query_value
                else:
                    if len(query_value) > 1:
                        raise ValidationError.from_exception_data(
                            "_RequestData",
                            [
                                InitErrorDetails(
                                    type="value_error",
                                    loc=("query", query_key),
                                    input=query_value,
                                    ctx={
                                        "error": f"`{query_key}` must be specified only once",
                                    },
                                ),
                            ],
                        )
                    out[query_key] = query_value[0]
            else:
                raise ValidationError.from_exception_data(
                    "_RequestData",
                    [
                        InitErrorDetails(type="missing", loc=("query", query_key), input=None),
                    ],
                )

        out.update(query_args)  # add any extra query args, to trigger pydantic validation errors
        return out

    def _validate_request_parameters(
        self, request_data: RawRequestData, content_type: str | None
    ) -> inspect.BoundArguments:
        """Validate the request parameters and return them as the bound arguments.

        This function will handle the aliasing of query parameters and headers, so the request data
        should be with the original keys.
        The response are the arguments that can be used to invoke the handler function.
        If the validation fails or unknown parameters are present in the request data,
        a pydantic ValidationError exception will be raised.
        """
        if self.request_body_type is not None and content_type and request_data["body"]:
            body = convert_request_body(self.request_body_type, content_type, request_data["body"])
        else:
            # we don't set it to None, so that we get the pydantic validation error
            body = request_data["body"] or None
        prepared_data: _PreparedRequestData = {
            "body": body,
            "path": request_data["path"],
            "query": self._handle_query_args_list(request_data["query"]),
            # convert `Headers` to a dict, case fold the keys for case-insensitive access
            "headers": {k.casefold(): v for k, v in request_data["headers"].items()},
        }

        # handle the aliasing, make sure to not modify the original request data
        if self._parameters.header_aliases:
            prepared_data["headers"] = prepared_data["headers"].copy()
            for name, alias in self._parameters.header_aliases.items():
                if alias in prepared_data["headers"]:
                    prepared_data["headers"][name] = prepared_data["headers"].pop(alias)

        # validate the input model
        # TypeAdapter performance: once per request
        input_type_adapter = TypeAdapter(self._input_model)  # nosemgrep: type-adapter-detected
        input_data = input_type_adapter.validate_python(prepared_data, strict=False)

        # unwrap the parameters
        out = dataclasses.asdict(input_data)
        if not self.has_request_schema:
            out.pop("body", None)  # validation will leave us with {"body": None}

        out.update(out.pop("path", {}))
        out.update(out.pop("query", {}))
        out.update(out.pop("headers", {}))

        # this also guarantees that all required parameters to call the handler are present
        return self._signature.bind(**out)

    def validate_request_and_call_handler(
        self, request_data: RawRequestData, content_type: str | None
    ) -> T:
        """Validate the request parameters and call the handler function.

        This function will handle the aliasing of query parameters and headers, so the request data
        should be with the original keys."""
        try:
            bound_arguments = self._validate_request_parameters(request_data, content_type)
        except ValidationError as e:
            RequestDataValidator.raise_formatted_pydantic_error(e)
        return self._handler(*bound_arguments.args, **bound_arguments.kwargs)

    def get_annotation(self, field: Literal["body", "path", "query", "headers"], /) -> type | None:
        for field_instance in dataclasses.fields(self._input_model):
            if field_instance.name == field:
                # this will be `Annotated`, but there is no way to type that
                return cast(type, field_instance.type)

        return None
