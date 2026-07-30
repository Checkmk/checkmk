#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    Password,
    Proxy,
    ProxySchema,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import SpecialAgent, Topic


def _tcp_timeouts() -> Dictionary:
    return Dictionary(
        title=Title("TCP timeouts"),
        elements={
            "connect": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Connect timeout (seconds)"),
                    help_text=Help("Number of seconds to wait for a TCP connection"),
                    prefill=DefaultValue(10),
                ),
            ),
            "read": DictElement(
                required=False,
                parameter_form=Integer(
                    title=Title("Read timeout (seconds)"),
                    help_text=Help(
                        "Number of seconds to wait for the agent to respond during a TCP "
                        "connection."
                    ),
                    prefill=DefaultValue(30),
                ),
            ),
        },
    )


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Kubernetes pull mode"),
        help_text=Help(
            "Monitor a Kubernetes cluster in pull mode. Checkmk connects to an agent that runs "
            "inside the cluster, which gathers the data and returns it on request. This rule only "
            "configures how to reach that agent. What is monitored is configured in the cluster "
            "itself, so there are no Kubernetes-specific settings here."
        ),
        elements={
            "url": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Base URL"),
                    prefill=InputHint("https://<agent host>"),
                    macro_support=True,
                    custom_validate=(
                        validators.LengthInRange(min_value=1),
                        validators.Url(
                            protocols=[
                                validators.UrlProtocol.HTTP,
                                validators.UrlProtocol.HTTPS,
                            ]
                        ),
                    ),
                    help_text=Help(
                        "The base URL of the in-cluster agent, including the protocol (http or "
                        "https). Checkmk appends /pull/sections to this URL automatically to "
                        "reach the endpoint that exposes the sections. Depending on how you "
                        "deployed the agent, this is either its NodePort, its Ingress or its "
                        "LoadBalancer endpoint."
                    ),
                ),
            ),
            "shared_secret": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Shared secret"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    help_text=Help(
                        "The shared secret that you configured in the in-cluster agent, so that "
                        "it only answers to this site."
                    ),
                ),
            ),
            "verify_cert": DictElement(
                required=True,
                parameter_form=BooleanChoice(
                    title=Title("SSL certificate verification"),
                    label=Label("Verify the certificate"),
                    prefill=DefaultValue(True),
                    help_text=Help(
                        "Verify the TLS certificate presented by the in-cluster agent or by the "
                        "reverse proxy in front of it. If the certificate is self-signed or "
                        'signed by a private CA, add the CA certificate under "Trusted '
                        'certificate authorities for SSL" in global settings. Only disable '
                        "verification in exceptional cases. Without verification, anyone able "
                        "to intercept the connection can read the shared secret and all "
                        "monitoring data from your cluster."
                    ),
                ),
            ),
            "proxy": DictElement(
                required=False,
                parameter_form=Proxy(
                    allowed_schemas=frozenset({ProxySchema.HTTP, ProxySchema.HTTPS}),
                ),
            ),
            "timeout": DictElement(required=False, parameter_form=_tcp_timeouts()),
        },
    )


rule_spec_special_agent_rustik = SpecialAgent(
    name="rustik",
    title=Title("Kubernetes pull mode"),
    topic=Topic.CLOUD,
    parameter_form=_parameter_form,
)
