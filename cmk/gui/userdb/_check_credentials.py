#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

import traceback
from datetime import datetime
from typing import Literal

import cmk.ccc.version as cmk_version
from cmk.ccc.user import UserId

import cmk.utils.paths
from cmk.utils.log.security_event import log_security_event

from cmk.gui.config import active_config
from cmk.gui.customer import customer_api
from cmk.gui.exceptions import MKInternalError, MKUserError
from cmk.gui.htmllib.html import html
from cmk.gui.i18n import _
from cmk.gui.log import logger as gui_logger
from cmk.gui.logged_in import LoggedInUser
from cmk.gui.utils.htpasswd import Htpasswd
from cmk.gui.utils.security_log_events import UserManagementEvent

from cmk.crypto.password import Password

from ._connections import active_connections, get_connection
from ._user_spec import new_user_template
from .ldap_connector import MKLDAPException
from .store import load_user, load_users, save_users

auth_logger = gui_logger.getChild("auth")


def check_credentials(
    username: UserId, password: Password, now: datetime
) -> UserId | Literal[False]:
    """Verify the credentials given by a user using all auth connections"""
    for connection_id, connection in active_connections():
        # None        -> User unknown, means continue with other connectors
        # '<user_id>' -> success
        # False       -> failed
        result = connection.check_credentials(username, password)

        if result is False:
            return False

        if result is None:
            continue

        user_id: UserId = result
        if not isinstance(user_id, str):
            raise MKInternalError(
                _("The username returned by the %s connector is not of type string (%r).")
                % (connection_id, user_id)
            )

        # Check whether or not the user exists (and maybe create it)
        #
        # We have the cases where users exist "partially"
        # a) The htpasswd file of the site may have a username:pwhash data set
        #    and Checkmk does not have a user entry yet
        #
        # In this situation a user account with the "default profile" should be created
        create_non_existing_user(connection_id, user_id, now)

        if not is_customer_user_allowed_to_login(user_id):
            # A CME not assigned with the current sites customer
            # is not allowed to login
            auth_logger.debug("User '%s' is not allowed to login: Invalid customer" % user_id)
            return False

        # Now, after successfull login (and optional user account creation), check whether or
        # not the user is locked.
        if user_locked(user_id):
            auth_logger.debug("User '%s' is not allowed to login: Account locked" % user_id)
            return False  # The account is locked

        return user_id

    return False


def create_non_existing_user(connection_id: str, username: UserId, now: datetime) -> None:
    # Since user_exists also looks into the htpasswd and treats all users that can be found there as
    # "existing users", we don't care about partially known users here and don't create them ad-hoc.
    # The load_users() method will handle this kind of users (TODO: Consolidate this!).
    # Which makes this function basically relevant for users that authenticate using an LDAP
    # connection and do not exist yet.
    if user_exists(username):
        return  # User exists. Nothing to do...

    users = load_users(lock=True)
    users[username] = new_user_template(connection_id)
    users[username].setdefault("alias", username)
    save_users(users, now)

    # Call the sync function for this new user
    connection = get_connection(connection_id)
    try:
        if connection is None:
            raise MKUserError(None, _("Invalid user connection: %s") % connection_id)

        log_security_event(
            UserManagementEvent(
                event="user created",
                affected_user=username,
                acting_user=None,
                connector=connection.type(),
                connection_id=connection_id,
            )
        )

        connection.do_sync(
            add_to_changelog=False,
            only_username=username,
            load_users_func=load_users,
            save_users_func=save_users,
        )
    except MKLDAPException as e:
        _show_exception(connection_id, _("Error during sync"), e, debug=active_config.debug)
    except Exception as e:
        _show_exception(connection_id, _("Error during sync"), e)


# This function is called very often during regular page loads so it has to be efficient
# even when having a lot of users.
#
# When using the multisite authentication with just by Setup created users it would be
# easy, but we also need to deal with users which are only existant in the htpasswd
# file and don't have a profile directory yet.
def user_exists(username: UserId) -> bool:
    if user_exists_according_to_profile(username):
        return True

    return Htpasswd(cmk.utils.paths.htpasswd_file).exists(username)


def user_exists_according_to_profile(username: UserId) -> bool:
    base_path = cmk.utils.paths.profile_dir / username
    return base_path.joinpath("transids.mk").exists() or base_path.joinpath("serial.mk").exists()


def is_customer_user_allowed_to_login(user_id: UserId) -> bool:
    if cmk_version.edition(cmk.utils.paths.omd_root) is not cmk_version.Edition.CME:
        return True

    user = LoggedInUser(user_id)
    if customer_api().is_global(user.customer_id):
        return True

    return customer_api().is_current_customer(user.customer_id)


def _show_exception(connection_id: str, title: str, e: Exception, debug: bool = True) -> None:
    html.show_error(
        "<b>" + connection_id + " - " + title + "</b>"
        "<pre>%s</pre>" % (debug and traceback.format_exc() or e)
    )


def user_locked(user_id: UserId) -> bool:
    return load_user(user_id)["locked"]
