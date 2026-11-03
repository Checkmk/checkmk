#!/usr/bin/env python3
# Copyright (C) 2026 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import pytest

from cmk.ccc.user import UserId
from cmk.gui.data_source import data_source_registry
from cmk.gui.exceptions import MKUserError
from cmk.gui.type_defs import Row
from cmk.gui.utils.output_funnel import output_funnel
from cmk.gui.views.command.commands import CommandAcknowledge, CommandGroupAcknowledge
from cmk.gui.views.command.form import (
    core_command,
    do_actions,
    get_command_groups,
    should_show_command_form,
)
from cmk.gui.views.store import multisite_builtin_views
from cmk.livestatus_client import ScheduleForcedHostCheck
from cmk.livestatus_client.testing import MockLiveStatusConnection
from tests.testlib.unit.gui.global_settings import logged_in
from tests.unit.cmk.gui.helpers.setup_mode_test_helper import set_request_vars, submit

HOST_ROWS: list[Row] = [
    {"site": "local", "host_name": "alpha"},
    {"site": "local", "host_name": "beta"},
]


def _do_actions(rows: list[Row]) -> tuple[bool, str]:
    with output_funnel.plugged():
        done = do_actions(
            multisite_builtin_views["allhosts"],
            "host",
            rows,
            "view.py?view_name=allhosts",
            debug=False,
        )
        return done, "".join(output_funnel.drain())


@pytest.mark.usefixtures("request_context")
def test_a_command_the_user_may_use_is_issued(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_resched_checks="1", _resched_spread="0")

    with logged_in(with_user[0], "action.reschedule"):
        commands, _confirm_options, _dialog, _executor = core_command(
            "host", HOST_ROWS[0], 0, HOST_ROWS
        )

    assert [type(command) for command in commands] == [ScheduleForcedHostCheck]


@pytest.mark.usefixtures("request_context")
def test_a_command_the_user_may_not_use_is_not_issued(with_user: tuple[UserId, str]) -> None:
    set_request_vars(_resched_checks="1", _resched_spread="0")

    with logged_in(with_user[0], "action.addcomment"), pytest.raises(MKUserError):
        core_command("host", HOST_ROWS[0], 0, HOST_ROWS)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_an_unknown_command_is_rejected() -> None:
    with pytest.raises(MKUserError):
        core_command("host", HOST_ROWS[0], 0, HOST_ROWS)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_a_confirmed_command_is_sent_once_per_selected_row(
    mock_livestatus: MockLiveStatusConnection,
) -> None:
    submit(_add_comment="1", _comment="look here", _do_confirm="1")
    for host_name in ("alpha", "beta"):
        mock_livestatus.expect_query(
            f"COMMAND [...] ADD_HOST_COMMENT;{host_name};...",
            match_type="ellipsis",
            sites=["local"],
        )

    with mock_livestatus():
        done, output = _do_actions(HOST_ROWS)

    assert done
    assert "Successfully sent 2 commands." in output


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_an_unconfirmed_command_asks_for_confirmation_first() -> None:
    set_request_vars(_add_comment="1", _comment="look here")

    done, output = _do_actions(HOST_ROWS)

    assert not done
    assert "Add comment?" in output


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_a_cancelled_command_does_nothing() -> None:
    set_request_vars(_cancel="1")

    assert _do_actions(HOST_ROWS) == (False, "")


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_a_command_without_selected_rows_explains_why_nothing_happened() -> None:
    done, output = _do_actions([])

    assert not done
    assert "No rows selected" in output


@pytest.mark.usefixtures("request_context")
def test_a_user_who_may_not_act_gets_no_commands() -> None:
    done, output = _do_actions(HOST_ROWS)

    assert not done
    assert "You are not allowed to perform actions" in output


@pytest.mark.usefixtures("request_context")
def test_a_user_who_may_not_act_gets_no_command_form() -> None:
    assert not should_show_command_form(data_source_registry["hosts"](), ignore_display_option=True)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_an_admin_gets_the_command_form_of_a_host_view() -> None:
    assert should_show_command_form(data_source_registry["hosts"](), ignore_display_option=True)


@pytest.mark.usefixtures("request_context", "with_admin_login")
def test_commands_are_grouped_for_the_command_menu() -> None:
    assert CommandAcknowledge in get_command_groups("host")[CommandGroupAcknowledge]
