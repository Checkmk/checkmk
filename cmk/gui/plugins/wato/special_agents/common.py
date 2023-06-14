#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from typing import Any

from cmk.utils import aws_constants

from cmk.gui.exceptions import MKUserError
from cmk.gui.i18n import _
from cmk.gui.plugins.wato.utils import (
    MigrateToIndividualOrStoredPassword,
    rulespec_group_registry,
    RulespecGroup,
    RulespecSubGroup,
)
from cmk.gui.utils.urls import DocReference
from cmk.gui.valuespec import (
    Alternative,
    CascadingDropdown,
    Dictionary,
    DictionaryEntry,
    DropdownChoice,
    FixedValue,
    HTTPUrl,
    ListOf,
    NetworkPort,
    RegExp,
    TextInput,
)


@rulespec_group_registry.register
class RulespecGroupVMCloudContainer(RulespecGroup):
    @property
    def name(self) -> str:
        return "vm_cloud_container"

    @property
    def title(self) -> str:
        return _("VM, Cloud, Container")

    @property
    def help(self):
        return _("Integrate with VM, cloud or container platforms")

    @property
    def doc_references(self) -> dict[DocReference, str]:
        return {
            DocReference.WATO_AGENTS: _("Monitoring agents"),
            DocReference.VMWARE: _("Monitoring VMWare ESXi"),
            DocReference.AWS: _("Monitoring Amazon Web Services (AWS)"),
            DocReference.AZURE: _("Monitoring Microsoft Azure"),
            DocReference.GCP: _("Monitoring Google Cloud Platform (GCP)"),
            DocReference.KUBERNETES: _("Monitoring Kubernetes"),
            DocReference.PROMETHEUS: _("Integrating Prometheus"),
        }


@rulespec_group_registry.register
class RulespecGroupDatasourcePrograms(RulespecGroup):
    @property
    def name(self) -> str:
        return "datasource_programs"

    @property
    def title(self) -> str:
        return _("Other integrations")

    @property
    def help(self):
        return _("Integrate platforms using special agents, e.g. SAP R/3")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsOS(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "os"

    @property
    def title(self) -> str:
        return _("Operating systems")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsApps(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "apps"

    @property
    def title(self) -> str:
        return _("Applications")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsCloud(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "cloud"

    @property
    def title(self) -> str:
        return _("Cloud based environments")


class RulespecGroupDatasourceProgramsContainer(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "container"

    @property
    def title(self) -> str:
        return _("Containerization")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsCustom(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "custom"

    @property
    def title(self) -> str:
        return _("Custom integrations")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsHardware(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "hw"

    @property
    def title(self) -> str:
        return _("Hardware")


@rulespec_group_registry.register
class RulespecGroupDatasourceProgramsTesting(RulespecSubGroup):
    @property
    def main_group(self) -> type[RulespecGroup]:
        return RulespecGroupDatasourcePrograms

    @property
    def sub_group_name(self) -> str:
        return "testing"

    @property
    def title(self) -> str:
        return _("Testing")


def api_request_authentication() -> DictionaryEntry:
    return (
        "auth_basic",
        CascadingDropdown(
            title=_("Authentication"),
            choices=[
                (
                    "auth_login",
                    _("Basic authentication"),
                    Dictionary(
                        elements=[
                            (
                                "username",
                                TextInput(
                                    title=_("Login username"),
                                    allow_empty=False,
                                ),
                            ),
                            (
                                "password",
                                MigrateToIndividualOrStoredPassword(
                                    title=_("Password"),
                                    allow_empty=False,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                ),
                (
                    "auth_token",
                    _("Token authentication"),
                    Dictionary(
                        elements=[
                            (
                                "token",
                                MigrateToIndividualOrStoredPassword(
                                    title=_("Login token"),
                                    allow_empty=False,
                                ),
                            ),
                        ],
                        optional_keys=[],
                    ),
                ),
            ],
        ),
    )


def api_request_connection_elements(  # type: ignore[no-untyped-def]
    help_text: str, default_port: int
):
    return [
        ("port", NetworkPort(title=_("Port"), default_value=default_port)),
        (
            "path-prefix",
            TextInput(title=_("Custom path prefix"), help=help_text, allow_empty=False),
        ),
    ]


def filter_kubernetes_namespace_element():
    return (
        "namespace_include_patterns",
        ListOf(
            valuespec=RegExp(
                mode=RegExp.complete,
                title=_("Pattern"),
                allow_empty=False,
            ),
            title=_("Monitor namespaces matching"),
            add_label=_("Add new pattern"),
            allow_empty=False,
            help=_(
                "If your cluster has multiple namespaces, you can specify "
                "a list of regex patterns. Only matching namespaces will "
                "be monitored. Note that this concerns everything which "
                "is part of the matching namespaces such as pods for "
                "example."
            ),
        ),
    )


def connection_set(options: list[str] | None = None, auth_option: str | None = None) -> list[Any]:
    """Standard connection elements set

    A set of frequently used connection configuration options.
    Using the listed elements here allows to use additional helper functions
    in base/check_legacy_includes/agent_helper & in cmk/special_agents/utils.py which serve
    to facilitate the API connection setup from the special_agent side

    Args:
        options:
            list of strings specifying which connection elements to include. If empty
            then all connection elements will be included
        auth_option:
            string which specify which connection authentication element to include

    Returns:
        list of Setup connection elements

    """
    connection_options: list[Any] = []
    if options is None:
        all_options = True
        options = []
    else:
        all_options = False

    if "connection_type" in options or all_options:
        connection_options.append(
            (
                "connection",
                CascadingDropdown(
                    choices=[
                        ("host_name", _("Host name")),
                        ("ip_address", _("IP Address")),
                        (
                            "url_custom",
                            _("Custom URL"),
                            Dictionary(
                                elements=[
                                    (
                                        "url_address",
                                        TextInput(
                                            title=_("Custom URL server address"),
                                            help=_(
                                                "Specify a custom URL to connect to "
                                                "your server. Do not include the "
                                                "protocol. This option overwrites "
                                                "all available options such as port and "
                                                "other URL prefixes."
                                            ),
                                            allow_empty=False,
                                        ),
                                    )
                                ],
                                optional_keys=[],
                            ),
                        ),
                    ],
                    title=_("Connection option"),
                ),
            )
        )

    if "port" in options or all_options:
        connection_options.append(
            (
                "port",
                NetworkPort(
                    title=_("TCP port number"),
                    help=_("Port number that server is listening on."),
                    default_value=4223,
                    minvalue=1,
                    maxvalue=65535,
                ),
            )
        )

    if "protocol" in options or all_options:
        connection_options.append(
            (
                "protocol",
                DropdownChoice(
                    title=_("Protocol"),
                    choices=[
                        ("http", "HTTP"),
                        ("https", "HTTPS"),
                    ],
                ),
            )
        )

    if "url_prefix" in options or all_options:
        connection_options.append(
            (
                "url-prefix",
                HTTPUrl(
                    title=_("Custom URL prefix"),
                    help=_(
                        "Specifies a URL prefix which is prepended to the path in calls to "
                        "the API. This is e.g. useful if you use the ip address or the hostname "
                        "as base address but require some additional prefix to make the correct "
                        "API call. Use the custom URL option if you need to specify a more "
                        "complex API url."
                    ),
                    allow_empty=False,
                ),
            )
        )

    if "path_prefix" in options or all_options:
        connection_options.append(
            (
                "path-prefix",
                TextInput(
                    title=_("Custom path prefix"),
                    help=_(
                        "Specifies an URL path suffix which is appended to the path in calls "
                        "to the API. This is e.g. useful if you use the ip address or the hostname "
                        "as base address and require to specify a path URL in order to make the "
                        'correct API calls. Do not prepend or append your custom path with "/". '
                        "Use the custom URL option if you need to specify a "
                        "more complex API URL"
                    ),
                    allow_empty=False,
                ),
            )
        )

    if "ssl_verify" in options or all_options:
        connection_options.append(
            (
                "no-cert-check",
                Alternative(
                    title=_("SSL certificate verification"),
                    elements=[
                        FixedValue(value=False, title=_("Verify the certificate"), totext=""),
                        FixedValue(
                            value=True, title=_("Ignore certificate errors (unsecure)"), totext=""
                        ),
                    ],
                    default_value=False,
                ),
            )
        )

    if auth_option:
        connection_options.extend(_auth_option(auth_option))

    return connection_options


def _auth_option(option: str) -> list[Any]:
    auth: list[Any] = []
    if option == "basic":
        auth.append(
            (
                "auth_basic",
                Dictionary(
                    elements=[
                        (
                            "username",
                            TextInput(
                                title=_("Login username"),
                                allow_empty=False,
                            ),
                        ),
                        (
                            "password",
                            MigrateToIndividualOrStoredPassword(
                                title=_("Password"),
                                allow_empty=False,
                            ),
                        ),
                    ],
                    optional_keys=[],
                    title=_("Basic authentication"),
                ),
            )
        )

    elif option == "token":
        auth.append(
            (
                "token",
                TextInput(
                    title=_("API key/token"),
                    allow_empty=False,
                    size=70,
                ),
            )
        )
    return auth


def validate_aws_tags(value, varprefix):
    used_keys = []
    # KEY:
    # ve_p_services_p_ec2_p_choice_1_IDX_0
    # VALUES:
    # ve_p_services_p_ec2_p_choice_1_IDX_1_IDX
    for idx_tag, (tag_key, tag_values) in enumerate(value):
        tag_field = f"{varprefix}_{idx_tag + 1}_0"
        if tag_key not in used_keys:
            used_keys.append(tag_key)
        else:
            raise MKUserError(
                tag_field, _("Each tag must be unique and cannot be used multiple times")
            )
        if tag_key.startswith("aws:"):
            raise MKUserError(tag_field, _("Do not use 'aws:' prefix for the key."))
        if len(tag_key) > 128:
            raise MKUserError(tag_field, _("The maximum key length is 128 characters."))
        if len(tag_values) > 50:
            raise MKUserError(tag_field, _("The maximum number of tags per resource is 50."))

        for idx_values, v in enumerate(tag_values):
            values_field = f"{varprefix}_{idx_tag + 1}_1_{idx_values + 1}"
            if len(v) > 256:
                raise MKUserError(values_field, _("The maximum value length is 256 characters."))
            if v.startswith("aws:"):
                raise MKUserError(values_field, _("Do not use 'aws:' prefix for the values."))


def ssl_verification():
    return (
        "verify-cert",
        Alternative(
            title=_("SSL certificate verification"),
            elements=[
                FixedValue(value=True, title=_("Verify the certificate"), totext=""),
                FixedValue(value=False, title=_("Ignore certificate errors (unsecure)"), totext=""),
            ],
            default_value=False,
        ),
    )


def aws_region_to_monitor() -> list[tuple[str, str]]:
    def key(regionid_display: tuple[str, str]) -> str:
        return regionid_display[1]

    regions_by_display_order = [
        *sorted((r for r in aws_constants.AWSRegions if "GovCloud" not in r[1]), key=key),
        *sorted((r for r in aws_constants.AWSRegions if "GovCloud" in r[1]), key=key),
    ]
    return [(id_, " | ".join((region, id_))) for id_, region in regions_by_display_order]
