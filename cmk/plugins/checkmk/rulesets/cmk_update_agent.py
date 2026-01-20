#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence
from typing import Any

from cmk.ccc.site import omd_site
from cmk.gui.config import active_config
from cmk.gui.form_specs.unstable import MultipleChoiceExtended
from cmk.gui.form_specs.unstable.multiple_choice import MultipleChoiceElementExtended
from cmk.rulesets.v1 import Help, Label, Message, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FileUpload,
    FixedValue,
    Integer,
    List,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, CustomTopic

DEFAULT_UPDATE_INTERVAL: int = 3600
MAX_UPDATE_INTERVAL: int = 30 * 24 * 60 * 60  # 30 days


def _migrate_activated(value: object) -> str:
    if isinstance(value, bool):
        return "enabled" if value else "disabled"
    if isinstance(value, str) and value in ("enabled", "disabled"):
        return value
    raise ValueError(value)


def _migrate_protocol(value: object) -> tuple[str, Mapping[str, object]]:
    match value:
        case ("http", _) | "http":
            return "http", {}
        case ("https", _) | "https":
            return "https", {}
        case _:
            raise ValueError(value)


def _migrate_proxy_old_format(
    value: object,
) -> tuple[str, object]:
    match value:
        case None:
            return "no_proxy", None
        case "env":
            return "env_proxy", "env"
        case {
            "server": server,
            "port": port,
            "proxy_protocol": proxy_config,
        }:
            protocol, credentials = _parse_proxy_protocol(proxy_config)
            creds = {}
            if credentials:
                creds = {
                    "credentials": {
                        "user": credentials[0],
                        "password": credentials[1],
                    }
                }
            return "explicit_proxy", {
                "server": server,
                "port": port,
                "proxy_protocol": protocol,
                **creds,
            }
        case (str() as choice, dict() as config):
            return choice, config
        case _:
            raise ValueError(value)


def _parse_proxy_protocol(
    proxy_protocol: object,
) -> tuple[str, tuple[str, str] | None]:
    match proxy_protocol:
        case ("http", Mapping() as credentials):
            return "http", credentials["credentials"]
        case ("http", None):
            return "http", None
        case ("socks4", None):
            return "socks4", None
        case ("socks5", Mapping() as credentials):
            return "socks5", credentials["credentials"]
        case ("socks5", None):
            return "socks5", None
        case "http":
            return "http", None
        case "socks4":
            return "socks4", None
        case "socks5":
            return "socks5", None
        case _:
            return "http", None


def _migrate_edition(value: object) -> tuple[str, None]:
    if isinstance(value, str) and value in ("64bit", "32bit", "script"):
        match value:
            case "64bit":
                return "bit64", None
            case "32bit":
                return "bit32", None
            case "script":
                return "script", None
            case _:
                raise ValueError(value)

    if isinstance(value, Sequence):
        return value[0], None

    raise ValueError(value)


def _migrate_certificates(value: object) -> Sequence[Any]:
    if isinstance(value, list):
        result: list[tuple[str, str, bytes]] = []
        for idx, cert in enumerate(value):
            if isinstance(cert, str):
                # Old format: PEM string, convert to FileUpload tuple
                cert_bytes = cert.encode()
                result.append((f"certificate_{idx}.pem", "application/x-pem-file", cert_bytes))
            elif isinstance(cert, tuple) and len(cert) == 3:
                # Already in new format
                name, mime_type, content = cert
                result.append((str(name), str(mime_type), bytes(content)))
        return result
    return []


def _migrate_signature_keys(value: object) -> Sequence[str]:
    match value:
        case list():
            return value
        case dict():
            return list(value.values())
        case _:
            raise TypeError(value)


def _valuespec_proxy_settings() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Proxy settings"),
        help_text=Help("Configure the agent updater whether to connect via proxy server."),
        elements=[
            CascadingSingleChoiceElement(
                name="no_proxy",
                title=Title("Disable proxy handling"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="env_proxy",
                title=Title("Use environment variables from host"),
                parameter_form=FixedValue(value="env"),
            ),
            CascadingSingleChoiceElement(
                name="explicit_proxy",
                title=Title("Provide proxy settings"),
                parameter_form=Dictionary(
                    title=Title("Provide settings"),
                    elements={
                        "server": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("DNS name or IP address of proxy server"),
                            ),
                        ),
                        "port": DictElement(
                            required=True,
                            parameter_form=Integer(
                                title=Title("Port"),
                                prefill=DefaultValue(80),
                            ),
                        ),
                        "proxy_protocol": DictElement(
                            required=True,
                            parameter_form=SingleChoice(
                                title=Title("Proxy protocol"),
                                elements=[
                                    SingleChoiceElement(
                                        name="http",
                                        title=Title("HTTP"),
                                    ),
                                    SingleChoiceElement(
                                        name="socks4",
                                        title=Title("SOCKS4"),
                                    ),
                                    SingleChoiceElement(
                                        name="socks5",
                                        title=Title("SOCKS5"),
                                    ),
                                ],
                                prefill=DefaultValue("http"),
                            ),
                        ),
                        "credentials": DictElement(
                            required=False,
                            parameter_form=Dictionary(
                                title=Title("Credentials"),
                                elements={
                                    "user": DictElement(
                                        required=True,
                                        parameter_form=String(
                                            title=Title("User"),
                                        ),
                                    ),
                                    "password": DictElement(
                                        required=True,
                                        parameter_form=Password(
                                            title=Title("Password"),
                                        ),
                                    ),
                                },
                            ),
                        ),
                    },
                ),
            ),
        ],
        migrate=_migrate_proxy_old_format,
    )


def _valuespec_editions() -> CascadingSingleChoice:
    return CascadingSingleChoice(
        title=Title("Executable format (Linux)"),
        help_text=Help(
            "Optionally choose the format of the agent updater executable file. Relevant for Linux only."
            " On other OSes, the executable format will be chosen automatically regardless of this rule."
            " The binary formats yield a broader compatibility whereas the python script is small and editable."
            " Please note that the Checkmk team can offer no support for issues about the target"
            ' system\'s python environment when choosing "Script".'
        ),
        elements=[
            CascadingSingleChoiceElement(
                name="bit64",
                title=Title("64-bit packaged binary"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="bit32",
                title=Title("32-bit packaged binary"),
                parameter_form=FixedValue(value=None),
            ),
            CascadingSingleChoiceElement(
                name="script",
                title=Title("Script (Limited support, see inline help)"),
                parameter_form=FixedValue(value=None),
            ),
        ],
        prefill=DefaultValue("bit64"),
        migrate=_migrate_edition,
    )


def _valuespec_server_data() -> Dictionary:
    return Dictionary(
        title=Title("Update server information"),
        help_text=Help(
            "Optionally provide protocol, server and site for agent registration "
            "and/or updates. If not entered here, you can provide it on registration."
        ),
        elements={
            "usage": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Usage"),
                    elements=[
                        SingleChoiceElement(
                            name="registration",
                            title=Title("Registration and fallback"),
                        ),
                        SingleChoiceElement(
                            name="always",
                            title=Title("Use for all connections"),
                        ),
                    ],
                    help_text=Help(
                        'In case of "Registration and fallback", the agent updater '
                        "will use this information only on registration and rely on "
                        "the update URL provided by the Agent Bakery afterwards. If the "
                        "connection fails, the agent updater will additionally "
                        'use this information as a fallback. In case of "Use for all connections", '
                        "the agent updater will ignore the update URL provided by the Agent Bakery."
                    ),
                    prefill=DefaultValue("registration"),
                ),
            ),
            "server": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("DNS name or IP address of update server"),
                    help_text=Help(
                        "This is the name/address at which the agent "
                        "can reach your central monitoring server via HTTPS or HTTP. "
                        "<b>Note</b>: If you are using HTTPS then this name must "
                        "exactly match the common name of the server certificate."
                    ),
                ),
            ),
            "site": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Name of Checkmk site of update server"),
                    help_text=Help(
                        "You likely should enter <tt>%s</tt> here. However, in a distributed "
                        "monitoring setup, the update site might differ."
                    )
                    % omd_site(),
                    prefill=DefaultValue(omd_site()),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "protocol": DictElement(
                required=True,
                parameter_form=CascadingSingleChoice(
                    title=Title("Protocol to use for fetching updates"),
                    help_text=Help(
                        "HTTPS is the suggested setting here. It requires a valid SSL "
                        "setup of your Apache web server on your monitoring server, however. "
                        "When using HTTP then confidential data that is contained in the baked "
                        "agents could be spied out (such as passwords for plug-ins)."
                    ),
                    elements=[
                        CascadingSingleChoiceElement(
                            name="http",
                            title=Title("HTTP"),
                            parameter_form=FixedValue(value=None),
                        ),
                        CascadingSingleChoiceElement(
                            name="https",
                            title=Title("HTTPS"),
                            parameter_form=FixedValue(value=None),
                        ),
                    ],
                    prefill=DefaultValue("https"),
                    migrate=_migrate_protocol,
                ),
            ),
        },
    )


def _valuespec_activation() -> SingleChoice:
    return SingleChoice(
        title=Title("Activation"),
        help_text=Help(
            "Do not forget to activate the plug-in in at least one of your rules. "
            "It can be useful to create rules that are only partially filled out. "
            "Since the rule execution is done on a <i>per parameter</i> base "
            "you can for example create one rule at the top of your list that "
            "just sets the activation to <i>no</i> for just some of your hosts without "
            "setting any of the other parameters."
        ),
        elements=[
            SingleChoiceElement(
                name="disabled",
                title=Title("Do not deploy automatic agent update plug-in"),
            ),
            SingleChoiceElement(
                name="enabled",
                title=Title("Deploy plug-in that updates agent automatically"),
            ),
        ],
        prefill=DefaultValue("disabled"),
        migrate=_migrate_activated,
    )


def _valuespec_certificates() -> List[tuple[str, str, bytes]]:
    return List(
        title=Title("Certificates for HTTPS verification"),
        help_text=Help(
            "You can optionally provide CA or self-signed certificates that will be used by "
            "the agent updater to verify outgoing HTTPS connections. By providing valid "
            "certificates here, it is guaranteed that the agent updater is communicating "
            "only with authentic update servers."
        ),
        element_template=FileUpload(
            title=Title("CA or self-signed certificate"),
        ),
        add_element_label=Label("Add CA or self-signed certificate"),
        migrate=_migrate_certificates,
    )


def _valuespec_interval() -> TimeSpan:
    return TimeSpan(
        title=Title("Interval for update check"),
        help_text=Help(
            "In order to save resources on the target host and on the update server "
            "it is recommended to do the update checks not more than once every 10 minutes."
        ),
        displayed_magnitudes=[
            TimeMagnitude.DAY,
            TimeMagnitude.HOUR,
            TimeMagnitude.MINUTE,
        ],
        prefill=DefaultValue(float(DEFAULT_UPDATE_INTERVAL)),
        custom_validate=(
            validators.NumberInRange(
                min_value=0,
                max_value=MAX_UPDATE_INTERVAL,
                error_msg=Message(
                    "To prevent the agent updater from being locked out, "
                    "the maximum allowed update interval is set to %s seconds (30 days)"
                )
                % str(MAX_UPDATE_INTERVAL),
            ),
        ),
    )


def _valuespec_signature_keys() -> MultipleChoiceExtended:
    return MultipleChoiceExtended(
        title=Title("Signature keys the agent will accept"),
        help_text=Help(
            "The agent will update itself only with packages that are signed "
            "by one of these keys. You need to specify at least one key. Keys are "
            "being created <a href='%s' target='_blank'>here</a>."
        )
        % "wato.py?mode=signature_keys",
        elements=[
            MultipleChoiceElementExtended(
                name=key.certificate,
                title=Title("%s") % key.alias,
            )
            for key in sorted(active_config.agent_signature_keys.values(), key=lambda k: k.alias)
        ],
        custom_validate=(validators.LengthInRange(min_value=1),),
        migrate=_migrate_signature_keys,
    )


def _valuespec_agent_config_cmk_update_agent() -> Dictionary:
    return Dictionary(
        title=Title("Agent updater (Linux, Windows, Solaris)"),
        help_text=Help(
            "This ruleset allows to deploy an agent plug-in that updates "
            "the Checkmk agent for Linux, Solaris and Windows on a regular base. "
            "The agent will look for new updates on a regular base and update "
            "itself, when a newly baked agent is available, released and signed. "
            "<br><b>Note<sup>1</sup>:</b> This update mechanism is baked into the agent itself. "
            "So after activating this feature you need at least one more manual "
            "update of the agent, of course."
            "<br><b>Note<sup>2</sup>:</b> After deploying this new plug-in "
            "you need to call it once manually to register the agent "
            "at your update server. Call <tt>cmk-update-agent register -H <i>HOST</i></tt> (UNIX), "
            "or <tt>check_mk_agent.exe updater register -H <i>HOST</i></tt> (Windows), "
            "where <i>HOST</i> must be the name of that host in your monitoring."
            "<br><b>Note<sup>3</sup>:</b> In order to deploy this plug-in to Solaris, a "
            'Python 3.7 installation (or newer) with installed python packages "pyOpenSSL", '
            '"requests" and "PySocks" is required on the target hosts.'
        ),
        elements={
            "activated": DictElement(
                required=True,
                parameter_form=_valuespec_activation(),
            ),
            "server_data": DictElement(
                required=False,
                parameter_form=_valuespec_server_data(),
            ),
            "certificates": DictElement(
                required=False,
                parameter_form=_valuespec_certificates(),
            ),
            "interval": DictElement(
                required=False,
                parameter_form=_valuespec_interval(),
            ),
            "proxy": DictElement(
                required=False,
                parameter_form=_valuespec_proxy_settings(),
            ),
            "edition": DictElement(
                required=False,
                parameter_form=_valuespec_editions(),
            ),
            "signature_keys": DictElement(
                required=False,
                parameter_form=_valuespec_signature_keys(),
            ),
        },
    )


rule_spec_cmk_update_agent = AgentConfig(
    name="cmk_update_agent",
    title=Title("Agent updater (Linux, Windows, Solaris)"),
    topic=CustomTopic(Title("Automatic Updates")),
    parameter_form=_valuespec_agent_config_cmk_update_agent,
)
