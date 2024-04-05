#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.utils.rulesets.definition import RuleGroup

from cmk.gui.i18n import _
from cmk.gui.valuespec import Checkbox, Dictionary, Integer, Migrate, NetworkPort, TextInput
from cmk.gui.wato import IndividualOrStoredPassword, RulespecGroupActiveChecks
from cmk.gui.watolib.rulespecs import HostRulespec, rulespec_registry


def _valuespec_active_checks_sftp():
    return Migrate(
        migrate=lambda p: (
            p if isinstance(p, dict) else {"host": p[0], "user": p[1], "secret": p[2], **p[3]}
        ),
        valuespec=Dictionary(
            title=_("Check SFTP Service"),
            help=_(
                "Check functionality of a SFTP server. You can use the default values for putting or getting "
                "a file. This file will then be created for the test and deleted afterwards. It will of course not "
                "deleted if it was not created by this active check."
            ),
            optional_keys=[
                "description",
                "port",
                "look_for_keys",
                "timeout",
                "timestamp",
                "put",
                "get",
            ],
            elements=[
                (
                    "host",
                    TextInput(title=_("Hostname"), allow_empty=False),
                ),
                (
                    "user",
                    TextInput(title=_("Username"), allow_empty=False),
                ),
                (
                    "secret",
                    IndividualOrStoredPassword(title=_("Password"), allow_empty=False),
                ),
                (
                    "description",
                    TextInput(title=_("Service Description"), default_value="SFTP", size=30),
                ),
                ("port", NetworkPort(title=_("Port"), default_value=22)),
                (
                    "look_for_keys",
                    Checkbox(
                        title=_("Look for keys"),
                        label=_("Search for discoverable keys in the '~/.ssh' directory"),
                    ),
                ),
                ("timeout", Integer(title=_("Timeout"), default_value=10)),
                (
                    "timestamp",
                    TextInput(
                        title=_("Timestamp of a remote file"),
                        size=30,
                        help=_(
                            "Show timestamp of a given file. You only need to specify the "
                            "relative path of the remote file. Examples: 'myDirectory/testfile' "
                            " or 'testfile'"
                        ),
                    ),
                ),
                (
                    "put",
                    Migrate(
                        migrate=lambda p: (
                            p if isinstance(p, dict) else {"local": p[0], "remote": p[1]}
                        ),
                        valuespec=Dictionary(
                            title=_("Put file to SFTP server"),
                            optional_keys=[],
                            elements=[
                                (
                                    "local",
                                    TextInput(
                                        title=_("Local file"),
                                        size=30,
                                        default_value="tmp/check_mk_testfile",
                                        help=_(
                                            "Local path including filename. Base directory for this relative path "
                                            "will be the home directory of your site. The testfile will be created "
                                            "if it does not exist. Examples: 'tmp/testfile' (file will be located in "
                                            "$OMD_ROOT/tmp/testfile )"
                                        ),
                                    ),
                                ),
                                (
                                    "remote",
                                    TextInput(
                                        title=_("Remote destination"),
                                        size=30,
                                        default_value="",
                                        help=_(
                                            "Remote path where to put the file. If you leave this empty, the file will be placed "
                                            "in the home directory of the user. Example: 'myDirectory' "
                                        ),
                                    ),
                                ),
                            ],
                        ),
                    ),
                ),
                (
                    "get",
                    Migrate(
                        migrate=lambda p: (
                            p if isinstance(p, dict) else {"remote": p[0], "local": p[1]}
                        ),
                        valuespec=Dictionary(
                            title=_("Get file from SFTP server"),
                            optional_keys=[],
                            elements=[
                                (
                                    "remote",
                                    TextInput(
                                        title=_("Remote file"),
                                        size=30,
                                        default_value="check_mk_testfile",
                                        help=_(
                                            "Remote path including filename "
                                            "(e.g. 'testfile'). If you also enabled "
                                            "'Put file to SFTP server', you can use the same file for both tests."
                                        ),
                                    ),
                                ),
                                (
                                    "local",
                                    TextInput(
                                        title=_("Local destination"),
                                        size=30,
                                        default_value="tmp",
                                        help=_(
                                            "Local path where to put the downloaded file "
                                            "(e.g. 'tmp' )."
                                        ),
                                    ),
                                ),
                            ],
                        ),
                    ),
                ),
            ],
        ),
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name=RuleGroup.ActiveChecks("sftp"),
        valuespec=_valuespec_active_checks_sftp,
    )
)
