#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.


from collections.abc import Mapping

from cmk.rulesets.v1 import Help, Label, Title
from cmk.rulesets.v1.form_specs import (
    BooleanChoice,
    DefaultValue,
    DictElement,
    Dictionary,
    InputHint,
    Integer,
    migrate_to_password,
    Password,
    String,
    TimeMagnitude,
    TimeSpan,
    validators,
)
from cmk.rulesets.v1.rule_specs import ActiveCheck, Topic


def _migrate_from_tuple(params: object) -> Mapping[str, object]:
    match params:
        case (str(host), str(user), (str(secret_type), str(secret)), {**rest}):
            return {
                "host": host,
                "user": user,
                "secret": (secret_type, secret),
                **{str(k): v for k, v in rest.items()},
            }
        case dict():
            return params
    raise ValueError(params)


def _migrate_put_params(params: object) -> Mapping[str, object]:
    match params:
        case (str(local), str(remote)):
            return {"local": local, "remote": remote}
        case dict():
            return params
    raise ValueError(params)


def _migrate_get_params(params: object) -> Mapping[str, object]:
    match params:
        case (str(remote), str(local)):
            return {"local": local, "remote": remote}
        case dict():
            return params
    raise ValueError(params)


def _make_form_spec_check_sftp() -> Dictionary:
    return Dictionary(
        migrate=_migrate_from_tuple,
        title=Title("Check SFTP Service"),
        help_text=Help(
            "Check functionality of a SFTP server. You can use the default values for putting or getting "
            "a file. This file will then be created for the test and deleted afterwards. It will of course not "
            "deleted if it was not created by this active check."
        ),
        elements={
            "host": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Hostname"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "user": DictElement(
                required=True,
                parameter_form=String(
                    title=Title("Username"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                ),
            ),
            "secret": DictElement(
                required=True,
                parameter_form=Password(
                    title=Title("Password"),
                    custom_validate=(validators.LengthInRange(min_value=1),),
                    migrate=migrate_to_password,
                ),
            ),
            "description": DictElement(
                parameter_form=String(
                    title=Title("Service description"),
                    prefill=DefaultValue("SFTP"),
                ),
            ),
            "port": DictElement(
                parameter_form=Integer(
                    title=Title("Port"),
                    prefill=DefaultValue(22),
                    custom_validate=(validators.NetworkPort(),),
                )
            ),
            "look_for_keys": DictElement(
                parameter_form=BooleanChoice(
                    title=Title("Look for keys"),
                    label=Label("Search for discoverable keys in the '~/.ssh' directory"),
                    prefill=DefaultValue(True),
                ),
            ),
            "timeout": DictElement(
                parameter_form=TimeSpan(
                    title=Title("Timeout"),
                    prefill=DefaultValue(10),
                    migrate=float,  # type: ignore[arg-type]  # wrong type, but desired behaviour.
                    displayed_magnitudes=[TimeMagnitude.SECOND],
                ),
            ),
            "timestamp": DictElement(
                parameter_form=String(
                    title=Title("Timestamp of a remote file"),
                    help_text=Help(
                        "Show timestamp of a given file. You only need to specify the "
                        "relative path of the remote file. Examples: 'myDirectory/testfile' "
                        " or 'testfile'"
                    ),
                ),
            ),
            "put": DictElement(
                parameter_form=Dictionary(
                    migrate=_migrate_put_params,
                    title=Title("Put file to SFTP server"),
                    elements={
                        "local": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Local file"),
                                prefill=InputHint("check_mk_testfile"),
                                help_text=Help(
                                    "Local path to the file to be uploaded. The path is "
                                    'relative to "var/check_mk/active_checks/check_sftp" '
                                    "within the home directory of your site. If the file "
                                    "does not exist, it will be created. Example: "
                                    "'testfile.txt' (The file $OMD_ROOT/var/check_mk/"
                                    "active_checks/check_sftp/testfile.txt will be uploaded)."
                                ),
                            ),
                        ),
                        "remote": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Remote destination"),
                                help_text=Help(
                                    "Remote path to the directory where to put the file. "
                                    "If left empty, the file will be placed in the home "
                                    "directory of the user. The directory has to exist "
                                    "on the remote or the check will fail. "
                                    "Example: 'myDirectory' (The file will be uploaded to "
                                    "'~/myDirectory')."
                                ),
                            ),
                        ),
                    },
                ),
            ),
            "get": DictElement(
                required=False,
                parameter_form=Dictionary(
                    migrate=_migrate_get_params,
                    title=Title("Get file from SFTP server"),
                    elements={
                        "remote": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Remote file"),
                                prefill=InputHint("check_mk_testfile"),
                                help_text=Help(
                                    "Remote path to the file to be downloaded. The path is "
                                    "relative to the home directory of the user. If you "
                                    "also enabled 'Put file to SFTP server', you can use "
                                    "the same file for both tests."
                                ),
                            ),
                        ),
                        "local": DictElement(
                            required=True,
                            parameter_form=String(
                                title=Title("Local destination"),
                                help_text=Help(
                                    "Local path to the directory where to put the file, "
                                    'relative to "var/check_mk/active_checks/check_sftp" '
                                    "within the home directory of your site. If left empty, "
                                    "the file will be placed directly in "
                                    '"var/check_mk/active_checks/check_sftp".'
                                ),
                            ),
                        ),
                    },
                ),
            ),
        },
    )


rule_spec_active_check_sftp = ActiveCheck(
    name="sftp",
    title=Title("Check SFTP Service"),
    topic=Topic.APPLICATIONS,
    parameter_form=_make_form_spec_check_sftp,
)
