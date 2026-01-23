#!/usr/bin/env python3
# Copyright (C) 2025 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Sequence
from typing import Any, Literal
from urllib.parse import urlparse

from cmk.ccc.exceptions import MKGeneralException
from cmk.gui.form_specs.unstable import SingleChoiceElementExtended, SingleChoiceExtended
from cmk.gui.form_specs.unstable.legacy_converter import (
    TransformDataForLegacyFormatOrRecomposeFunction,
)
from cmk.gui.form_specs.visitors import DefaultValue as FrontendDefaultValue
from cmk.gui.watolib import config_domains
from cmk.gui.watolib.password_store import _transform_password_back as transform_password_to_disk
from cmk.rulesets.internal.form_specs import InternalProxy
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    FormSpec,
    Integer,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, NetworkPort
from cmk.utils.http_proxy_config import ProxyAuthSpec, ProxyConfigSpec


def _convert_url_to_explicit_proxy_dict(url: str) -> ProxyConfigSpec:
    parts = urlparse(url)
    proxy_dict = ProxyConfigSpec(
        scheme=parts.scheme,
        proxy_server_name=parts.hostname or "",
        port=parts.port or 0,
    )

    if parts.username and parts.password:
        proxy_dict["auth"] = ProxyAuthSpec(
            user=parts.username,
            password=transform_password_to_disk(("password", parts.password)),
        )

    return proxy_dict


type DiskRepresentation = (
    tuple[
        Literal["cmk_postprocessed"],
        Literal["environment_proxy", "no_proxy", "stored_proxy"],
        str,
    ]
    | tuple[
        Literal["cmk_postprocessed"],
        Literal["explicit_proxy"],
        ProxyConfigSpec,
    ]
)

type FrontendRepresentation = (
    tuple[Literal["environment"], Literal["environment"]]
    | tuple[Literal["no_proxy"], None]
    | tuple[Literal["global_"], str]
    | tuple[Literal["manual"], ProxyConfigSpec]
)


def _transform_from_disk(
    value: DiskRepresentation | FrontendDefaultValue,
) -> FrontendRepresentation | FrontendDefaultValue:
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
            return "manual", _convert_url_to_explicit_proxy_dict(url)

        case "cmk_postprocessed", "explicit_proxy", {
            "scheme": str(scheme),
            "proxy_server_name": str(proxy_server_name),
            "port": int(port),
            "auth": {
                "user": str(user),
                "password": (
                    "cmk_postprocessed",
                    "explicit_password" | "stored_password" as pw_type,
                    (str(part1), str(part2)),
                ),
            },
        }:
            return "manual", ProxyConfigSpec(
                scheme=scheme,
                proxy_server_name=proxy_server_name,
                port=port,
                auth=ProxyAuthSpec(
                    user=user, password=("cmk_postprocessed", pw_type, (part1, part2))
                ),
            )

        case "cmk_postprocessed", "explicit_proxy", {
            "scheme": str() as scheme,
            "proxy_server_name": str() as proxy_server_name,
            "port": int() as port,
        }:
            return "manual", ProxyConfigSpec(
                scheme=scheme,
                proxy_server_name=proxy_server_name,
                port=port,
            )

        case _:
            raise ValueError(f"Unknown proxy configuration: {value}")


def _transform_to_disk(value: FrontendRepresentation) -> DiskRepresentation:
    match value:
        case "environment", "environment":
            return "cmk_postprocessed", "environment_proxy", ""

        case "no_proxy", None:
            return "cmk_postprocessed", "no_proxy", ""

        case "global_", str(stored_proxy_id):
            return "cmk_postprocessed", "stored_proxy", stored_proxy_id

        case "manual", {
            "scheme": str() as scheme,
            "proxy_server_name": str() as proxy_server_name,
            "port": int() as port,
            "auth": {
                "user": str(user),
                "password": (
                    "cmk_postprocessed",
                    "explicit_password" | "stored_password" as pw_type,
                    (str(part1), str(part2)),
                ),
            },
        }:
            return (
                "cmk_postprocessed",
                "explicit_proxy",
                ProxyConfigSpec(
                    scheme=scheme,
                    proxy_server_name=proxy_server_name,
                    port=port,
                    auth=ProxyAuthSpec(
                        user=user, password=("cmk_postprocessed", pw_type, (part1, part2))
                    ),
                ),
            )

        case "manual", {
            "scheme": str() as scheme,
            "proxy_server_name": str() as proxy_server_name,
            "port": int() as port,
        }:
            return (
                "cmk_postprocessed",
                "explicit_proxy",
                ProxyConfigSpec(
                    scheme=scheme,
                    proxy_server_name=proxy_server_name,
                    port=port,
                ),
            )

        case _:
            raise ValueError(f"Unknown proxy configuration: {value}")


def recompose(
    form_spec: FormSpec[Any],
) -> TransformDataForLegacyFormatOrRecomposeFunction:
    if not isinstance(form_spec, InternalProxy):
        raise MKGeneralException(
            f"Cannot recompose form spec. Expected an InternalProxy form spec, got {type(form_spec)}"
        )

    global_proxies = config_domains.ConfigDomainCore().load().get("http_proxies", {}).values()
    global_proxy_choices: Sequence[SingleChoiceElementExtended[str]] = [
        SingleChoiceElementExtended(
            name=p["ident"],
            title=Title("%s") % p["title"],
        )
        for p in global_proxies
    ]

    elements: list[CascadingSingleChoiceElement[Any]] = [
        CascadingSingleChoiceElement(
            name="environment",
            title=Title("Auto-detect proxy settings for this network"),
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
            title=Title("No proxy"),
            parameter_form=FixedValue(
                value=None,
                label=Label("Connect directly to the destination instead of using a proxy."),
            ),
        ),
        CascadingSingleChoiceElement(
            name="global_",
            title=Title("Globally configured proxy"),
            parameter_form=SingleChoiceExtended(
                elements=global_proxy_choices,
                no_elements_text=Message("There are no elements defined for this selection yet."),
            ),
        ),
        CascadingSingleChoiceElement(
            name="manual",
            title=Title("Manual proxy configuration"),
            parameter_form=Dictionary(
                title=Title("Proxy"),
                elements={
                    "scheme": DictElement(
                        parameter_form=SingleChoice(
                            title=Title("Scheme"),
                            prefill=DefaultValue("http"),
                            elements=[
                                SingleChoiceElement(
                                    name=scheme.value,
                                    title=Title("%s") % scheme.name,
                                )
                                for scheme in InternalProxy.allowed_schemas
                            ],
                        ),
                        required=True,
                    ),
                    "proxy_server_name": DictElement(
                        parameter_form=String(
                            title=Title("Proxy server name or IP address"),
                            custom_validate=(LengthInRange(min_value=1),),
                            field_size=FieldSize.LARGE,
                        ),
                        required=True,
                    ),
                    "port": DictElement(
                        parameter_form=Integer(
                            title=Title("Port"),
                            custom_validate=(NetworkPort(),),
                        ),
                        required=True,
                    ),
                    "auth": DictElement(
                        parameter_form=Dictionary(
                            title=Title("Authentication for proxy required"),
                            elements={
                                "user": DictElement(
                                    parameter_form=String(
                                        title=Title("Username"),
                                        custom_validate=(LengthInRange(min_value=1),),
                                    ),
                                    required=True,
                                ),
                                "password": DictElement(
                                    parameter_form=Password(title=Title("Password")),
                                    required=True,
                                ),
                            },
                        ),
                    ),
                },
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
        from_disk=_transform_from_disk,  # type: ignore[arg-type]
        to_disk=_transform_to_disk,  # type: ignore[arg-type]
        migrate=form_spec.migrate,
    )
