#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from cmk.gui.i18n import _
from cmk.gui.plugins.wato.active_checks.common import RulespecGroupActiveChecks
from cmk.gui.plugins.wato.utils import (
    HostRulespec,
    MigrateToIndividualOrStoredPassword,
    rulespec_registry,
)
from cmk.gui.valuespec import Checkbox, Dictionary, Integer, TextInput, Tuple


def _valuespec_active_checks_sftp():
    return Tuple(
        title=_("Check SFTP Service"),
        help=_(
            "Check functionality of a SFTP server. You can use the default values for putting or getting "
            "a file. This file will then be created for the test and deleted afterwards. It will of course not "
            "deleted if it was not created by this active check."
        ),
        elements=[
            TextInput(title=_("Hostname"), allow_empty=False),
            TextInput(title=_("Username"), allow_empty=False),
            MigrateToIndividualOrStoredPassword(title=_("Password"), allow_empty=False),
            Dictionary(
                default_keys=["look_for_keys"],
                elements=[
                    (
                        "description",
                        TextInput(title=_("Service Description"), default_value="SFTP", size=30),
                    ),
                    ("port", Integer(title=_("Port"), default_value=22)),
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
                        Tuple(
                            title=_("Put file to SFTP server"),
                            elements=[
                                TextInput(
                                    title=_("Local file"),
                                    size=30,
                                    default_value="check_mk_testfile",
                                    help=_(
                                        "Local path to the file to be uploaded. The path is "
                                        'relative to "var/check_mk/active_checks/check_sftp" '
                                        "within the home directory of your site. If the file does "
                                        "not exist, it will be created. Example: 'testfile.txt' "
                                        "(The file $OMD_ROOT/var/check_mk/active_checks/check_sftp/"
                                        "testfile.txt will be uploaded)."
                                    ),
                                ),
                                TextInput(
                                    title=_("Remote destination"),
                                    size=30,
                                    default_value="",
                                    help=_(
                                        "Remote path to the directory where to put the file. "
                                        "If left empty, the file will be placed in the home "
                                        "directory of the user. The directory has to exist "
                                        "on the remote or the check will fail. "
                                        "Example: 'myDirectory' (The file will be uploaded to "
                                        "'~/myDirectory')."
                                    ),
                                ),
                            ],
                        ),
                    ),
                    (
                        "get",
                        Tuple(
                            title=_("Get file from SFTP server"),
                            elements=[
                                TextInput(
                                    title=_("Remote file"),
                                    size=30,
                                    default_value="check_mk_testfile",
                                    help=_(
                                        "Remote path to the file to be downloaded. The path is "
                                        "relative to the home directory of the user. If you "
                                        "also enabled 'Put file to SFTP server', you can use "
                                        "the same file for both tests."
                                    ),
                                ),
                                TextInput(
                                    title=_("Local destination"),
                                    size=30,
                                    default_value="",
                                    help=_(
                                        "Local path to the directory where to put the file, "
                                        'relative to "var/check_mk/active_checks/check_sftp" '
                                        "within the home directory of your site. If left empty, "
                                        "the file will be placed directly in "
                                        '"var/check_mk/active_checks/check_sftp".'
                                    ),
                                ),
                            ],
                        ),
                    ),
                ],
            ),
        ],
    )


rulespec_registry.register(
    HostRulespec(
        group=RulespecGroupActiveChecks,
        match_type="all",
        name="active_checks:sftp",
        valuespec=_valuespec_active_checks_sftp,
    )
)
