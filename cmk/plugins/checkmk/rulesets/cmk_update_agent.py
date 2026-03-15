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


def _migrate(obj: object) -> Mapping[str, object]:
    if not isinstance(obj, Mapping):
        raise ValueError(obj)

    if not obj:
        return {
            "updater_registration": "manual",
        }

    return obj


def _migrate_activated(value: object) -> str:
    if isinstance(value, bool):
        return "enabled" if value else "disabled"
    if isinstance(value, str) and value in ("enabled", "disabled"):
        return value
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


def _migrate_edition(value: object) -> str:
    if isinstance(value, str):
        match value:
            case "64bit":
                return "bit64"
            case "32bit" | "bit32" | "script":
                # 32bit binaries are no longer supported, migrate to script since that is the
                # only alternative for 32bit systems.
                return "script"
            case _:
                raise ValueError(value)

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


def _valuespec_editions() -> SingleChoice:
    return SingleChoice(
        title=Title("Executable format (Linux)"),
        help_text=Help(
            "Optionally choose the format of the agent updater executable file. Relevant for Linux only."
            " On other OSes, the executable format will be chosen automatically regardless of this rule."
            " The binary format yields a broader compatibility, while the Python script is small and editable.<br>"
            " Concrete requirements are:<br>"
            " <b>packaged binary:</b> x86-64 Linux system with glibc 2.17 or newer."
            " <b>Python script:</b> Python3 with modules _cryptography_, _requests_ and _pysocks_ (for SOCKS proxy support)."
        ),
        elements=[
            SingleChoiceElement(
                name="bit64",
                title=Title("packaged binary"),
            ),
            SingleChoiceElement(
                name="script",
                title=Title("Python script"),
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
            "and/or updates. If not entered here, you can provide it on registration.<br>"
            "<br>"
            "<i>New with Checkmk 2.5</i>: The agent updater registration will be triggered by the "
            "agent controller registration by default. This means that these settings won't apply "
            "to the agent updater registration.<br>"
            "You can change the behavior below under <i>Registration</i>."
        ),
        elements={
            "usage": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Usage"),
                    elements=[
                        SingleChoiceElement(
                            name="registration",
                            title=Title("Manual registration and fallback"),
                        ),
                        SingleChoiceElement(
                            name="always",
                            title=Title("Use for all connections"),
                        ),
                    ],
                    help_text=Help(
                        "In case of <i>Manual registration and fallback</i>, the agent updater "
                        "will use this information only on registration with `cmk-update-agent register`, and rely on "
                        "the update URL provided by the Agent Bakery afterwards. If the "
                        "connection fails, the agent updater will additionally "
                        "use this information as a fallback.<br>"
                        "In case of Use <i>for all connections</i>, "
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
                        "can reach your central monitoring server via HTTPS or HTTP.<br>"
                        "<b>Note</b>: If you are using HTTPS then this name must "
                        "be listed in the Subject Alternative Names (SANs) of the server certificate."
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
                parameter_form=SingleChoice(
                    title=Title("Protocol to use for fetching updates"),
                    help_text=Help(
                        "Optional. The agent updater will try to auto detect the protocol, "
                        "first tryping HTTPS and then HTTP. You can use this setting to force one "
                        "of the two protocols.<br>"
                        "HTTPS is highly recommended. It requires a valid SSL "
                        "setup of your Apache web server on your monitoring server, however. "
                        "When using HTTP then confidential data that is contained in the baked "
                        "agents could be spied out (such as passwords for plug-ins)."
                    ),
                    elements=[
                        SingleChoiceElement(
                            name="http",
                            title=Title("HTTP"),
                        ),
                        SingleChoiceElement(
                            name="https",
                            title=Title("HTTPS"),
                        ),
                    ],
                    prefill=DefaultValue("https"),
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


def _valuespec_updater_registration() -> SingleChoice:
    return SingleChoice(
        title=Title("Registration"),
        help_text=Help(
            "To start updating the agent package, the agent updater must register at a monitoring "
            "site.<br>"
            "<br>"
            "<i>New with Checkmk 2.5</i>: By default, the agent updater will be registered by the agent "
            "controller, after its own successful registration, at the same site and with the "
            "same hostname.<br>"
            "<br>"
            "Here you can configure the overwriting behavior of subsequent agent controller "
            "registrations, or opt to skip the agent controller triggered agent updater "
            "registration entirely.<br>"
            "Consider the differences between agent controller and agent updater "
            "registrations: "
            "The agent controller can register at multiple sites, or overwrite existing "
            "registrations when registering for the same site again. "
            "The agent updater can only hold one registration at a time. Every new registration "
            "will overwrite the previous one, regardless of the connection details.<br>"
            "<br>"
            "Available Choices:<ul>"
            "<li><b>On first agent controller registration</b>: An existing Agent Updater registration will be kept."
            " If you register the agent controller at multiple sites, only the first site will be used for agent updates.</li>"
            "<li><b>On every agent controller registration</b>: The Agent Updater registration will be overwritten on every agent controller registration."
            " If you register the agent controller at multiple sites, only the last site will be used for agent updates.</li>"
            "<li><b>Manual</b>: Manually register the agent updater.<br>"
            "Either on agent controller registration with explicit flag: "
            "<tt>cmk-agent-ctl register [args] --automatic-updates</tt><br>"
            "Or separately: "
            "<tt>cmk-update-agent register</tt> (Linux)/<tt>check_mk_agent.exe updater register</tt> (Windows).<br>"
            "Since the registration is handled manually by the user, any existing "
            "agent updater registration will be overwritten.</li>"
            "</ul>"
            "<i>Note</i>: Since the agent controller is available for Linux and Windows only, "
            "this setting is not relevant for Solaris, where the agent updater will always need to "
            "be registered manually."
        ),
        elements=[
            SingleChoiceElement(
                name="keep",
                title=Title("On first agent controller registration"),
            ),
            SingleChoiceElement(
                name="overwrite",
                title=Title("On every agent controller registration"),
            ),
            SingleChoiceElement(
                name="manual",
                title=Title("Manual"),
            ),
        ],
        prefill=DefaultValue("keep"),
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
            "it must be registered at your Checkmk server. This can be done either by registering "
            "the agent controller, or by manual agent updater registration call. "
            "Customizable in _Registration_ option below. See there for details."
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
            "updater_registration": DictElement(
                required=False,
                parameter_form=_valuespec_updater_registration(),
            ),
        },
        migrate=_migrate,
    )


rule_spec_cmk_update_agent = AgentConfig(
    name="cmk_update_agent",
    title=Title("Agent updater (Linux, Windows, Solaris)"),
    topic=CustomTopic(Title("Automatic Updates")),
    parameter_form=_valuespec_agent_config_cmk_update_agent,
)
