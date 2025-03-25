#!/usr/bin/env python3
# Copyright (C) 2019 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

"""This module is meant to be used by components (e.g. active checks, notifications, bakelets)
that support getting credentials from the Check_MK password store.

The password stores primary use is to centralize stored credentials. Instead of spreading the
credentials in the whole configuration, we have this as a central place for sensitive information.

The password store mechanic provides a mechanism for keeping passwords out of the cmdline of a
process, e.g. an active check plug-in. It has been built to extend existing plugins with as small
modificiations as possible. It is built out of two parts:

a) Adding arguments for the command line. This job is done for active checks plugins by
   `cmk.base.core_config._prepare_check_command` and `cmk.agent_based.legacy.v0_unstable.passwordstore_get_cmdline`.

b) Extracting arguments from the command line. This is done by `password_store.replace_passwords`
   for python plugins and for C monitoring plug-ins by the patches which can be found at
   `omd/packages/monitoring-plugins/patches/0003-cmk-password-store.dif`.

   The most interesting part is, that the password store arguments are replaced before the existing
   argument handling of the active check plug-ins is executed. This way we don't have to deal with
   the individual mechanics of the active check plug-ins. We can hook into the entry point of the
   plugin, do our work and leave the rest to the plugin.

Python active check plug-ins need to do something like this before the argv are processed.

  import cmk.utils.password_store
  cmk.utils.password_store.replace_passwords()

  (... use regular argv processing ...)

For cases where the password ID is not received from the command line, for example a configuration
file, there is the `extract` function which can be used like this:

  import cmk.utils.password_store
  password = cmk.utils.password_store.extract("pw_id")

"""

from ._pwstore import ad_hoc_password_id as ad_hoc_password_id
from ._pwstore import core_password_store_path as core_password_store_path
from ._pwstore import extract as extract
from ._pwstore import load as load
from ._pwstore import lookup as lookup
from ._pwstore import lookup_for_bakery as lookup_for_bakery
from ._pwstore import Password as Password
from ._pwstore import password_store_path as password_store_path
from ._pwstore import PasswordId as PasswordId
from ._pwstore import PasswordStore as PasswordStore
from ._pwstore import pending_password_store_path as pending_password_store_path
from ._pwstore import save as save
from .hack import replace_passwords as replace_passwords
