#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from collections.abc import Mapping
from typing import Any

from cmk.rulesets.v1 import Help, Title
from cmk.rulesets.v1.form_specs import (
    CascadingSingleChoice,
    CascadingSingleChoiceElement,
    DefaultValue,
    DictElement,
    Dictionary,
    FieldSize,
    FixedValue,
    Float,
    Integer,
    List,
    Password,
    SingleChoice,
    SingleChoiceElement,
    String,
    validators,
)
from cmk.rulesets.v1.rule_specs import AgentConfig, Topic


def _migrate_instance_config(instance_config: dict[str, Any]) -> dict[str, Any]:
    """Migrate instance configuration fields to new format.

    Migrates:
    - "server": string/None -> ("ip_or_fqdn", string) or ("use_local_fqdn", None)
    - "login": tuple -> dictionary with password wrapped for migration
    """
    migrated = dict(instance_config)

    if "server" in migrated:
        server = migrated["server"]
        if server is None:
            migrated["server"] = ("use_local_fqdn", None)
        elif isinstance(server, str):
            migrated["server"] = ("ip_or_fqdn", server)

    if "login" in migrated:
        login = migrated["login"]
        if isinstance(login, tuple) and len(login) == 3:
            user, password, mode = login
            if isinstance(password, str):
                password = ("cmk_postprocessed", "explicit_password", ("", password))
            elif not isinstance(password, tuple):
                raise TypeError(f"Cannot migrate jolokia login password format: {password!r}")
            migrated["login"] = {
                "user": user,
                "password": password,
                "mode": mode,
            }

    return migrated


def _migrate_to_agent_config(value: object) -> Mapping[str, object]:
    """Migrate old ruleset format to new format with deployment field.

    Old format had Alternative at the top level:
    - None: Do not deploy
    - Dictionary: Deploy with configuration

    New format has all parameters in a flat Dictionary with deployment field:
    - {"deployment": "do_not_deploy"}
    - {"deployment": "sync", ...config...}
    """
    match value:
        case None:
            return {"deployment": "do_not_deploy"}
        case {"deployment": str()} if isinstance(value, dict):
            return value
        case dict():
            config = _migrate_instance_config(value)
            if "instances" in config:
                instances = config["instances"]
                if isinstance(instances, list):
                    config["instances"] = [_migrate_instance_config(inst) for inst in instances]

            return {"deployment": "sync", **config}
        case _:
            raise ValueError(f"Cannot migrate jolokia agent config value: {value!r}")


def _jolokia_instance_elements() -> Mapping[str, DictElement[Any]]:
    """Common elements for Jolokia instance configuration."""
    return {
        "protocol": DictElement(
            required=False,
            parameter_form=SingleChoice(
                title=Title("Protocol"),
                elements=[
                    SingleChoiceElement(name="http", title=Title("HTTP")),
                    SingleChoiceElement(name="https", title=Title("HTTPS")),
                ],
                prefill=DefaultValue("http"),
            ),
        ),
        "server": DictElement(
            required=False,
            parameter_form=CascadingSingleChoice(
                title=Title("Jolokia server"),
                elements=[
                    CascadingSingleChoiceElement(
                        name="ip_or_fqdn",
                        title=Title("IP address or FQDN of JVM web server"),
                        parameter_form=String(
                            help_text=Help(
                                "Use <tt>127.0.0.1</tt> should be correct in almost every situation. "
                                "It is possible - though uncommon - to do a remote monitoring here."
                            ),
                            prefill=DefaultValue("127.0.0.1"),
                        ),
                    ),
                    CascadingSingleChoiceElement(
                        name="use_local_fqdn",
                        title=Title("Use local FQDN"),
                        parameter_form=FixedValue(
                            value=None,
                            title=Title(
                                "Use the FQDN of the machine on which the agent is running."
                            ),
                        ),
                    ),
                ],
                prefill=DefaultValue("ip_or_fqdn"),
            ),
        ),
        "port": DictElement(
            required=False,
            parameter_form=Integer(
                title=Title("TCP port for connection"),
                prefill=DefaultValue(8080),
                custom_validate=(validators.NetworkPort(),),
            ),
        ),
        "timeout": DictElement(
            required=False,
            parameter_form=Float(
                title=Title("Connection timeout in seconds"),
                help_text=Help(
                    "Tell the Jolokia plug-in to stop waiting for a response from each configured instance"
                    " after the provided number of seconds have passed. This time limit is applied both to"
                    " the initial connection, as well as the time the plug-in has to wait between chunks of data"
                    " it receives."
                ),
                prefill=DefaultValue(1.0),
            ),
        ),
        "login": DictElement(
            required=False,
            parameter_form=Dictionary(
                title=Title("Optional login (if required)"),
                elements={
                    "user": DictElement(
                        required=True,
                        parameter_form=String(
                            title=Title("User ID for web login (if login required)"),
                            prefill=DefaultValue("monitoring"),
                        ),
                    ),
                    "password": DictElement(
                        required=True,
                        parameter_form=Password(
                            title=Title("Password for this user"),
                        ),
                    ),
                    "mode": DictElement(
                        required=True,
                        parameter_form=SingleChoice(
                            title=Title("Login mode"),
                            elements=[
                                SingleChoiceElement(
                                    name="basic",
                                    # weblate-flags: read-only, vendor-name
                                    title=Title("HTTP Basic authentication"),
                                ),
                                # weblate-flags: read-only, vendor-name
                                SingleChoiceElement(name="digest", title=Title("HTTP Digest")),
                            ],
                            prefill=DefaultValue("basic"),
                        ),
                    ),
                },
            ),
        ),
        "suburi": DictElement(
            required=False,
            parameter_form=String(
                title=Title("Relative URI under which Jolokia is visible"),
                prefill=DefaultValue("jolokia"),
                field_size=FieldSize.MEDIUM,
            ),
        ),
        "instance": DictElement(
            required=False,
            parameter_form=String(
                title=Title("Name of the instance in the monitoring"),
                help_text=Help(
                    "If you do not specify a name here, then the TCP port number "
                    "will be used as an instance name."
                ),
            ),
        ),
        # TODO: These instance parameters used by mk_jolokia are all missing!!
        # cert_path
        # client_cert
        # client_key
        # service_url
        # service_user
        # service_password
        # product
        "custom_vars": DictElement(
            required=False,
            parameter_form=List(
                title=Title("Custom MBeans"),
                element_template=Dictionary(
                    elements={
                        "mbean": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("MBean"),
                                help_text=Help(
                                    "The MBean's object name, for example java.lang:type=Memory"
                                ),
                            ),
                        ),
                        "path": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Path"),
                                help_text=Help(
                                    "The path to the value within the MBean,"
                                    " for example NonHeapMemoryUsage/used"
                                ),
                            ),
                        ),
                        "value_type": DictElement(
                            required=True,
                            parameter_form=SingleChoice(
                                title=Title("Value Type"),
                                help_text=Help(
                                    "Choose the logic with which the value is to be interpreted."
                                ),
                                elements=[
                                    SingleChoiceElement(name="string", title=Title("String")),
                                    SingleChoiceElement(
                                        name="number", title=Title("Numeric value")
                                    ),
                                    SingleChoiceElement(name="rate", title=Title("Rate of change")),
                                ],
                            ),
                        ),
                        "title": DictElement(
                            required=False,
                            parameter_form=String(
                                title=Title("Title"),
                                help_text=Help(
                                    "The title under which the value will appear in Checkmk."
                                    " Defaults to path if unspecified."
                                ),
                            ),
                        ),
                    },
                ),
            ),
        ),
    }


def _form_spec_agent_config_mk_jolokia() -> Dictionary:
    return Dictionary(
        title=Title("JMX monitoring of Java JVMs using Jolokia"),
        help_text=Help(
            "This will deploy and configure the Checkmk agent plug-in <tt>mk_jolokia</tt>. "
            "In order to use this you need the Jolokia <tt>.war</tt> file from the"
            " <a href='http://www.jolokia.org/index.html'>Jolokia Project Homepage</a>"
            " deployed in your JVMs. Currently at least Tomcat, JBoss and BEA Weblogic are"
            " supported. Please note: The Checkmk <tt>mk_jolokia</tt> plug-in requires both"
            " the requests Python library on the host running the plug-in <b>and</b> the"
            " WAR file on the JVMs."
        ),
        migrate=_migrate_to_agent_config,
        elements={
            "deployment": DictElement(
                required=True,
                parameter_form=SingleChoice(
                    title=Title("Deployment"),
                    prefill=DefaultValue("sync"),
                    elements=[
                        SingleChoiceElement(
                            name="sync",
                            title=Title("Deploy the Jolokia plug-in"),
                        ),
                        SingleChoiceElement(
                            name="do_not_deploy",
                            title=Title("Do not deploy the Jolokia plug-in"),
                        ),
                    ],
                ),
            ),
            **_jolokia_instance_elements(),
            "instances": DictElement(
                required=False,
                parameter_form=List(
                    title=Title("Monitor multiple JMX instances on the host"),
                    help_text=Help(
                        "You just need to specify values that are different from "
                        "the default values that you've specified above."
                    ),
                    element_template=Dictionary(
                        elements=_jolokia_instance_elements(),
                    ),
                ),
            ),
        },
    )


rule_spec_mk_jolokia = AgentConfig(
    name="mk_jolokia",
    title=Title("JMX monitoring of Java JVMs using Jolokia (Linux, Windows)"),
    topic=Topic.APPLICATIONS,
    parameter_form=_form_spec_agent_config_mk_jolokia,
)
