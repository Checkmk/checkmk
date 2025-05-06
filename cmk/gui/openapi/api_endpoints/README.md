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
