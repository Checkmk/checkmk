#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import json
import urllib.parse
from collections.abc import Mapping, Sequence
from enum import Enum
from functools import lru_cache
from typing import assert_never, Literal

from flask import session

from cmk.gui.exceptions import MKNotFound
from cmk.gui.http import Request
from cmk.gui.i18n import _
from cmk.gui.logged_in import user
from cmk.gui.type_defs import HTTPVariables
from cmk.gui.utils.escaping import escape_text
from cmk.gui.utils.transaction_manager import TransactionManager

QueryVars = Mapping[str, Sequence[str]]

_ALWAYS_SAFE = frozenset(b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_.-~ ")
_ALWAYS_SAFE_BYTES = bytes(_ALWAYS_SAFE)
_QUOTED = {b: chr(b) if b in _ALWAYS_SAFE else f"%{b:02X}" for b in range(256)}


def quote(string: str) -> str:
    """More performant version of urllib.parse equivalent to the call quote(string, safe=' ')."""
    if not string:
        return string
    bs = string.encode("utf-8", "strict")
    if not bs.rstrip(_ALWAYS_SAFE_BYTES):
        return bs.decode()
    return "".join([_QUOTED[char] for char in bs])


@lru_cache(maxsize=4096)
def quote_plus(string: str) -> str:
    """More performant version of urllib.parse equivalent to the call quote_plus(string)."""
    if " " not in string:
        return quote(string)
    return quote(string).replace(" ", "+")


def _quote_pair(varname: str, value: None | int | str) -> str:
    assert isinstance(varname, str)
    if isinstance(value, int):
        return f"{quote_plus(varname)}={quote_plus(str(value))}"
    if value is None:
        # TODO: This is not ideal and should better be cleaned up somehow. Shouldn't
        # variables with None values simply be skipped? We currently can not find the
        # call sites easily. This may be cleaned up once we establish typing. Until then
        # we need to be compatible with the previous behavior.
        return "%s=" % quote_plus(varname)
    return f"{quote_plus(varname)}={quote_plus(value)}"


# TODO: Inspect call sites to this function: Most of them can be replaced with makeuri_contextless
def urlencode_vars(vars_: HTTPVariables) -> str:
    """Convert a mapping object or a sequence of two-element tuples to a “percent-encoded” string"""
    return "&".join([_quote_pair(var, val) for var, val in sorted(vars_)])


# TODO: Inspect call sites to this function: Most of them can be replaced with makeuri_contextless
def urlencode(value: str | None) -> str:
    """Replace special characters in string using the %xx escape."""
    return "" if value is None else quote_plus(value)


def _file_name_from_path(
    path: str,
    on_error: Literal["raise", "ignore"] = "ignore",
    default: str = "index",
) -> str:
    """Derive a "file name" from the path.

    These no longer map to real file names, but rather to the page handlers attached to the names.

    Args:
        path:
            The path, without query string, and without server portion.

    Returns:
        The "file name" as a string.

    Examples:

        Sensible values.

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py")
            'should_match'

            >>> _file_name_from_path("/NO_SITE/check_mk/")
            'index'

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/NO_SITE/check_mk/blubb.py", on_error="ignore")
            'index'

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/NO_SITE/check_mk/blubb.py", on_error="ignore", default="not_found")
            'not_found'

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/NO_SITE/check_mk/blubb.py", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found

            >>> _file_name_from_path("/NO_SITE/check_mk/foo/bar", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found

            >>> _file_name_from_path("/NO_SITE/check_mk/.py", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found

        Not so sensible values. Not sure where this would occur, but tests were in place which
        required this.

            >>> _file_name_from_path("/NO_SITE/check_mk/should_match.py/", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found

        `file_name_and_query_vars_from_url` expects relative URLs, so we sadly need to support
        those as well.

            >>> _file_name_from_path("wato.py")
            'wato'

        This works as expected.

            >>> _file_name_from_path(".py", on_error="raise")
            Traceback (most recent call last):
            ...
            cmk.gui.exceptions.MKNotFound: Not found
    """
    parts = path.split("/")
    if len(parts) in (1, 4) and len(parts[-1]) > 3 and parts[-1].endswith(".py"):
        # If it is a relative url or a URL like /site/check_mk/file.py and the filename is not just
        # the extension (like /site/check_mk/.py) then we have a filename.
        result = parts[-1][:-3]
    elif len(parts) < 5 and not parts[-1]:
        # If we have a "normal" url and not an excessive amount of paths (probably a duplication)
        # and the last part is empty, we have an "index" URL.
        result = "index"
    elif on_error == "raise":
        raise MKNotFound("Not found")
    elif on_error == "ignore":
        result = default
    else:
        assert_never(on_error)

    return result


def requested_file_name(
    request: Request, on_error: Literal["raise", "ignore"] = "ignore", default: str = "index"
) -> str:
    """Convenience wrapper around _file_name_from_path

    Args:
        request:
            A Werkzeug or Flask request wrapper.

    Returns:
        The "file name".

    Examples:

        >>> requested_file_name(Request({"PATH_INFO": "/dev/check_mk/foo_bar.py"}))
        'foo_bar'

        >>> requested_file_name(Request({"PATH_INFO": "/dev/check_mk/foo_bar.py/"}), on_error="raise")
        Traceback (most recent call last):
        ...
        cmk.gui.exceptions.MKNotFound: Not found

        >>> requested_file_name(Request({"PATH_INFO": "/dev/check_mk/foo_bar.py/foo"}), on_error="raise")
        Traceback (most recent call last):
        ...
        cmk.gui.exceptions.MKNotFound: Not found

    """
    return _file_name_from_path(request.path, on_error=on_error, default=default)


def requested_file_with_query(request: Request) -> str:
    """Returns a string containing the requested file name and query to be used in hyperlinks"""
    file_name = requested_file_name(request)
    query = request.query_string.decode("utf-8")
    return f"{file_name}.py?{query}"


def makeuri(
    request: Request,
    addvars: HTTPVariables,
    filename: str | None = None,
    remove_prefix: str | None = None,
    delvars: Sequence[str] | None = None,
) -> str:
    new_vars = [nv[0] for nv in addvars]
    vars_: HTTPVariables = [
        (v, val)
        for v, val in request.itervars()
        if v[0] != "_" and v not in new_vars and not (delvars and v in delvars)
    ]
    if remove_prefix is not None:
        vars_ = [i for i in vars_ if not i[0].startswith(remove_prefix)]
    vars_ = vars_ + addvars
    if filename is None:
        filename = urlencode(requested_file_name(request)) + ".py"
    if vars_:
        return filename + "?" + urlencode_vars(vars_)
    return filename


def makeuri_contextless(
    request: Request,
    vars_: HTTPVariables,
    filename: str | None = None,
) -> str:
    if not filename:
        filename = requested_file_name(request) + ".py"
    if vars_:
        return filename + "?" + urlencode_vars(vars_)
    return filename


def makeactionuri(
    request: Request,
    transaction_manager: TransactionManager,
    addvars: HTTPVariables,
    filename: str | None = None,
    delvars: Sequence[str] | None = None,
) -> str:
    session_vars: HTTPVariables = [("_transid", transaction_manager.get())]
    if session and hasattr(session, "session_info"):
        session_vars.append(("_csrf_token", session.session_info.csrf_token))

    return makeuri(request, addvars + session_vars, filename=filename, delvars=delvars)


def makeactionuri_contextless(
    request: Request,
    transaction_manager: TransactionManager,
    addvars: HTTPVariables,
    filename: str | None = None,
) -> str:
    session_vars: HTTPVariables = [("_transid", transaction_manager.get())]
    if session and hasattr(session, "session_info"):
        session_vars.append(("_csrf_token", session.session_info.csrf_token))

    return makeuri_contextless(request, addvars + session_vars, filename=filename)


def makeuri_contextless_rulespec_group(
    request: Request,
    group_name: str,
) -> str:
    return makeuri_contextless(
        request,
        [("group", group_name), ("mode", "rulesets")],
        filename="wato.py",
    )


def make_confirm_link(
    *,
    url: str,
    title: str,
    suffix: str | None = None,
    message: str | None = None,
    confirm_button: str | None = None,
    cancel_button: str | None = None,
) -> str:
    return _make_customized_confirm_link(
        url=url,
        title=get_confirm_link_title(title, suffix),
        confirm_button=confirm_button if confirm_button else _("Yes"),
        cancel_button=cancel_button if cancel_button else _("No"),
        message=message,
    )


def make_confirm_delete_link(
    *,
    url: str,
    title: str,
    suffix: str | None = None,
    message: str | None = None,
    confirm_button: str | None = None,
    cancel_button: str | None = None,
    warning: bool = False,
    post_confirm_waiting_text: str | None = None,
) -> str:
    return _make_customized_confirm_link(
        url=url,
        title=get_confirm_link_title(title, suffix),
        confirm_button=confirm_button if confirm_button else _("Delete"),
        cancel_button=cancel_button if cancel_button else _("Cancel"),
        message=message,
        icon="warning" if warning else "question",
        custom_class_options={
            "confirmButton": "confirm_warning" if warning else "confirm_question",
            "icon": "confirm_icon" + (" confirm_warning" if warning else " confirm_question"),
        },
        post_confirm_waiting_text=post_confirm_waiting_text,
    )


def _make_customized_confirm_link(
    *,
    url: str,
    title: str,
    confirm_button: str,
    cancel_button: str,
    message: str | None = None,
    icon: str | None = None,
    custom_class_options: dict[str, str] | None = None,
    post_confirm_waiting_text: str | None = None,
) -> str:
    return "javascript:cmk.forms.confirm_link({}, {}, {}, {}),cmk.popup_menu.close_popup()".format(
        json.dumps(quote_plus(url)),
        json.dumps(escape_text(message, escape_links=True)),
        json.dumps(
            {
                "title": escape_text(title, escape_links=True),
                "confirmButtonText": confirm_button,
                "cancelButtonText": cancel_button,
                "icon": icon if icon else "question",
                "customClass": custom_class_options if custom_class_options else {},
            }
        ),
        json.dumps(post_confirm_waiting_text),
    )


def get_confirm_link_title(
    title: str | None = None,
    suffix: str | None = None,
) -> str:
    if title is None:
        return ""
    if title and suffix:
        return title + f" - {suffix}?"
    return title + "?"


def file_name_and_query_vars_from_url(url: str) -> tuple[str, QueryVars]:
    """Deconstruct a (potentially relative) URL.

    Args:
        url:
            A URL path without the server portion, but optionally including the `query string`.

    Returns:
        A tuple of "file name" and a parsed query string dict.

    Examples:

        With path and query string (relative)

            >>> file_name_and_query_vars_from_url("wato.py?foo=bar")
            ('wato', {'foo': ['bar']})

        With path and query string (absolute)

            >>> file_name_and_query_vars_from_url("/dev/check_mk/wato.py?foo=bar")
            ('wato', {'foo': ['bar']})

        Without path

            >>> file_name_and_query_vars_from_url("?foo=bar")
            ('index', {'foo': ['bar']})

        Without path and without query string

            >>> file_name_and_query_vars_from_url("")
            ('index', {})

    """
    split_result = urllib.parse.urlsplit(url)
    return _file_name_from_path(split_result.path), urllib.parse.parse_qs(split_result.query)


class DocReference(Enum):
    """All references to the documentation - e.g. "[intro_setup#install|Welcome]" - must be listed
    in DocReference. The string must consist of the page name and if an anchor exists the anchor
    name joined by a '#'. E.g. INTRO_SETUP_INSTALL = "intro_setup#install"""

    ACTIVE_CHECKS = "active_checks"
    ACTIVE_CHECKS_MRPE = "active_checks#mrpe"
    AGENT_LINUX = "agent_linux"
    AGENT_WINDOWS = "agent_windows"
    AGENT_LINUX_LEGACY = "agent_linux_legacy"
    ALERT_HANDLERS = "alert_handlers"
    ANALYZE_CONFIG = "analyze_configuration"
    ANALYZE_NOTIFICATIONS = "notifications#_rule_evaluation_by_the_notification_module"
    AWS = "monitoring_aws"
    AWS_MANUAL_VM = "monitoring_aws#_manually_creating_hosts_for_ec2_instances"
    AZURE = "monitoring_azure"
    BACKUPS = "backup"
    BI = "bi"  # Business Intelligence
    BOOKMARK_LIST = "user_interface#bookmarks"
    CERTIFICATES = "certificates"
    COMMANDS = "commands"
    COMMANDS_ACK = "basics_ackn"
    COMMANDS_DOWNTIME = "basics_downtimes"
    CUSTOM_GRAPH = "graphing#custom_graphs"
    DASHBOARD_HOST_PROBLEMS = "dashboards#host_problems"
    DASHBOARDS = "dashboards"
    DCD = "dcd"  # dynamic host configuration
    DEVEL_CHECK_PLUGINS = "devel_intro"
    DIAGNOSTICS = "support_diagnostics"
    DIAGNOSTICS_CLI = "support_diagnostics#commandline"
    DISTRIBUTED_MONITORING = "distributed_monitoring"
    EVENTCONSOLE = "ec"
    FORECAST_GRAPH = "forecast_graphs"
    FINETUNING_MONITORING = "intro_finetune"
    GCP = "monitoring_gcp"
    GCP_MANUAL_VM = "monitoring_gcp#_manually_creating_hosts_for_vm_instances"
    GRAPHING_RRDS = "graphing#rrds"
    HOST_TAGS = "host_tags"
    INFLUXDB_CONNECTIONS = "metrics_exporter"
    INTRO_BESTPRACTICE = "intro_bestpractise"
    INTRO_CREATING_FOLDERS = "intro_setup_monitor#folders"
    INTRO_FOLDERS = "intro_setup_monitor#folders"
    INTRO_GUI = "intro_gui"
    INTRO_LINUX = "intro_setup_monitor#linux"
    INTRO_SERVICES = "intro_setup_monitor#services"
    INTRO_WELCOME = "welcome"
    INTRO_SETUP = "intro_setup"
    KUBERNETES = "monitoring_kubernetes"
    LICENSING = "license"
    LDAP = "ldap"
    MKPS = "mkps"
    NOTIFICATIONS = "notifications"
    NTOPNG_CONNECT = "ntop#ntop_connect"
    PIGGYBACK = "piggyback"
    PROMETHEUS = "monitoring_prometheus"
    REGEXES = "regexes"
    REPLACE_AGENT_SIGNATURE_KEYS = "agent_deployment#replacing_signature_keys"
    REST_API = "rest_api"
    REPORTS = "reporting"
    SLA_CONFIGURATION = "sla"
    TIMEPERIODS = "timeperiods"
    TEST_NOTIFICATIONS = "notifications#notification_testing"
    USER_INTERFACE = "user_interface"
    VIEWS = "views"
    VMWARE = "monitoring_vmware"
    WATO_AGENTS = "wato_monitoringagents"
    WATO_HOSTS = "wato_hosts"
    WATO_RULES = "wato_rules"
    WATO_RULES_DEPCRECATED = "wato_rules#obsolete_rule_sets"
    WATO_RULES_IN_USE = "wato_rules#_rule_sets_in_use"
    WATO_RULES_INEFFECTIVE = "wato_rules#ineffective_rules"
    WATO_RULES_LABELS = "wato_rules#_labels"
    WATO_SERVICES = "wato_services"
    WATO_SERVICES_ENFORCED_SERVICES = "wato_services#enforced_services"
    WATO_USER = "wato_user"
    WATO_USER_2FA = "wato_user#2fa"

    @classmethod
    def has_key(cls, key: str) -> bool:
        return key in cls._member_names_


def doc_reference_url(doc_ref: DocReference | None = None) -> str:
    base = user.get_docs_base_url()
    origin = "?origin=checkmk"
    if doc_ref is None:
        return base + origin
    if "#" not in doc_ref.value:
        return f"{base}/{doc_ref.value}.html{origin}"
    return f"{base}/{doc_ref.value.replace('#', f'.html{origin}#', 1)}"


class YouTubeReference(Enum):
    """All references to youtube videos must be listed in YouTubeReference. The string must hold a
    valid video id."""

    INSTALLING_CHECKMK = "opO-SOgOJ1I"
    MONITORING_WINDOWS = "Nxiq7Jb9mB4"

    @classmethod
    def has_key(cls, key: str) -> bool:
        return key in cls._member_names_


def youtube_reference_url(youtube_ref: YouTubeReference | None = None) -> str:
    # Default to the Checkmk youtube channel
    if youtube_ref is None:
        return "https://youtube.com/@checkmk-channel"
    return "https://youtu.be/%s" % youtube_ref.value


class WerkReference(Enum):
    DECOMMISSION_V1_API = 17201

    def ref(self) -> str:
        return f"Werk #{self.value}"


def werk_reference_url(werk: WerkReference) -> str:
    return f"https://checkmk.com/werk/{werk.value}"
