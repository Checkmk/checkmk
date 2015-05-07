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
# ails.  You should have  received  a copy of the  GNU  General Public
# License along with GNU Make; see the file  COPYING.  If  not,  write
# to the Free Software Foundation, Inc., 51 Franklin St,  Fifth Floor,
# Boston, MA 02110-1301 USA.

import glob

def download_table(title, paths):
    forms.header(title)
    forms.container()
    for path in paths:
        os_path  = path
        relpath  = path.replace(defaults.agents_dir+'/', '')
        filename = path.split('/')[-1]

        size_kb = os.stat(os_path).st_size / 1024.0

        # FIXME: Rename classes etc. to something generic
        html.write('<div class="ruleset"><div class="text" style="width:250px;">')
        html.write('<a href="agents/%s">%s</a>' % (relpath, filename))
        html.write('<span class=dots>%s</span></div>' % ("." * 100))
        html.write('<div class="rulecount" style="width:30px;">%d&nbsp;KB</div>' % size_kb)
        html.write('</div></div>')
    forms.end()

def mode_download_agents(phase):
    if phase == "title":
        return _("Monitoring Agents")

    elif phase == "buttons":
        global_buttons()
        return

    elif phase == "action":
        return

    html.write('<div class="rulesets">')
    packed = glob.glob(defaults.agents_dir + "/*.deb") \
            + glob.glob(defaults.agents_dir + "/*.rpm") \
            + glob.glob(defaults.agents_dir + "/windows/c*.msi")

    download_table(_("Packed Agents"), packed)

    titles = {
        ''                 : _('Linux / Unix Agents'),
        '/plugins'         : _('Linux / Unix Plugins'),
        '/windows'         : _('Windows Agent'),
        '/windows/plugins' : _('Windows Plugins'),
        '/windows/mrpe'    : _('Windows MRPE Scripts'),
        '/cfg_examples'    : _('Example Configurations'),
        '/z_os'            : _('z/OS'),
        '/sap'             : _('SAP'),
        '/special'         : _('Special Agents'),
    }

    others = []
    for root, dirs, files in os.walk(defaults.agents_dir):
        file_paths = []
        relpath = root.split('agents')[1]
        title = titles.get(relpath, relpath)
        for filename in files:
            path = root + '/' + filename
            if path not in packed and 'deprecated' not in path:
                file_paths.append(path)

        others.append((title, file_paths))

    others.sort()

    for title, file_paths in others:
        if file_paths:
            download_table(title, sorted(file_paths))
    html.write('</div>')

# Don't do anything when the agent bakery exists. Otherwise register
# a simple download page for the default agents
if "agents" not in modes:
    modules.append(
        ("download_agents", _("Monitoring Agents"), "download_agents", "download_agents",
         _("Downloads the Check_MK monitoring agents"))
    )

    modes["download_agents"] = (["download_agents"], mode_download_agents)

    config.declare_permission("wato.download_agents",
        _("Monitoring Agents"),
        _("Download the default Check_MK monitoring agents for Linux, i"
          "Windows and other operating systems."),
       [ "admin", "user", "guest" ])
