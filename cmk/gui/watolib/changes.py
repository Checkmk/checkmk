#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2014             mk@mathias-kettner.de |
# +------------------------------------------------------------------+
#
# This file is part of Check_MK.
# The official homepage is at http://mathias-kettner.de/check_mk.
#
# check_mk is free software;  you can redistribute it and/or modify it
# under the  terms of the  GNU General Public License  as published by
# the Free Software Foundation in version 2.  check_mk is  distributed
# in the hope that it will be useful, but WITHOUT ANY WARRANTY;  with-
# out even the implied warranty of  MERCHANTABILITY  or  FITNESS FOR A
# PARTICULAR PURPOSE. See the  GNU General Public License for more de-
# tails. You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.
"""Functions for logging changes and keeping the "Activate Changes" state and finally activating changes."""

import ast
import errno
import os
import time
from typing import Dict, List  # pylint: disable=unused-import
import six

import pathlib2 as pathlib

import cmk.utils
import cmk.utils.store as store

import cmk.gui.utils
import cmk.gui.config as config
from cmk.gui.config import SiteId, SiteConfiguration  # pylint: disable=unused-import
from cmk.gui.i18n import _
from cmk.gui.htmllib import HTML
from cmk.gui.globals import html
from cmk.gui.exceptions import MKGeneralException

import cmk.gui.watolib.git
import cmk.gui.watolib.sidebar_reload

from cmk.gui.plugins.watolib import config_domain_registry

var_dir = cmk.utils.paths.var_dir + "/wato/"
audit_log_path = pathlib.Path(var_dir, "log", "audit.log")


def log_entry(linkinfo, action, message, user_id=None):
    # Using attrencode here is against our regular rule to do the escaping
    # at the last possible time: When rendering. But this here is the last
    # place where we can distinguish between HTML() encapsulated (already)
    # escaped / allowed HTML and strings to be escaped.
    message = html.attrencode(message).strip()

    # TODO: Create a more generic referencing
    # linkinfo identifies the object operated on. It can be a Host or a Folder
    # or a text.
    # linkinfo is either a Folder, or a Host or a hostname or None
    if hasattr(linkinfo, "linkinfo"):
        link = linkinfo.linkinfo()
    else:
        link = linkinfo

    write_tokens = (
        time.strftime("%s"),
        link or "-",
        user_id or config.user.id or "-",
        action,
        message.replace("\n", "\\n"),
    )

    # TODO: once we know all of these are unicode, remove this line
    write_tokens = (t if isinstance(t, six.text_type) else t.encode("utf-8") for t in write_tokens)

    store.makedirs(audit_log_path.parent)
    with audit_log_path.open(mode="a", encoding='utf-8') as f:
        audit_log_path.chmod(0o660)
        f.write(u" ".join(write_tokens) + u"\n")


def log_audit(linkinfo, action, message, user_id=None):
    if config.wato_use_git:
        if isinstance(message, HTML):
            message = html.strip_tags(message.value)
        cmk.gui.watolib.git.add_message(message)
    log_entry(linkinfo, action, message, user_id)


def add_change(action_name,
               text,
               obj=None,
               add_user=True,
               need_sync=None,
               need_restart=None,
               domains=None,
               sites=None):

    log_audit(obj, action_name, text, config.user.id if add_user else '')
    cmk.gui.watolib.sidebar_reload.need_sidebar_reload()

    # On each change to the Check_MK configuration mark the agents to be rebuild
    # TODO: Really? Why?
    #if has_agent_bakery():
    #    import cmk.gui.cee.agent_bakery as agent_bakery
    #    agent_bakery.mark_need_to_bake_agents()

    ActivateChangesWriter().add_change(action_name, text, obj, add_user, need_sync, need_restart,
                                       domains, sites)


class ActivateChangesWriter(object):
    def add_change(self, action_name, text, obj, add_user, need_sync, need_restart, domains, sites):
        # Default to a core only change
        if domains is None:
            domains = [config_domain_registry["check_mk"]]

        # All replication sites in case no specific site is given
        if sites is None:
            sites = activation_sites().keys()

        change_id = self._new_change_id()

        for site_id in sites:
            self._add_change_to_site(site_id, change_id, action_name, text, obj, add_user,
                                     need_sync, need_restart, domains)

    def _new_change_id(self):
        return cmk.gui.utils.gen_id()

    def _add_change_to_site(self, site_id, change_id, action_name, text, obj, add_user, need_sync,
                            need_restart, domains):
        # Individual changes may override the domain restart default value
        if need_restart is None:
            need_restart = any([d.needs_activation for d in domains])

        if need_sync is None:
            need_sync = any([d.needs_sync for d in domains])

        def serialize_object(obj):
            if obj is None:
                return None
            return obj.__class__.__name__, obj.ident()

        # Using attrencode here is against our regular rule to do the escaping
        # at the last possible time: When rendering. But this here is the last
        # place where we can distinguish between HTML() encapsulated (already)
        # escaped / allowed HTML and strings to be escaped.
        text = html.attrencode(text)

        SiteChanges(site_id).save_change({
            "id": change_id,
            "action_name": action_name,
            "text": "%s" % text,
            "object": serialize_object(obj),
            "user_id": config.user.id if add_user else None,
            "domains": [d.ident for d in domains],
            "time": time.time(),
            "need_sync": need_sync,
            "need_restart": need_restart,
        })


class SiteChanges(object):
    """Manage persisted changes of a single site"""
    def __init__(self, site_id):
        super(SiteChanges, self).__init__()
        self._site_id = site_id

    def _site_changes_path(self):
        return os.path.join(var_dir, "replication_changes_%s.mk" % self._site_id)

    # TODO: Implement this locking as context manager
    def load(self, lock=False):
        """Parse the site specific changes file

        The file format has been choosen to be able to append changes without
        much cost. This is just a intermmediate format for 1.4.x. In 1.5 we will
        reimplement WATO changes and this very specific file format will vanish."""
        path = self._site_changes_path()

        if lock:
            store.aquire_lock(path)

        changes = []
        try:
            for entry in open(path).read().split("\0"):
                if entry:
                    changes.append(ast.literal_eval(entry))
        except IOError as e:
            if e.errno == errno.ENOENT:
                pass
            else:
                raise
        except:
            if lock:
                store.release_lock(path)
            raise

        return changes

    def save(self, changes):
        # First truncate the file
        open(self._site_changes_path(), "w")

        for change_spec in changes:
            self.save_change(change_spec)

    def save_change(self, change_spec):
        path = self._site_changes_path()
        try:
            store.aquire_lock(path)

            with open(path, "a+") as f:
                f.write(repr(change_spec) + "\0")
                f.flush()
                os.fsync(f.fileno())

            os.chmod(path, 0o660)

        except Exception as e:
            raise MKGeneralException(_("Cannot write file \"%s\": %s") % (path, e))

        finally:
            store.release_lock(path)

    def clear(self):
        try:
            os.unlink(self._site_changes_path())
        except OSError as e:
            if e.errno == errno.ENOENT:
                pass  # Not existant -> OK
            else:
                raise


def add_service_change(host, action_name, text, need_sync=False):
    add_change(action_name, text, obj=host, sites=[host.site_id()], need_sync=need_sync)


def activation_sites():
    # type: () -> Dict[SiteId, SiteConfiguration]
    """Returns the list of sites that are affected by WATO changes
    These sites are shown on activation page and get change entries
    added during WATO changes."""
    return {
        site_id: site
        for site_id, site in config.user.authorized_sites(
            unfiltered_sites=config.configured_sites()).iteritems()
        if config.site_is_local(site_id) or site.get("replication")
    }
