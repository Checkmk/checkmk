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
modificiations as possible."""

from ._pwstore import ad_hoc_password_id as ad_hoc_password_id
from ._pwstore import core_password_store_path as core_password_store_path
from ._pwstore import extract as extract
from ._pwstore import extract_formspec_password as extract_formspec_password
from ._pwstore import load as load
from ._pwstore import lookup as lookup
from ._pwstore import lookup_for_bakery as lookup_for_bakery
from ._pwstore import make_staged_passwords_lookup as make_staged_passwords_lookup
from ._pwstore import Password as Password
from ._pwstore import password_store_path as password_store_path
from ._pwstore import PasswordId as PasswordId
from ._pwstore import pending_password_store_path as pending_password_store_path
from ._pwstore import save as save
from .hack import replace_passwords as replace_passwords
