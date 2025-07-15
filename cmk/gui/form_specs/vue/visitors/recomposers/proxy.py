#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.
import urllib.parse
from typing import Any, Literal

from cmk.ccc.exceptions import MKGeneralException

from cmk.utils.urls import is_allowed_url

from cmk.gui.form_specs.converter import TransformDataForLegacyFormatOrRecomposeFunction
from cmk.gui.watolib import config_domains

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    FixedValue,
    FormSpec,
    Proxy,
    ProxySchema,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, ValidationError

from ..._type_defs import DefaultValue as FrontendDefaultValue


def _validate_proxy_scheme(allowed_schemes: frozenset[ProxySchema], value: str) -> None:
    parts = urllib.parse.urlparse(value)
    if not parts.scheme:
        raise ValidationError(
            Message(
                "Invalid proxy given: missing scheme in proxy format 'scheme://network_location'"
            )
        )
    if not parts.netloc:
        raise ValidationError(
            Message(
                "Invalid proxy given: missing network_location in proxy format 'scheme://network_location'"
            )
        )

    if parts.scheme not in allowed_schemes:
        raise ValidationError(
            Message("Invalid proxy scheme given. Must be one of: %s") % ", ".join(allowed_schemes)
        )
    if not is_allowed_url(value, cross_domain=True, schemes=allowed_schemes):
        raise ValidationError(Message("Invalid proxy given: not an allowed url"))


def _transform_from_disk(
    value: object,
) -> tuple[str, str | None] | FrontendDefaultValue:
    if isinstance(value, FrontendDefaultValue):
        return value

    match value:
        case "cmk_postprocessed", "environment_proxy", str():
            return "environment", "environment"
        case "cmk_postprocessed", "no_proxy", str():
            return "no_proxy", None
        case "cmk_postprocessed", "stored_proxy", str(stored_proxy_id):
            return "global_", stored_proxy_id
        case "cmk_postprocessed", "explicit_proxy", str(url):
            return "url", url

    raise ValueError(value)


def _transform_to_disk(
    value: object,
) -> tuple[
    Literal["cmk_postprocessed"],
    Literal["environment_proxy", "no_proxy", "stored_proxy", "explicit_proxy"],
    str,
]:
    match value:
        case "environment", "environment":
            return "cmk_postprocessed", "environment_proxy", ""
        case "no_proxy", None:
            return "cmk_postprocessed", "no_proxy", ""
        case "global_", str(stored_proxy_id):
            return "cmk_postprocessed", "stored_proxy", stored_proxy_id
        case "url", str(url):
            return "cmk_postprocessed", "explicit_proxy", url

    raise ValueError(value)


def recompose(
    form_spec: FormSpec[Any],
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    if not isinstance(form_spec, Proxy):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected a Proxy form spec, got {type(form_spec)}"
        )

    global_proxies = config_domains.ConfigDomainCore().load().get("http_proxies", {}).values()
    global_proxy_choices: list[SingleChoiceElement] = [
        SingleChoiceElement(
            name=p["ident"],
            title=Title("%s") % p["title"],
        )
        for p in global_proxies
        if urllib.parse.urlparse(p["proxy_url"]).scheme in form_spec.allowed_schemas
    ]

    elements: list[CascadingSingleChoiceElement[Any]] = [
        CascadingSingleChoiceElement(
            name="environment",
            title=Title("Use from environment"),
            parameter_form=FixedValue(
                value="environment",
                help_text=Help(
                    "Use the proxy settings from the environment variables. The variables <tt>NO_PROXY</tt>, "
                    "<tt>HTTP_PROXY</tt> and <tt>HTTPS_PROXY</tt> are taken into account during execution. "
                    "Have a look at the python requests module documentation for further information. Note "
                    "that these variables must be defined as a site-user in ~/etc/environment and that "
                    "this might affect other notification methods which also use the requests module."
                ),
                label=Label(
                    "Use proxy settings from the process environment. This is the default."
                ),
            ),
        ),
        CascadingSingleChoiceElement(
            name="no_proxy",
            title=Title("Connect without proxy"),
            parameter_form=FixedValue(
                value=None,
                label=Label("Connect directly to the destination instead of using a proxy."),
            ),
        ),
        CascadingSingleChoiceElement(
            name="global_",
            title=Title("Use globally configured proxy"),
            parameter_form=SingleChoice(
                elements=global_proxy_choices,
                no_elements_text=Message("There are no elements defined for this selection yet."),
            ),
        ),
        CascadingSingleChoiceElement(
            name="url",
            title=Title("Use explicit proxy settings"),
            parameter_form=String(
                custom_validate=[
                    LengthInRange(min_value=1),
                    lambda value: _validate_proxy_scheme(form_spec.allowed_schemas, value),
                ]
            ),
        ),
    ]

    return TransformDataForLegacyFormatOrRecomposeFunction(
        wrapped_form_spec=CascadingSingleChoice(
            title=form_spec.title or Title("Proxy"),
            help_text=form_spec.help_text,
            elements=elements,
            prefill=DefaultValue("environment"),
        ),
        from_disk=_transform_from_disk,
        to_disk=_transform_to_disk,
        migrate=form_spec.migrate,
    )
