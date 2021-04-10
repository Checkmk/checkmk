#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Copyright (C) 2019 tribe29 GmbH - License: GNU General Public License v2
# This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
# conditions defined in the file COPYING, which is part of this source code package.

########################################
# >>>>>>>>>>>>  IMPORTANT <<<<<<<<<<<<<<
# This script deletes subfolders in the ~/etc/check_mk/conf.d/wato directory
# It should only be used in slave sites. You have been warned...
########################################

# The purpose of this script is to remove WATO folders in slave sites which
# do not have any reference to the site. The positive site effect of this
# operation is a reduced size of the ~/var/check_mk/core/config.mk, which represents
# the configuration for the "Checkmk Check Helpers".
# A smaller configuration results in smaller helper processes

# The deletion of the nonsite folders is always triggered in a hook right before the
# "Activate changes" action, internally named pre-activate-changes. Keep in mind that
# this script delete folders, rules and hosts. Other scripts in the pre-activate-changes
# block might receive outdated information, where all hosts are still present.

# Installation:
# Copy this file to a distributed monitoring slave site in the site folder
# ~/local/share/check_mk/web/plugins/wato
# and restart the apache afterwards. A restart of the monitoring core is also advised,
# since the check helpers are not fully restarted during a core reload.

# The umodified version of this script only creates a logfile in
# ~/var/log/remove_nonsite_folders.log, showing the required actions.
# If you want the script to actually remove the folders you need to change
# the parameter do_remove_folders (just below) to True.


def remove_nonrelated_site_folders(effective_hosts):
    # Note: most of the paths here are hardcorded
    # I do not want to use any helper functions from the WATO world, because
    # they might change over time.

    # Set this true if you actually want to delete folders
    # If you just want to start a dry run, leave this at False and have a
    # look in the logfile
    do_remove_folders = False

    logfile = open(os.path.expanduser("~/var/log/remove_site_folders.log"), "w")

    def log_info(info):
        logfile.write(info + "\n")

    # Is this a master or a viewer site? -> return
    if os.path.exists(cmk.utils.paths.default_config_dir + "/multisite.d/sites.mk"):
        return

    # The own site id is written into the distributed_wato.mk file. If it's missing -> return
    if not os.path.exists(cmk.utils.paths.check_mk_config_dir + "/distributed_wato.mk"):
        return

    # Parse the file with the site name
    file_vars_g = {}
    file_vars = {}
    try:
        exec(
            open(cmk.utils.paths.check_mk_config_dir + "/distributed_wato.mk").read(), file_vars_g,
            file_vars)
    except Exception:
        # Return on any error
        return
    our_site = file_vars.get("distributed_wato_site")

    if not our_site:
        # Looks like the file is empty -> return
        return

    # Get all folders in WATO dir
    config_dir = cmk.utils.paths.check_mk_config_dir + "/wato/"
    all_folders = sorted([x[0][len(config_dir):] for x in os.walk(config_dir)
                         ])[1:]  # Skip first folder (WATO root!)

    keep_folders = set([])
    total_hosts = 0
    for attributes in effective_hosts.values():
        host_folder = attributes[".folder"][".path"]

        host_site = None
        host_tags = attributes.get(".tags", [])
        for tag in host_tags:
            if tag.startswith("site:"):
                host_site = tag.split(":", 1)[1]
                break
        if not host_site:
            # Site host tag not available. Keep this folder
            keep_folders.add(host_folder)
            continue

        if host_site == our_site:
            total_hosts += 1
            keep_folders.add(host_folder)

    def folder_required(foldername):
        for folder in keep_folders:
            if folder.startswith(foldername):
                return True
        return False

    remove_folders = []
    for folder in all_folders:
        if not folder_required(folder):
            remove_folders.append(folder)

    if do_remove_folders:
        import shutil
        for folder in remove_folders:
            if folder:  # This is just another safety mechanism to prevent the deletion of the
                # WATO root folder. The WATO root folder should never appear in this list of folders,
                # because it is filtered out earlier on. Just in case..
                the_folder = "%s%s" % (config_dir, folder)
                if os.path.exists(the_folder):
                    shutil.rmtree(the_folder)

    log_info("Did actually remove folders (no dry run): %s" % do_remove_folders)

    # Log the outcome
    log_info("\nAll folders\n##############")
    log_info("\n".join(all_folders))
    log_info("\nKeep folders\n##############")
    log_info("\n".join(keep_folders))
    log_info("\nRemove folders\n##############")
    log_info("\n".join(remove_folders))
    log_info("\nTotal hosts of current site %s" % total_hosts)


register_hook("pre-activate-changes", remove_nonrelated_site_folders)
