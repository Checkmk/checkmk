#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

# A ``Dictionary``'s elements are heterogeneous, so ``DictElement[Any]`` is the
# only shape that types them together (as in cmk.gui.wato._notification_parameter).
# mypy: disable-error-code="explicit-any"
"""FormSpec for the Maps connections global setting.

:func:`connections_list_spec` builds the ``maps_connections`` global (a list of
connections, edited in Setup → Global settings → "Maps"); add/remove is the
list's own UI. ``type`` is a CascadingSingleChoice mirroring the backend
``ConnectionConfig`` discriminator (currently only ``livestatus``). The
``automation_secret`` rides the Checkmk password store.
"""

import os
from typing import Any, Literal

from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    InputHint,
    Integer,
    List,
    Password,
    String,
)
from cmk.rulesets.v1.form_specs.validators import LengthInRange, MatchRegex


def _omd_socket_prefill() -> InputHint[str] | DefaultValue[str]:
    """Auto-fill the OMD livestatus socket when Maps runs inside an OMD site.

    Saves the operator from retyping /omd/sites/<site>/tmp/run/live on every
    new connection. Falls back to a placeholder hint when not in OMD.
    """
    omd_root = os.environ.get("OMD_ROOT")
    if omd_root:
        # /tmp/run/live is the OMD Livestatus Unix-domain socket, not a
        # temp-file path — bandit B108 is a false positive here.
        return DefaultValue(f"{omd_root}/tmp/run/live")  # nosec B108
    return InputHint("/omd/sites/<site>/tmp/run/live")


def _livestatus_target() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Connection target"),
        help_text=Help(
            "Pick Unix socket when Maps runs inside the same OMD site as the "
            "monitoring core (path is at tmp/run/live). Pick TCP for remote "
            "Livestatus / xinetd setups."
        ),
        elements=[
            CascadingSingleChoiceElement(
                name="socket",
                title=Title("Unix socket"),
                parameter_form=Dictionary(
                    title=Title("Unix socket"),
                    elements={
                        "socket_path": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Socket path"),
                                prefill=_omd_socket_prefill(),
                                field_size=FieldSize.LARGE,
                            ),
                        ),
                    },
                ),
            ),
            CascadingSingleChoiceElement(
                name="tcp",
                title=Title("TCP (host + port)"),
                parameter_form=Dictionary(
                    title=Title("TCP endpoint"),
                    elements={
                        "host": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Host"),
                                prefill=InputHint("livestatus.example.com"),
                                field_size=FieldSize.LARGE,
                            ),
                        ),
                        "port": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Port"),
                                prefill=DefaultValue(6557),
                            ),
                        ),
                        "tls": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("TLS"),
                                label=Label("Use TLS (matches OMD LIVESTATUS_TLS=on)"),
                                help_text=Help(
                                    "OMD wraps the 6557 listener in stunnel by default. "
                                    "Disable only when the remote endpoint is plain TCP."
                                ),
                                prefill=DefaultValue(True),
                            ),
                        ),
                        "tls_verify": DictElement(
                            required=True,
                            parameter_form=BooleanChoice(
                                title=Title("Verify TLS certificate"),
                                label=Label(
                                    "Verify the Livestatus server certificate using the local site CA"
                                ),
                                help_text=Help(
                                    "Verify the endpoint's certificate against this site's trusted "
                                    "certificate authorities, or accept any certificate it offers. "
                                    "It is highly recommended to leave this enabled. If the endpoint "
                                    "is an external site whose CA this site does not yet trust, add "
                                    "its CA to the global trusted certificate authorities."
                                ),
                                prefill=DefaultValue(True),
                            ),
                        ),
                    },
                ),
            ),
        ],
        prefill=DefaultValue("socket"),
    )


def _metric_history(default_source: str) -> CascadingSingleChoice:
    """Where Maps fetches metric history — Livestatus (CMC) vs the REST API (Nagios/Raw).

    CMC streams metric history over Livestatus and needs no credentials; Nagios /
    Checkmk Raw cores have no Livestatus metric history, so Maps reads it via the
    Checkmk REST API, which needs an automation user. ``default_source`` follows
    *this* site's monitoring core (see :func:`connections_list_spec`); the operator can
    override it for a connection that targets a remote site with a different core
    — so the credential fields appear exactly when the chosen source needs them.
    """
    return CascadingSingleChoice(
        title=Title("Metric history source"),
        help_text=Help(
            "How Maps fetches metric history for graphs. CMC cores stream it over "
            "Livestatus (no credentials). Nagios / Checkmk Raw cores need the REST API."
        ),
        elements=[
            CascadingSingleChoiceElement(
                name="livestatus",
                title=Title("Livestatus (CMC core) — no credentials needed"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="rest_api",
                title=Title("Checkmk REST API (Nagios / Raw core)"),
                parameter_form=Dictionary(
                    title=Title("REST API credentials"),
                    elements={
                        "automation_user": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Automation user"),
                                prefill=InputHint("automation"),
                            ),
                        ),
                        "automation_secret": DictElement(
                            required=True,
                            parameter_form=Password(title=Title("Secret")),
                        ),
                    },
                ),
            ),
        ],
        prefill=DefaultValue(default_source),
    )


def _livestatus_branch(default_metric_source: str) -> Dictionary:
    elements: dict[str, DictElement[Any]] = {
        "target": DictElement(
            required=True,
            parameter_form=_livestatus_target(),
        ),
        "timeout": DictElement(
            required=True,
            parameter_form=Integer(
                title=Title("Timeout"),
                unit_symbol="s",
                prefill=DefaultValue(10),
            ),
        ),
        "checkmk_url": DictElement(
            parameter_form=String(
                title=Title("Checkmk URL"),
                help_text=Help(
                    "Used for deep links into the Checkmk GUI. Leave empty "
                    "to inherit the global setting."
                ),
                prefill=InputHint("/<site>/check_mk"),
                field_size=FieldSize.LARGE,
            ),
        ),
        "metric_history": DictElement(
            required=True,
            parameter_form=_metric_history(default_metric_source),
        ),
    }
    return Dictionary(title=Title("Livestatus connection"), elements=elements)


MonitoringCore = Literal["cmc", "nagios"]


def _connection_elements(default_metric_source: str) -> dict[str, DictElement[Any]]:
    return {
        # Required, mirroring a site's mandatory alias: maps reference a
        # connection by id but every picker shows this label, so it must exist.
        "label": DictElement(
            required=True,
            parameter_form=String(
                title=Title("Display label"),
                help_text=Help("Human-readable name shown in map pickers and the connection list."),
                field_size=FieldSize.LARGE,
                custom_validate=(LengthInRange(min_value=1),),
            ),
        ),
        "type": DictElement(
            required=True,
            parameter_form=CascadingSingleChoice(
                title=Title("Backend type"),
                elements=[
                    CascadingSingleChoiceElement(
                        name="livestatus",
                        title=Title("Livestatus (Checkmk / Nagios)"),
                        parameter_form=_livestatus_branch(default_metric_source),
                    ),
                ],
                prefill=DefaultValue("livestatus"),
            ),
        ),
    }


def connections_list_spec(
    monitoring_core: MonitoringCore | None = None,
    title: Title = Title("Maps connections"),
) -> List[Any]:
    """The WATO global: the list of monitoring connections Maps queries.

    Each entry carries a stable ``id`` (referenced by maps) plus the
    single-connection fields. The ``automation_secret`` rides the Checkmk
    password store (the ``Password`` form spec), so global.mk holds only a
    reference; the daemon resolves it via ``cmk.utils.password_store``.
    """
    default_metric_source = "rest_api" if monitoring_core == "nagios" else "livestatus"
    return List(
        title=title,
        help_text=Help(
            "Monitoring connections that maps query for live state. Maps reference "
            "a connection by its ID."
        ),
        add_element_label=Label("Add connection"),
        remove_element_label=Label("Remove connection"),
        no_element_label=Label("No connections configured yet."),
        editable_order=False,
        element_template=Dictionary(
            title=Title("Connection"),
            elements={
                "id": DictElement(
                    required=True,
                    parameter_form=String(
                        title=Title("Connection ID"),
                        help_text=Help(
                            "Stable identifier maps reference. Letters, digits, "
                            "underscore and hyphen only; must be unique."
                        ),
                        custom_validate=(
                            MatchRegex(
                                r"^[a-zA-Z0-9_\-]+$",
                                error_msg=Message(
                                    "Use only letters, digits, underscore and hyphen."
                                ),
                            ),
                        ),
                        field_size=FieldSize.MEDIUM,
                    ),
                ),
                **_connection_elements(default_metric_source),
            },
        ),
    )
