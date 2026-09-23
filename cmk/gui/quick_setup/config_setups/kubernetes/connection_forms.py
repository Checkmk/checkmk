#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from dataclasses import replace
from urllib.parse import urlsplit

from cmk.ccc.hostaddress import HostName
from cmk.gui.form_specs.unstable import TwoColumnDictionary
from cmk.gui.form_specs.unstable.validators import HostAddress
from cmk.gui.watolib.form_spec_generators import create_full_path_folder_choice
from cmk.rulesets.v1 import Help, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    Integer,
    String,
    validators,
)


def host_configuration() -> Dictionary:
    return TwoColumnDictionary(
        elements={
            "host_name_source": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Checkmk host name"),
                    prefill=DefaultValue("cluster_name"),
                    help_text=Help(
                        "For a new setup, use the cluster name. When migrating, record the old "
                        "source host name and delete that host before running this setup, then "
                        "enter it as an explicit host name to retain monitoring history."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="cluster_name",
                            title=Title("Use the cluster name as the host name"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="explicit",
                            title=Title("Use an explicit host name"),
                            parameter_form=String(
                                title=Title("Explicit host name"),
                                custom_validate=(
                                    validators.LengthInRange(min_value=1, max_value=240),
                                    validators.MatchRegex(
                                        regex=HostName.REGEX_HOST_NAME,
                                        error_msg=Message(
                                            "Use only letters, numbers, dots, hyphens and underscores, "
                                            "starting with a letter, number or underscore."
                                        ),
                                    ),
                                ),
                            ),
                        ),
                    ],
                ),
            ),
            "host_path": DictElement(
                required=True,
                parameter_form=create_full_path_folder_choice(
                    title=Title("Folder"),
                    allow_new_folder_creation=False,
                    help_text=Help(
                        "Select the folder for the source host. Create a new folder first if needed."
                    ),
                ),
            ),
        }
    )


def connection_configuration(
    *, receiver_host: str, shared_secret: str, push_supported: bool = True
) -> CascadingSingleChoice:
    """Keep generated defaults in form state, without displaying the shared secret as a field."""
    spec = CascadingSingleChoice(
        title=Title("How should the Kubernetes agent connect to Checkmk?"),
        prefill=DefaultValue("push" if push_supported else "pull"),
        help_text=None if push_supported else Help("This Checkmk edition supports pull mode only."),
        elements=[
            CascadingSingleChoiceElement(
                name="push",
                title=Title("Push mode"),
                parameter_form=Dictionary(
                    elements={
                        "receiver_host": DictElement(
                            required=True,
                            render_only=True,
                            parameter_form=String(
                                prefill=DefaultValue(receiver_host),
                            ),
                        ),
                        "receiver_host_override": DictElement(
                            parameter_form=String(
                                title=Title("Override push receiver host name"),
                                custom_validate=(HostAddress(),),
                                help_text=Help(
                                    "Enter the host name or IP address reachable from the cluster, without a scheme or port."
                                ),
                            )
                        ),
                    }
                ),
            ),
            CascadingSingleChoiceElement(
                name="pull",
                title=Title("Pull mode"),
                parameter_form=Dictionary(
                    elements={
                        "shared_secret": DictElement(
                            required=True,
                            render_only=True,
                            parameter_form=String(
                                prefill=DefaultValue(shared_secret),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                            ),
                        ),
                        "service_exposure": DictElement(
                            required=True,
                            parameter_form=CascadingSingleChoice(
                                title=Title("Pull service exposure"),
                                prefill=DefaultValue("node_port"),
                                elements=[
                                    CascadingSingleChoiceElement(
                                        name="node_port",
                                        title=Title("NodePort"),
                                        parameter_form=Integer(
                                            title=Title("NodePort"),
                                            prefill=DefaultValue(30050),
                                            custom_validate=(
                                                validators.NumberInRange(
                                                    min_value=30000, max_value=32767
                                                ),
                                            ),
                                        ),
                                    )
                                ],
                            ),
                        ),
                        "tls_secret_name": DictElement(
                            parameter_form=String(
                                title=Title("Existing TLS Secret"),
                                custom_validate=(validators.LengthInRange(min_value=1),),
                                help_text=Help(
                                    "A Secret in the deployment namespace containing tls.crt and tls.key. "
                                    "Its certificate must cover the host name used by Checkmk. Without this, "
                                    "the pull endpoint serves HTTP: use a trusted network or external TLS termination."
                                ),
                            )
                        ),
                    }
                ),
            ),
        ],
    )
    return replace(
        spec,
        elements=[element for element in spec.elements if push_supported or element.name == "pull"],
    )


def _validate_pull_base_url(value: str) -> None:
    validators.Url(protocols=[validators.UrlProtocol.HTTP, validators.UrlProtocol.HTTPS])(value)
    try:
        parts = urlsplit(value)
        port = parts.port
    except ValueError:
        raise validators.ValidationError(Message("Enter a valid pull mode base URL.")) from None
    if (
        not parts.hostname
        or parts.username is not None
        or "?" in value
        or "#" in value
        or any(character.isspace() for character in value)
        or port == 0
    ):
        raise validators.ValidationError(
            Message("Enter a base URL without credentials, whitespace, a query or a fragment.")
        )
    if parts.path.rstrip("/").endswith("/pull/sections"):
        raise validators.ValidationError(
            Message("Remove /pull/sections from the URL; Checkmk appends it automatically.")
        )


def pull_url_configuration() -> Dictionary:
    return TwoColumnDictionary(
        elements={
            "base_url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Pull mode base URL"),
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        _validate_pull_base_url,
                    ),
                    help_text=Help(
                        "After deploying the agent, enter its URL as reachable from the monitoring site. "
                        "Checkmk appends /pull/sections automatically. For a private CA, add the CA to "
                        "Trusted certificate authorities for SSL in global settings."
                    ),
                ),
            ),
        }
    )
