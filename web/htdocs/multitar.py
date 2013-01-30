#!/usr/bin/python
# -*- encoding: utf-8; py-indent-offset: 4 -*-
# +------------------------------------------------------------------+
# |             ____ _               _        __  __ _  __           |
# |            / ___| |__   ___  ___| | __   |  \/  | |/ /           |
# |           | |   | '_ \ / _ \/ __| |/ /   | |\/| | ' /            |
# |           | |___| | | |  __/ (__|   <    | |  | | . \            |
# |            \____|_| |_|\___|\___|_|\_\___|_|  |_|_|\_\           |
# |                                                                  |
# | Copyright Mathias Kettner 2013             mk@mathias-kettner.de |
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

# This module contains some helper functions dealing with the creation
# of multi-tier tar files (tar files containing tar files)

import os, tarfile, time, shutil, StringIO

class fake_file:
    def __init__(self, content):
        self.content = content
        self.pointer = 0

    def size(self):
        return len(self.content)

    def read(self, size):
        new_end = self.pointer + size
        data = self.content[self.pointer:new_end]
        self.pointer = new_end
        return data


def create(filename, components):
    tar = tarfile.open(filename, "w:gz")
    for what, name, path in components:
        abspath = os.path.abspath(path)
        if os.path.exists(path):
            if what == "dir":
                basedir = abspath
                filename = "."
            else:
                basedir = os.path.dirname(abspath)
                filename = os.path.basename(abspath)
            subtarname = name + ".tar"
            subdata = os.popen("tar cf - --dereference --force-local -C '%s' '%s'" % \
                               (basedir, filename)).read()

            info = tarfile.TarInfo(subtarname)
            info.mtime = time.time()
            info.uid = 0
            info.gid = 0
            info.size = len(subdata)
            info.mode = 0644
            info.type = tarfile.REGTYPE
            info.name = subtarname
            tar.addfile(info, fake_file(subdata))

def extract_from_buffer(buffer, components):
    stream = StringIO.StringIO()
    stream.write(buffer)
    stream.seek(0)
    extract(tarfile.open(None, "r:gz", stream), components)

def extract_from_file(filename, components):
    extract(tarfile.open(filename, "r:gz"), components)


# Extract a tarball
def extract(tar, components):
    for what, name, path in components:
        try:
            subtarstream = tar.extractfile(name + ".tar")
        except:
            pass # may be missing, e.g. sites.tar is only present
                 # if some sites have been created.

        if what == "dir":
            target_dir = path
        else:
            target_dir = os.path.dirname(path)

        # Remove old stuff
        if os.path.exists(path):
            if what == "dir":
                wipe_directory(path)
            else:
                os.remove(path)
        elif what == "dir":
            os.makedirs(path)

        # Extract without use of temporary files
        subtar = tarfile.open(fileobj = subtarstream)
        subtar.extractall(target_dir)

def wipe_directory(path):
    for entry in os.listdir(path):
        if entry not in [ '.', '..' ]:
            p = path + "/" + entry
            if os.path.isdir(p):
                shutil.rmtree(p)
            else:
                os.remove(p)
