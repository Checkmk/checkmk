#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping, Sequence

from cmk.ccc.site import omd_site
from cmk.ccc.store import load_from_mk_file
from cmk.ccc.version import Edition, edition
from cmk.rulesets.internal.form_specs import (
    DictGroupExtended,
    DictionaryGroupLayout,
    MultipleChoiceElementExtended,
    MultipleChoiceExtended,
)
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
from cmk.utils import paths
from cmk.utils.keypair_store import KeypairStore

DEFAULT_UPDATE_INTERVAL: int = 3600
MAX_UPDATE_INTERVAL: int = 30 * 24 * 60 * 60  # 30 days

_LEGACY_UPDATER_GROUP = DictGroupExtended(
    title=Title("Options of the legacy updater"),
    help_text=Help(
        "Only the legacy updater uses these options. The entries <i>Enable agent updates "
        "using the Agent Controller (fallback to legacy updater in case of problems)</i> and "
        "<i>Enable agent updates using the legacy updater (deprecated)</i> of "
        "<i>Activation</i> deploy it. The entry <i>Enable agent updates using the Agent "
        "Controller</i> deploys it on Solaris only. <i>Do not enable agent updates</i> "
        "ignores these options."
    ),
    layout=DictionaryGroupLayout.vertical,
)


def _migrate(obj: object) -> Mapping[str, object]:
    if not isinstance(obj, Mapping):
        raise ValueError(obj)

    if not obj:
        return {
            "updater_registration": "manual",
        }

    return obj


def _migrate_activated(value: object) -> str:
    match value:
        # Up to Checkmk 2.5, the only updater was the legacy one. The compatible entry keeps it.
        case "enabled":
            return "compatible"
        case str() if value in ("disabled", "integrated_only", "compatible", "legacy"):
            return value
    raise ValueError(value)


def _migrate_proxy_old_format(
    value: object,
) -> tuple[str, object]:
    match value:
        # used for migration from 2.4.0 version
        case None:
            return "no_proxy", None
        # used for migration from 2.4.0 version
        case "env":
            return "env_proxy", "env"
        # used for migration from 2.4.0 version
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
        # new format with CascadingSingleChoice element
        case ((str() as choice), config):
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
    match value:
        case (str(choice), None):
            return _migrate_edition(choice)
        case "bit64" | "64bit":
            return "bit64"
        case "32bit" | "bit32" | "script":
            # 32bit binaries are no longer supported, migrate to script since that is the
            # only alternative for 32bit systems.
            return "script"
        case _:
            raise ValueError(value)


def _migrate_certificates(value: object) -> Sequence[tuple[str, str, bytes]]:
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
                parameter_form=FixedValue(
                    value="env",
                    label=Label(
                        'Agent updater will follow variables "HTTP_PROXY" and "HTTPS_PROXY" on the host.'
                    ),
                ),
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
            "Agent Controller registration by default. This means that these settings won't apply "
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
                        "You likely should enter <tt>%(site)s</tt> here. However, in a distributed "
                        "monitoring setup, the update site might differ."
                    )
                    % {"site": omd_site()},
                    prefill=DefaultValue(omd_site()),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "protocol": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Protocol to use for fetching updates"),
                    help_text=Help(
                        "Optional. The agent updater will try to auto-detect the protocol, "
                        "first trying HTTPS and then HTTP. You can use this setting to force one "
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
            "Choose which updater keeps the agents up to date.<br>"
            "<b>Enable agent updates using the Agent Controller</b>: The Agent Controller "
            "updates the agents for Linux and Windows. On Linux, it needs the Agent Controller "
            "and the single directory deployment of the rule set <i>Customize agent package</i>. "
            "Baking fails for Linux agents without them. Solaris agents get the legacy "
            "updater.<br>"
            "<b>Enable agent updates using the Agent Controller (fallback to legacy updater in "
            "case of problems)</b>: The agents get both updaters, and both run side by side, "
            "independently of each other. Both install the agent package that is baked for the "
            "host, so it does not matter which of them updates an agent first. If the Agent "
            "Controller fails to update an agent, the legacy updater still keeps it up to date. "
            "Agents that cannot use the Agent Controller get the legacy updater only: Solaris "
            "agents, and Linux agents without the Agent Controller or without the single "
            "directory deployment. Rules that enabled agent updates before Checkmk 3.0 use this "
            "entry after the update.<br>"
            "<b>Enable agent updates using the legacy updater (deprecated)</b>: Only the legacy "
            "updater updates the agents.<br>"
            "<br>"
            "Do not forget to enable agent updates in at least one of your rules. "
            "It can be useful to create rules that are only partially filled out. "
            "Since the rule execution is done on a <i>per parameter</i> base "
            "you can for example create one rule at the top of your list that "
            "just sets the activation to <i>Do not enable agent updates</i> for just some of "
            "your hosts without setting any of the other parameters."
        ),
        elements=[
            SingleChoiceElement(
                name="disabled",
                title=Title("Do not enable agent updates"),
            ),
            SingleChoiceElement(
                name="integrated_only",
                title=Title("Enable agent updates using the Agent Controller"),
            ),
            SingleChoiceElement(
                name="compatible",
                title=Title(
                    "Enable agent updates using the Agent Controller"
                    " (fallback to legacy updater in case of problems)"
                ),
            ),
            SingleChoiceElement(
                name="legacy",
                title=Title("Enable agent updates using the legacy updater (deprecated)"),
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
                    "the maximum allowed update interval is set to %(max_interval)s seconds (30 days)"
                )
                % {"max_interval": str(MAX_UPDATE_INTERVAL)},
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
            "same host name.<br>"
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
                title=Title("On first Agent Controller registration"),
            ),
            SingleChoiceElement(
                name="overwrite",
                title=Title("On every Agent Controller registration"),
            ),
            SingleChoiceElement(
                name="manual",
                title=Title("Manual"),
            ),
        ],
        prefill=DefaultValue("keep"),
    )


def _is_ultimatemt_remote_site() -> bool:
    # Mirror of the 2.4 guard `edition() is Edition.CME and is_wato_slave_site()`.
    # Reading distributed_wato.mk directly avoids cmk.gui import
    if edition(paths.omd_root) is not Edition.ULTIMATEMT:
        return False
    distributed_wato_file = paths.check_mk_config_dir / "distributed_wato.mk"
    if not distributed_wato_file.exists() or distributed_wato_file.stat().st_size == 0:
        return False
    is_distributed_setup_remote_site = load_from_mk_file(
        distributed_wato_file,
        key="is_distributed_setup_remote_site",
        default=False,
        lock=False,
    )
    # On 2.4 site this option is called `is_wato_slave_site`
    is_wato_slave_site = load_from_mk_file(
        distributed_wato_file,
        key="is_wato_slave_site",
        default=False,
        lock=False,
    )
    return is_distributed_setup_remote_site or is_wato_slave_site


def _validate_signature_keys(value: Sequence[object]) -> None:
    if _is_ultimatemt_remote_site():
        return
    validators.LengthInRange(min_value=1)(value)


def _valuespec_signature_keys() -> MultipleChoiceExtended:
    return MultipleChoiceExtended(
        title=Title("Signature keys the agent will accept"),
        help_text=Help(
            "The agent will update itself only with packages that are signed "
            "by one of these keys. You need to specify at least one key. Keys are "
            "being created <a href='%(url)s' target='_blank'>here</a>."
        )
        % {"url": "wato.py?mode=signature_keys"},
        # The keys are loaded lazily, since they may change while the form spec is cached
        elements=_signature_key_elements,
        custom_validate=(_validate_signature_keys,),
    )


def _signature_key_elements() -> list[MultipleChoiceElementExtended]:
    return [
        MultipleChoiceElementExtended(
            name=key.certificate,
            title=Title("%(alias)s") % {"alias": key.alias},
        )
        for key in sorted(_make_agent_sign_keypair_store().load().values(), key=lambda k: k.alias)
    ]


def _make_agent_sign_keypair_store() -> KeypairStore:
    return KeypairStore(
        paths.default_config_dir.joinpath("multisite.d", "wato", "agent_signature_keys.mk"),
        "agent_signature_keys",
    )


def _valuespec_agent_config_cmk_update_agent() -> Dictionary:
    return Dictionary(
        title=Title("Agent updater (Linux, Windows, Solaris)"),
        help_text=Help(
            "This rule set enables automatic updates "
            "of the Checkmk agent for Linux, Solaris and Windows. "
            "The agent will look for new updates on a regular base and update "
            "itself, when a newly baked agent is available, released and signed. "
            "<br><b>Note<sup>1</sup>:</b> This update mechanism is baked into the agent itself. "
            "So after activating this feature you need at least one more manual "
            "update of the agent, of course."
            "<br><b>Note<sup>2</sup>:</b> After installing such an agent, its updater "
            "must be registered at your Checkmk server. This can be done either by registering "
            "the Agent Controller, or by manual agent updater registration call. "
            "Customizable in _Registration_ option below. See there for details."
            "<br><b>Note<sup>3</sup>:</b> In order to deploy the legacy updater to Solaris, a "
            'Python 3.7 installation (or newer) with installed python packages "cryptography", '
            '"requests" and "PySocks" is required on the target hosts.'
        ),
        elements={
            "activated": DictElement(
                required=False,
                parameter_form=_valuespec_activation(),
            ),
            "interval": DictElement(
                required=False,
                parameter_form=_valuespec_interval(),
            ),
            "signature_keys": DictElement(
                required=False,
                parameter_form=_valuespec_signature_keys(),
            ),
            "updater_registration": DictElement(
                required=False,
                parameter_form=_valuespec_updater_registration(),
            ),
            "server_data": DictElement(
                required=False,
                parameter_form=_valuespec_server_data(),
                group=_LEGACY_UPDATER_GROUP,
            ),
            "certificates": DictElement(
                required=False,
                parameter_form=_valuespec_certificates(),
                group=_LEGACY_UPDATER_GROUP,
            ),
            "proxy": DictElement(
                required=False,
                parameter_form=_valuespec_proxy_settings(),
                group=_LEGACY_UPDATER_GROUP,
            ),
            "edition": DictElement(
                required=False,
                parameter_form=_valuespec_editions(),
                group=_LEGACY_UPDATER_GROUP,
            ),
        },
        migrate=_migrate,
    )


rule_spec_cmk_update_agent = AgentConfig(
    name="cmk_update_agent",
    title=Title("Agent updater (Linux, Windows, Solaris)"),
    topic=CustomTopic(Title("Automatic updates")),
    parameter_form=_valuespec_agent_config_cmk_update_agent,
)
