#!/usr/bin/env python3
# Copyright (C) 2024 Checkmk GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

from abc import ABC

from cmk.ccc.site import SiteId


class PseudoUserId(ABC):
    """Alternative type for UserIds

    We have cases where we want something to authenticate to the UI/RestAPI that is not a real user.
    Previously we mostly used automation users for that.
    This is error prone since we rely on certain permissions which admins could change. Besides that
    we needed to store the cleartext passwords in order to use them. These were then synced across
    all remote sites (if sync was enabled...).

    Unfortunately our current auth function does not return User objects but UserIds which is
    basically the username. For these Pseudo users we don't want to have usernames that would then
    need to be reserved... Therefore we now return this class.
    """


class SiteInternalPseudoUser(PseudoUserId):
    """PseudoUser for SiteInternal auth

    This user is authenticated with the `SiteInternalSecret` which is local only and rotated at
    every site start"""


class RemoteSitePseudoUser(PseudoUserId):
    """PseudoUser for remote sites

    The only use-case so far is the agent-updater registration but there we need to forward the
    request to the central site. This used to be done with the automation user"""

    def __init__(self, site_name: SiteId) -> None:
        self.site_name = site_name
