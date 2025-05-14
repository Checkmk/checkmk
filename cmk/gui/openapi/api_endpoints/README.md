## Adding new (versioned) API endpoints

### Concepts

The API consists of multiple endpoint families, each containing one or more
"versioned endpoints". The versioned endpoint defines various aspects of how it
is exposed to the outside world, like the URL and HTTP method. More importantly,
it maps individual API versions to the actual implementation of the endpoint.
We will call these implementations "handler functions". The handlers are regular
Python functions that are called when the endpoint is accessed. They also define
the supported request parameters and the request and response schemas, through
the use of type annotations.

### Code structure
The recommended package structure for endpoints is as follows:
```
<some-package>/
    __init__.py
    (_family.py)
    <one_endpoint>.py
    <other_endpoint>.py
```
Where `<some-package>` is either:
* `api` or something similar, within an existing package - example:
  `cmk/gui/cee/dcd/_openapi`
* `cmk/gui/openapi/api_endpoints/<family_name>` if there is no clear package for
  the family

The endpoint family definition should be:
* in `_family.py` if the family is fully migrated to the versioned endpoints
* in `cmk/gui/openapi/shared_endpoint_families` if it's shared with the legacy
  implementation

Every endpoint within the family should have its own module, named after the
endpoint. The module should contain at minimum the endpoint handlers and the
`VersionedEndpoint` definition. Models may be defined in separate modules,
especially if they are shared between endpoints.

The `__init__.py` file should contain a `register` function, which would then
register the family and all endpoints within it to the appropriate registries.

### Endpoint family
Before we can define an endpoint, we need to define the family it belongs to.
Some families already exist in the legacy world (`cmk/gui/openapi/endpoints`),
these will need to be migrated to the new system.

Define the family either within the package (for new or fully migrated families)
or in `cmk/gui/openapi/shared_endpoint_families` (for shared families).
Check there for a more detailed example.
```python
from cmk.gui.openapi.restful_objects.endpoint_family import EndpointFamily

family = EndpointFamily(
    name="FamilyName",  # will be used as an identifier in other places
    description="My family",
    doc_group="Setup",
    # optional
    display_name="Display name",
)
```

### Endpoint handler functions
The handler function is the actual implementation of the endpoint. This is where
you define the logic of what happens when the endpoint is accessed. This
includes checking permissions and converting between "internal" and "external"
(API) data models. The response type will what is returned to the client.

The simplest possible handler function is this:
```python
def handler() -> None:
    return
```
This would handler takes no parameters or request body and returns an empty
response (204 No Content).

#### Adding a request body
To add a request body, you need to define a dataclass model for it. Every field
in the model should have a description and an example. Fields of nested models
will only need a description.

See the [omitted fields](#omitted-fields) and
[`api_field` sections](#the-api_field-function) for more details.

Then, add a `body` parameter to the handler, with the correct type annotation.
```python
from dataclasses import dataclass
from cmk.gui.openapi.framework.model import api_field, ApiOmitted

@dataclass(kw_only=True, slots=True)
class RequestBodyModel:
    required_field: str = api_field(
        description="Required field.",
        example="example",
    )
    optional_field: int | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        description="Optional field.",
        example=123,
    )

def handler(body: RequestBodyModel) -> None:
    return
```

#### Path, query and request parameters
Adding parameters requires annotating the argument with a marker.
The public facing names will be the same as the argument names, but query and
headers may be aliased to a different name. This also allows for using names
that would be invalid in Python, like `X-Header-Name`.
Note that headers are case-insensitive, so the only problem is using dashes.
The types can be anything, as long as pydantic can deserialize into them.
```python
from typing import Annotated
from cmk.gui.openapi.framework import HeaderParam, PathParam, QueryParam
from cmk.gui.openapi.framework.model import ApiOmitted

def handler(
    path_param: Annotated[str, PathParam(description="...", example="example")],
    query_param: Annotated[int, QueryParam(description="...", example="123")],
    header_param: Annotated[
        str | ApiOmitted,
        HeaderParam(description="...", example="...")
    ] = ApiOmitted(),
) -> None:
    return
```
Path parameters will need to be specified (with the same name) in the URL.
We will get to that later, when we talk about `VersionedEndpoint`.

Query parameters may also be a list, which allows specifying the parameter
multiple times in the URL. For that, change the parameters type to `list[...]`
and set the `is_list=True` flag in the `QueryParam` marker.

#### Changing the response
Similar to the request body, the response body should be defined as a dataclass.
The same restrictions on descriptions and examples apply. Additionally, no
defaults (except `ApiOmitted`) are allowed. Specify the model as the return type
hint of the handler function.

Because we're using the typing, the handler must instantiate the response model.
The type checking will be the closest we get to "validating" the response body.

```python
from dataclasses import dataclass
from cmk.gui.openapi.framework.model import api_field, ApiOmitted

@dataclass(kw_only=True, slots=True)
class ResponseModel:
    required_field: str = api_field(
        description="Required field.",
        example="example",
    )
    optional_field: int | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        description="Optional field.",
        example=123,
    )

def handler() -> ResponseModel:
    return ResponseModel(required_field="value")
```
This would return a 200 OK response with this JSON body:
```json
{"required_field":"value"}
```

If you need to return a different status code or additional headers,
change the return type to `TypedResponse[ResponseModel]`.
This allows you to return *either* your `ResponseModel` or an `ApiResponse`
which wraps your `ResponseModel`.
```python
from dataclasses import dataclass
from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.response import ApiResponse, TypedResponse

@dataclass(kw_only=True, slots=True)
class ResponseModel:
    field: str = api_field(
        description="Required field.",
        example="example",
    )

def handler() -> TypedResponse[ResponseModel]:
    return ApiResponse(
        status_code=201,
        body=ResponseModel(field="value"),
        headers={"X-Header": "value"},
    )
```

### VersionedEndpoint
The remaining metadata will be defined in the `VersionedEndpoint` class.
Most options should be self-explanatory. Check the documentation on the
individual classes for more details.

```python
from cmk.gui.openapi.framework import *

def handler() -> None:
    return

my_endpoint = VersionedEndpoint(
    metadata=EndpointMetadata(
        path="/test",
        link_relation=".../default",
        method="get",
    ),
    permissions=EndpointPermissions(),  # declare all checked permissions
    doc=EndpointDoc(
        family="FamilyName",  # ideally, get the name via the family object
    ),
    versions={
        APIVersion.V1: EndpointHandler(handler=handler),
    },
    # optional
    behavior=EndpointBehavior(),
    removed_in_version=None,
)
```
Once you have your versioned endpoint defined, you can register it in the
`VersionedEndpointRegistry`.

## Advanced models
We are using `pydantic` for validation and serialization of the models. This
means, all types supported by pydantic are supported in the REST API as well.
For *request* models, the use of validator annotations is encouraged.

### The `api_field` function
Apart from defining the fields description and example, the `api_field` function
can be used for a few other things:

* `default` and `default_factory` - mostly used for `ApiOmitted`, but can also
  be used within *request* models for other defaults.
* `alias` - used to define a different name for the field in the JSON
  representation. This is useful for camelCase names, or if the field name is
  invalid in Python.
* `title` - define a custom title. Usually the default title is fine.
* `pattern` - define a regex pattern for the field, will be used for validation.

### Omitted fields
Due to the way some internal data structures distinguish between `None` and
"not set", we need to use a special type (`ApiOmitted`) for fields that may be
omitted from the response. This is equivalent to `NotRequired` for `TypedDict`.

When using `ApiOmitted` in your models, you must set the `default_factory` on
the field. This will be checked in unit tests. For request models, it is usually
better to *not* use `ApiOmitted`, and have different defaults.

It is important that `ApiOmitted` stays *within the API*. This means that within
an endpoint handler function, you should convert `ApiOmitted` to whatever the
correct internal representation is.

```python
from dataclasses import dataclass
from typing import TypedDict, NotRequired
from cmk.gui.openapi.framework.model import api_field, ApiOmitted

@dataclass(kw_only=True, slots=True)
class MyModel:
    id: str = api_field(description="Unique identifier.", example="abc")
    name: str | ApiOmitted = api_field(
        default_factory=ApiOmitted,
        description="Name of the object.",
        example="foo",
    )
    
class InternalModel(TypedDict):
    id: str
    name: NotRequired[str]
    
def _some_internal_function(internal: InternalModel) -> InternalModel:
    return internal  # do something with the data
    
def handler(body: MyModel) -> MyModel:
    as_internal: InternalModel = {
        "id": body.id,
    }
    if not isinstance(body.name, ApiOmitted):
        as_internal["name"] = body.name
    
    # do something with the data
    internal_out = _some_internal_function(as_internal)
    return MyModel(
        id=internal_out["id"],
        name=internal_out.get("name", ApiOmitted()),
    )

```

### Validators
Pydantic offers a few different ways of validating data through annotations:

* `AfterValidator` - runs **after** the normal pydantic validation. This should
  be your first choice for custom validation.
* `BeforeValidator` - runs **before** the normal pydantic validation. Use this
  to transform the data to a different type.
* `PlainValidator` - runs **instead of** the normal pydantic validation. This
  should be used for custom types, where you want to validate the data in a
  different way than pydantic does.
* `WrapValidator` - has an additional parameter for the normal validator. Can be
  used to run validation before and after the pydantic validation.

Each of these will take a validation function as an argument. The function must
return the value (even if unmodified) or raise an exception in case of errors.
```python
from typing import Annotated
from pydantic import AfterValidator

def _validate(value: str) -> str:
    if " " in value:
        raise ValueError("Value must not contain spaces")
    return value

# this can be used as a type in your model
NoSpaces = Annotated[str, AfterValidator(_validate)]
```

Note that validation functions for validators other than `AfterValidator` should
have an `object` type hint (for the input).

More details can be found in the [pydantic validator documentation][validators].

Some validators and custom types are already available as part of the framework.
Check the `cmk.gui.openapi.framework.model` package, specifically the
`validators` and `common_fields` modules. These can also be used as inspiration
for new validators.

[validators]: https://docs.pydantic.dev/latest/concepts/validators/

#### Custom types
Fully custom types are also supported. Either by using the validators (and
serializers) through annotations, or by implementing the pydantic specific
class methods.

See the [pydantic documentation on custom types][custom-types].

[custom-types]: https://docs.pydantic.dev/latest/concepts/types/#custom-types

### Dynamic fields (custom attributes)
Some entities allow the user to add custom attributes.
In order to support this, we use the `WithDynamicFields` class.
In short, this class adds a `dynamic_fields` field to the model, which will be
merged with the rest of the fields during serialization. Any additional fields
during deserialization will also be added to it. To the user, it should look
like a "flat" object. The only difference would be that the custom attributes
don't show up in the schema.

```python
from dataclasses import dataclass
from cmk.gui.openapi.framework.model import api_field, json_dump_without_omitted
from cmk.gui.openapi.framework.model.dynamic_fields import WithDynamicFields

@dataclass(kw_only=True, slots=True)
class MyModel(WithDynamicFields):
    id: str = api_field(description="Unique identifier.")

x = MyModel(id="123", dynamic_fields={"custom": "value"})
print(json_dump_without_omitted(MyModel, x))
# {"id": "123", "custom": "value"}
```

Adding validations to the dynamic fields can be dony by overriding the
`dynamic_fields` field or the `_populate_dynamic_fields` class method.
```python
from dataclasses import dataclass
from typing import Annotated, Mapping
from pydantic import AfterValidator
from cmk.gui.openapi.framework.model import api_field
from cmk.gui.openapi.framework.model.dynamic_fields import WithDynamicFields

@dataclass(kw_only=True, slots=True)
class MyModel(WithDynamicFields):
    id: str = api_field(description="Unique identifier.")

    # the only requirement is a mapping with string keys
    dynamic_fields: Mapping[str, Annotated[str, AfterValidator(...)]]
```

## Marshmallow schema to dataclass models

This guide provides a reference for translating Marshmallow schemas to modern
dataclass implementations with strong typing and improved validation.

### Example

#### Marshmallow Schema

```python
from marshmallow import Schema, fields, validate

class LinkSchema(Schema):
    """Schema for link resources."""
    href = fields.String(required=True)
    rel = fields.String(required=True)

class UserSchema(Schema):
    """Schema representing a user."""

    # Required field
    id = fields.String(
        required=True,
        description="Unique identifier."
    )

    # Required field with validation
    username = fields.String(
        required=True,
        validate=validate.Length(min=3, max=50),
        description="User's login name."
    )

    # Field with custom validation
    active_users = fields.List(
        fields.Username(),  # class validating if the username is valid
        required=True,
        description="List of active users."
    )

    # Optional field
    display_name = fields.String(
        required=False,
        description="User's display name."
    )

    # Nullable field
    bio = fields.String(
        allow_none=True,
        description="User's biography."
    )

    # Optional and nullable field
    location = fields.String(
        required=False,
        allow_none=True,
        description="User's location."
    )

    # Field with custom JSON key name
    email_address = fields.String(
        data_key="emailAddress",
        description="User's email."
    )

    # Field with enum
    status = fields.String(
        description="Account status.",
        load_default="active",
        enum=["active", "suspended", "inactive"],
    )

    # Constant field
    type = fields.Constant(
        "user",
        description="Resource type."
    )

    # Boolean field
    is_verified = fields.Boolean(
        description="Whether user is verified.",
        load_default=False
    )

    # List field
    roles = fields.List(
        fields.String(),
        required=True,
        description="User roles."
    )

    # Dict field
    preferences = fields.Dict(
        description="User preferences.",
        allow_none=True
    )

    # Nested object field
    links = fields.List(
        fields.Nested(LinkSchema),
        required=False,
        description="Related links."
    )

```

#### Equivalent Dataclass Model

```python
from dataclasses import dataclass
from typing import Literal, Any, Annotated
from annotated_types import Interval
from pydantic import AfterValidator

from cmk.gui.openapi.framework.model.api_field import api_field
from cmk.gui.openapi.framework.model.omitted import ApiOmitted


def active_user_check(value: str) -> str:
    """Custom validation function for active users."""
    # Implement your validation logic here
    # raise an exception if invalid
    return value


@dataclass(kw_only=True, slots=True)
class LinkModel:
    """Model for link resources."""
    href: str
    rel: str

@dataclass(kw_only=True, slots=True)
class UserModel:
    """Model representing a user."""

    # Required field
    id: str = api_field(
        description="Unique identifier."
    )

    # Required field with validation
    username: Annotated[str, Interval(ge=3, le=50)] = api_field(
        description="User's login name.",
    )

    # Field with custom validation
    active_users: list[Annotated[str, AfterValidator(active_user_check)]] = api_field(
        description="List of active users.",
    )

    # Optional field
    display_name: str | ApiOmitted = api_field(
        description="User's display name.",
        default_factory = ApiOmitted
    )

    # Nullable field
    bio: str | None = api_field(
        description="User's biography.",
    )

    # Optional and nullable field
    location: str |  None | ApiOmitted = api_field(
        description="User's location.",
        default_factory = ApiOmitted
    )

    # Field with custom JSON key name
    email_address: str = api_field(
        description="User's email.",
        alias="emailAddress"
    )

    # Field with default value
    status: Literal["active", "suspended", "inactive"] = api_field(
        description="Account status.",
        default="active"
    )

    # Constant field
    type: Literal["user"] = "user"

    # Boolean field
    is_verified: bool = api_field(
        description="Whether user is verified.",
        default=False
    )

    # List field
    roles: list[str] = api_field(
        description="User roles."
    )

    # Dict field
    preferences: dict[str, Any] | None = api_field(
        description="User preferences.",
    )

    # Nested object field
    links: list[LinkModel] | ApiOmitted = api_field(
        description="Related links.",
        default_factory = ApiOmitted,
    )
```

### Additional Marshmallow Notes

* the `cast_to_dict` functionality in some marshmallow schemas can be ignored
  in the dataclass model, as the dataclass will automatically handle this.
