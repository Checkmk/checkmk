#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping

from cmk.crypto.certificate import Certificate, CertificatePEM
from cmk.crypto.pem import PEMDecodingError
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FixedValue,
    List,
    MultilineText,
    MultipleChoice,
    MultipleChoiceElement,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _agent_ctl_enabled_form() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Agent Controller deployment"),
        help_text=Help(
            "The Agent Controller provides a safe channel for the communication between "
            "the monitoring site and the agent. It also provides the possibility to push "
            "monitoring data to the site (if applicable in your Checkmk edition). "
            "You may disable the Agent Controller if you experience problems with it. "
            "In this case the agent will work in legacy pull mode. Please note: "
            "In the legacy pull mode the transported data is not encrypted."
        ),
        prefill=DefaultValue("enabled"),
        elements=(
            CascadingSingleChoiceElement(
                name="enabled",
                title=Title("Enable controller"),
                parameter_form=Dictionary(
                    elements={
                        "detect_proxy": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title("Configure proxy server usage"),
                                help_text=Help(
                                    "By default, the Controller ignores proxy servers configured "
                                    "on the target system and connects directly (e.g. when querying "
                                    "the Agent Receiver port from the Checkmk REST API)."
                                ),
                                label=Label(
                                    "Detect and use proxies configured on the target system"
                                ),
                                prefill=DefaultValue(False),
                            ),
                        ),
                        "validate_api_cert": DictElement(
                            required=False,
                            parameter_form=BooleanChoice(
                                title=Title(
                                    "Configure TLS certificate validation for querying the "
                                    "Agent Receiver port from the Checkmk REST API"
                                ),
                                help_text=Help(
                                    "By default, certificate validation is disabled, because it is not "
                                    "security-relevant at this stage, see "
                                    '<a href="https://checkmk.com/werk/14715" target="_blank">Werk #14715</a>.'
                                ),
                                label=Label("Validate server certificate during port query"),
                                prefill=DefaultValue(False),
                            ),
                        ),
                    },
                ),
            ),
            CascadingSingleChoiceElement(
                name="disabled",
                title=Title("Disable controller"),
                parameter_form=FixedValue(value=None),
            ),
        ),
    )


def _validate_certificate(pem: str) -> None:
    try:
        Certificate.load_pem(CertificatePEM(pem))
    except PEMDecodingError as exc:
        raise validators.ValidationError(
            Message("Not a valid PEM encoded certificate: %(error)s") % {"error": str(exc)}
        )


def _embed_certificates_form() -> Dictionary:
    return Dictionary(
        title=Title("Embed certificates"),
        help_text=Help(
            "Bake certificates into the agent that the agent controller should trust when"
            " connecting to this site. They are trusted in addition to the site certificate"
            " the controller receives while registering, but only on the connections to this"
            " site, the ones that are already registered included. Installing the agent"
            " therefore keeps the agent controller trusting its site across a rotation of the"
            " site CA, without a re-registration.<br>"
            "Note that only certificates are baked. Private keys are never part of the agent"
            " package."
        ),
        elements={
            "site_certificates": DictElement(
                required=False,
                parameter_form=MultipleChoice(
                    title=Title("Certificates of this site"),
                    help_text=Help(
                        "During a graceful rotation of the site CA, select both the current and"
                        " the upcoming CA, so that the agent controllers keep trusting the site"
                        " before and after the rotation is finalized."
                    ),
                    elements=[
                        MultipleChoiceElement(
                            name="site_ca",
                            title=Title("Site CA (etc/ssl/ca.pem)"),
                        ),
                        MultipleChoiceElement(
                            name="pending_rotation_ca",
                            title=Title(
                                "Upcoming site CA of a pending certificate rotation"
                                " (etc/ssl/pending_certificate_rotation/ca.pem)"
                            ),
                        ),
                    ],
                    show_toggle_all=True,
                ),
            ),
            "custom_certificates": DictElement(
                required=False,
                parameter_form=List(
                    title=Title("Custom certificates"),
                    help_text=Help(
                        "Certificates that are not managed by this site, for example the CA of"
                        " your own public key infrastructure."
                    ),
                    element_template=Dictionary(
                        elements={
                            "certificate": DictElement(
                                required=True,
                                parameter_form=MultilineText(
                                    title=Title("Certificate in PEM format"),
                                    monospaced=True,
                                    custom_validate=(_validate_certificate,),
                                ),
                            ),
                        },
                    ),
                ),
            ),
        },
    )


def migrate(value: object) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"Unexpected value: {value!r}")
    if "agent_ctl_enabled" not in value:
        return value
    ctl = value["agent_ctl_enabled"]
    # Old format: (True/False, opts) tuple
    if isinstance(ctl, (list, tuple)) and len(ctl) == 2 and isinstance(ctl[0], bool):
        enabled, opts = ctl[0], ctl[1]
        return {
            **value,
            "agent_ctl_enabled": (
                ("enabled", opts if opts is not None else {}) if enabled else ("disabled", None)
            ),
        }
    # Already migrated
    return value


def _parameter_form() -> Dictionary:
    return Dictionary(
        title=Title("Agent Controller"),
        elements={
            "agent_ctl_enabled": DictElement(
                required=True,
                parameter_form=_agent_ctl_enabled_form(),
            ),
            "embed_certificates": DictElement(
                required=False,
                parameter_form=_embed_certificates_form(),
            ),
        },
        migrate=migrate,
    )


rule_spec_agent_controller = AgentConfig(
    name="agent_controller",
    title=Title("Agent Controller"),
    topic=Topic.WINDOWS,
    parameter_form=_parameter_form,
)
