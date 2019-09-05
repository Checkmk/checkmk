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

import os
import ast
import pprint
import sys
import tarfile
import time
import subprocess
import json
from cStringIO import StringIO

import cmk.debug
import cmk.tty as tty
import cmk.paths
import cmk.ec.export

import cmk.log
logger = cmk.log.get_logger(__name__)

import cmk_base.utils

pac_ext = ".mkp"

# TODO: Subclass MKGeneralException()?
class PackageException(Exception):
    def __init__(self, reason):
        self.reason = reason
        super(PackageException, self).__init__(reason)
    def __str__(self):
        return self.reason

pac_dir = cmk.paths.omd_root + "/var/check_mk/packages/"

# TODO: OMD: Pack this path and remote this makedirs call
try:
    os.makedirs(pac_dir)
except:
    pass

# in case of local directories (OMD) use those instead
# TODO: Since we only care about OMD environments: Simplify that -> remove ldir
package_parts = [ (part, title, perm, ldir and ldir or dir) for part, title, perm, dir, ldir in [
  ( "checks",        "Checks",                    0644, cmk.paths.checks_dir,          cmk.paths.local_checks_dir ),
  ( "notifications", "Notification scripts",      0755, cmk.paths.notifications_dir,   cmk.paths.local_notifications_dir ),
  ( "inventory",     "Inventory plugins",         0644, cmk.paths.inventory_dir,       cmk.paths.local_inventory_dir ),
  ( "checkman",      "Checks' man pages",         0644, cmk.paths.check_manpages_dir,  cmk.paths.local_check_manpages_dir ),
  ( "agents",        "Agents",                    0755, cmk.paths.agents_dir,          cmk.paths.local_agents_dir ),
  ( "web",           "Multisite extensions",      0644, cmk.paths.web_dir,             cmk.paths.local_web_dir ),
  ( "pnp-templates", "PNP4Nagios templates",      0644, cmk.paths.pnp_templates_dir,   cmk.paths.local_pnp_templates_dir ),
  ( "doc",           "Documentation files",       0644, cmk.paths.doc_dir,             cmk.paths.local_doc_dir ),
  ( "locales",       "Localizations",             0644, cmk.paths.locale_dir,          cmk.paths.local_locale_dir ),
  ( "bin",           "Binaries",                  0755, None,                          cmk.paths.local_bin_dir ),
  ( "lib",           "Libraries",                 0644, None,                          cmk.paths.local_lib_dir),
  ( "mibs",          "SNMP MIBs",                 0644, None,                          cmk.paths.local_mib_dir),
  ( "alert_handlers", "Alert handlers",           0755, cmk.paths.share_dir + "/alert_handlers",
                                                        cmk.paths.local_share_dir + "/alert_handlers" ),
]]

config_parts = [
    ("ec_rule_packs", "Event Console rule packs", 0644, str(cmk.ec.export.mkp_rule_pack_dir())),
]

package_ignored_files = {
    "lib": [
        "nagios/plugins/README.txt",
        # it's a symlink to the nagios directory. All files would be doubled.
        # So better ignore this directory to prevent confusions.
        "icinga/plugins",
    ],
}

def get_package_parts():
    return [ p for p in package_parts if p[3] != None ]

def packaging_usage():
    sys.stdout.write("""Usage: check_mk [-v] -P|--package COMMAND [ARGS]

Available commands are:
   create NAME      ...  Collect unpackaged files into new package NAME
   pack NAME        ...  Create package file from installed package
   release NAME     ...  Drop installed package NAME, release packaged files
   find             ...  Find and display unpackaged files
   list             ...  List all installed packages
   list NAME        ...  List files of installed package
   list PACK.mkp    ...  List files of uninstalled package file
   show NAME        ...  Show information about installed package
   show PACK.mkp    ...  Show information about uninstalled package file
   install PACK.mkp ...  Install or update package from file PACK.mkp
   remove NAME      ...  Uninstall package NAME

   -v  enables verbose output

Package files are located in %s.
""" % pac_dir)


def do_packaging(args):
    if len(args) == 0:
        packaging_usage()
        sys.exit(1)
    command = args[0]
    args = args[1:]

    commands = {
        "create"  : package_create,
        "release" : package_release,
        "list"    : package_list,
        "find"    : package_find,
        "show"    : package_info,
        "pack"    : package_pack,
        "remove"  : package_remove,
        "install" : package_install,
    }
    f = commands.get(command)
    if f:
        try:
            f(args)
        except PackageException, e:
            logger.error("%s" % e)
            sys.exit(1)
    else:
        allc = commands.keys()
        allc.sort()
        allc = [ tty.bold + c + tty.normal for c in allc ]
        logger.error("Invalid packaging command. Allowed are: %s and %s.",
                                            ", ".join(allc[:-1]), allc[-1])
        sys.exit(1)


def package_list(args):
    if len(args) > 0:
        for name in args:
            show_package_contents(name)
    else:
        if logger.is_verbose():
            table = []
            for pacname in all_package_names():
                package = read_package_info(pacname)
                table.append((pacname, package["title"], package["num_files"]))
            tty.print_table(["Name", "Title", "Files"], [ tty.bold, "", "" ], table)
        else:
            for pacname in all_package_names():
                sys.stdout.write("%s\n" % pacname)


def package_info(args):
    if len(args) == 0:
        raise PackageException("Usage: check_mk -P show NAME|PACKAGE.mkp")
    for name in args:
        show_package_info(name)


def show_package_contents(name):
    show_package(name, False)


def show_package_info(name):
    show_package(name, True)


def show_package(name, show_info = False):
    try:
        if name.endswith(pac_ext):
            tar = tarfile.open(name, "r:gz")
            info = tar.extractfile("info")
            package = parse_package_info(info.read())
        else:
            package = read_package_info(name)
            if not package:
                raise PackageException("No such package %s." % name)
            if show_info:
                sys.stdout.write("Package file:                  %s%s\n" % (pac_dir, name))
    except PackageException:
        raise
    except Exception, e:
        raise PackageException("Cannot open package %s: %s" % (name, e))

    if show_info:
        sys.stdout.write("Name:                          %s\n" % package["name"])
        sys.stdout.write("Version:                       %s\n" % package["version"])
        sys.stdout.write("Packaged on Check_MK Version:  %s\n" % package["version.packaged"])
        sys.stdout.write("Required Check_MK Version:     %s\n" % package["version.min_required"])
        sys.stdout.write("Title:                         %s\n" % package["title"])
        sys.stdout.write("Author:                        %s\n" % package["author"])
        sys.stdout.write("Download-URL:                  %s\n" % package["download_url"])
        sys.stdout.write("Files:                         %s\n" % \
                " ".join([ "%s(%d)" % (part, len(fs)) for part, fs in package["files"].items() ]))
        sys.stdout.write("Description:\n  %s\n" % package["description"])
    else:
        if logger.is_verbose():
            sys.stdout.write("Files in package %s:\n" % name)
            for part, title, _unused_perm, dir in get_package_parts():
                files = package["files"].get(part, [])
                if len(files) > 0:
                    sys.stdout.write("  %s%s%s:\n" % (tty.bold, title, tty.normal))
                    for f in files:
                        sys.stdout.write("    %s\n" % f)
        else:
            for part, title, _unused_perm, dir in get_package_parts():
                for fn in package["files"].get(part, []):
                    sys.stdout.write(dir + "/" + fn + "\n")


def package_create(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P create NAME")

    pacname = args[0]
    if read_package_info(pacname):
        raise PackageException("Package %s already existing." % pacname)

    logger.verbose("Creating new package %s...", pacname)
    filelists = {}
    package = {
        "title"                : "Title of %s" % pacname,
        "name"                 : pacname,
        "description"          : "Please add a description here",
        "version"              : "1.0",
        "version.packaged"     : cmk.__version__,
        "version.min_required" : cmk.__version__,
        "author"               : "Add your name here",
        "download_url"         : "http://example.com/%s/" % pacname,
        "files"                : filelists
    }
    num_files = 0
    for part, title, _unused_perm, dir in get_package_parts():
        files = unpackaged_files_in_dir(part, dir)
        filelists[part] = files
        num_files += len(files)
        if len(files) > 0:
            logger.verbose("  %s%s%s:", tty.bold, title, tty.normal)
            for f in files:
                logger.verbose("    %s", f)


    write_package_info(package)
    logger.verbose("New package %s created with %d files.", pacname, num_files)
    logger.verbose("Please edit package details in %s%s%s", tty.bold, pac_dir + pacname, tty.normal)


def package_find(_no_args):
    first = True
    for part, title, _unused_perm, dir in get_package_parts() + config_parts:
        files = unpackaged_files_in_dir(part, dir)
        if len(files) > 0:
            if first:
                logger.verbose("Unpackaged files:")
                first = False

            logger.verbose("  %s%s%s:", tty.bold, title, tty.normal)
            for f in files:
                if logger.is_verbose():
                    logger.verbose("    %s", f)
                else:
                    logger.info("%s/%s", dir, f)

    if first:
        logger.verbose("No unpackaged files found.")


def release_package(pacname):
    if not pacname or not package_exists(pacname):
        raise PackageException("Package %s not installed or corrupt." % pacname)

    package = read_package_info(pacname)
    logger.verbose("Releasing files of package %s into freedom...", pacname)
    for part, title, _unused_perm, dir_ in get_package_parts() + config_parts:
        filenames = package["files"].get(part, [])
        if len(filenames) > 0:
            logger.verbose("  %s%s%s:", tty.bold, title, tty.normal)
            for f in filenames:
                logger.verbose("    %s", f)
            if part == 'ec_rule_packs':
                cmk.ec.export.release_packaged_rule_packs(filenames)
    remove_package_info(pacname)


def package_release(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P release NAME")
    pacname = args[0]
    release_package(pacname)


def package_exists(pacname):
    pacpath = pac_dir + pacname
    return os.path.exists(pacpath)


def package_pack(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P pack NAME")

    # Make sure, user is not in data directories of Check_MK
    abs_curdir = os.path.abspath(os.curdir)
    for dir in [cmk.paths.var_dir] + [ p[-1] for p in get_package_parts() + config_parts ]:
        if abs_curdir == dir or abs_curdir.startswith(dir + "/"):
            raise PackageException("You are in %s!\n"
                               "Please leave the directories of Check_MK before creating\n"
                               "a packet file. Foreign files lying around here will mix up things." % p)

    pacname = args[0]
    package = read_package_info(pacname)
    if not package:
        raise PackageException("Package %s not existing or corrupt." % pacname)
    tarfilename = "%s-%s%s" % (pacname, package["version"], pac_ext)
    logger.verbose("Packing %s into %s...", pacname, tarfilename)
    create_mkp_file(package, file_name=tarfilename)
    logger.verbose("Successfully created %s", tarfilename)


def create_mkp_file(package, file_name=None, file_object=None):
    package["version.packaged"] = cmk.__version__

    def create_tar_info(filename, size):
        info = tarfile.TarInfo()
        info.mtime = time.time()
        info.uid = 0
        info.gid = 0
        info.size = size
        info.mode = 0644
        info.type = tarfile.REGTYPE
        info.name = filename
        return info

    tar = tarfile.open(name=file_name, fileobj=file_object, mode="w:gz")

    # add the regular info file (Python format)
    info_file = StringIO(pprint.pformat(package))
    info = create_tar_info("info", len(info_file.getvalue()))
    tar.addfile(info, info_file)

    # add the info file a second time (JSON format) for external tools
    info_file = StringIO(json.dumps(package))
    info = create_tar_info("info.json", len(info_file.getvalue()))
    tar.addfile(info, info_file)

    # Now pack the actual files into sub tars
    for part, title, _unused_perm, dir in get_package_parts() + config_parts:
        filenames = package["files"].get(part, [])
        if len(filenames) > 0:
            logger.verbose("  %s%s%s:", tty.bold, title, tty.normal)
            for f in filenames:
                logger.verbose("    %s", f)
            subtarname = part + ".tar"
            subdata = subprocess.check_output(["tar", "cf", "-", "--dereference", "--force-local",
                                               "-C", dir] + filenames)
            info = create_tar_info(subtarname, len(subdata))
            tar.addfile(info, StringIO(subdata))
    tar.close()


def package_remove(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P remove NAME")
    pacname = args[0]
    package = read_package_info(pacname)
    if not package:
        raise PackageException("No such package %s." % pacname)

    logger.verbose("Removing package %s...", pacname)
    remove_package(package)
    logger.verbose("Successfully removed package %s.", pacname)


def remove_package(package):
    for part, title, _unused_perm, dir in get_package_parts() + config_parts:
        filenames = package["files"].get(part, [])
        if len(filenames) > 0:
            logger.verbose("  %s%s%s", tty.bold, title, tty.normal)
            for fn in filenames:
                logger.verbose("    %s", fn)
                try:
                    path = dir + "/" + fn
                    if part == 'ec_rule_packs':
                        cmk.ec.export.remove_packaged_rule_packs(filenames)
                    else:
                        os.remove(path)
                except Exception, e:
                    if cmk.debug.enabled():
                        raise
                    raise Exception("Cannot remove %s: %s\n" % (path, e))

    os.remove(pac_dir + package["name"])


def create_package(package_info):
    pacname = package_info["name"]
    if package_exists(pacname):
        raise PackageException("Packet already exists.")

    validate_package_files(pacname, package_info["files"])
    write_package_info(package_info)


def edit_package(pacname, new_package_info):
    if not package_exists(pacname):
        raise PackageException("No such package")

    # Renaming: check for collision
    if pacname != new_package_info["name"]:
        if package_exists(new_package_info["name"]):
            raise PackageException("Cannot rename package: a package with that name already exists.")

    validate_package_files(pacname, new_package_info["files"])

    remove_package_info(pacname)
    write_package_info(new_package_info)


# Packaged files must either be unpackaged or already
# belong to that package
def validate_package_files(pacname, files):
    packages = {}
    for package_name in all_package_names():
        packages[package_name] = read_package_info(package_name)

    for part, _unused_title, _unused_perm, dir in get_package_parts():
        validate_package_files_part(packages, pacname, part, dir, files.get(part, []))


def validate_package_files_part(packages, pacname, part, dir, rel_paths):
    for rel_path in rel_paths:
        path = dir + "/" + rel_path
        if not os.path.exists(path):
            raise PackageException("File %s does not exist." % path)

        for other_pacname, other_package_info in packages.items():
            for other_rel_path in other_package_info["files"].get(part, []):
                if other_rel_path == rel_path and other_pacname != pacname:
                    raise PackageException("File %s does already belong to package %s" % (path, other_pacname))


def package_install(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P install NAME")
    path = args[0]
    if not os.path.exists(path):
        raise PackageException("No such file %s." % path)

    return install_package(file_name = path)


def install_package(file_name=None, file_object=None):
    tar = tarfile.open(name=file_name, fileobj=file_object, mode="r:gz")
    package = parse_package_info(tar.extractfile("info").read())

    verify_check_mk_version(package)

    pacname = package["name"]
    old_package = read_package_info(pacname)
    if old_package:
        logger.verbose("Updating %s from version %s to %s.", pacname, old_package["version"], package["version"])
        update = True
    else:
        logger.verbose("Installing %s version %s.", pacname, package["version"])
        update = False

    # Before installing check for conflicts
    keep_files = {}
    for part, _unused_title, _unused_perm, dir in get_package_parts() + config_parts:
        packaged = packaged_files_in_dir(part)
        keep = []
        keep_files[part] = keep

        if update:
            old_files = old_package["files"].get(part, [])

        for fn in package["files"].get(part, []):
            path = dir + "/" + fn
            if update and fn in old_files:
                keep.append(fn)
            elif fn in packaged:
                raise PackageException("File conflict: %s is part of another package." % path)
            elif os.path.exists(path):
                raise PackageException("File conflict: %s already existing." % path)


    # Now install files, but only unpack files explicitely listed
    for part, title, perm, dir in get_package_parts() + config_parts:
        filenames = package["files"].get(part, [])
        if len(filenames) > 0:
            logger.verbose("  %s%s%s:", tty.bold, title, tty.normal)
            for fn in filenames:
                logger.verbose("    %s", fn)

            # make sure target directory exists
            if not os.path.exists(dir):
                logger.verbose("    Creating directory %s", dir)
                os.makedirs(dir)

            tarsource = tar.extractfile(part + ".tar")

            tardest = subprocess.Popen(["tar", "xf", "-", "-C", dir] + filenames,
                                       stdin=subprocess.PIPE)
            while True:
                data = tarsource.read(4096)
                if not data:
                    break
                tardest.stdin.write(data)

            tardest.stdin.close()
            tardest.wait()

            # Fix permissions of extracted files
            for filename in filenames:
                path = dir + "/" + filename
                has_perm = os.stat(path).st_mode & 07777
                if has_perm != perm:
                    logger.verbose("    Fixing permissions of %s: %04o -> %04o", path, has_perm, perm)
                    os.chmod(path, perm)

            if part == 'ec_rule_packs':
                cmk.ec.export.add_rule_pack_proxies(filenames)


    # In case of an update remove files from old_package not present in new one
    if update:
        for part, title, perm, dir in get_package_parts() + config_parts:
            filenames = old_package["files"].get(part, [])
            keep = keep_files.get(part, [])
            for fn in filenames:
                if fn not in keep:
                    path = dir + "/" + fn
                    logger.verbose("Removing outdated file %s.", path)
                    try:
                        os.remove(path)
                    except Exception, e:
                        logger.error("Error removing %s: %s", path, e)

            if part == 'ec_rule_packs':
                to_remove = [fn for fn in filenames if fn not in keep]
                cmk.ec.export.remove_packaged_rule_packs(to_remove, delete_export=False)

    # Last but not least install package file
    write_package_info(package)
    return package


# Checks whether or not the minimum required Check_MK version is older than the
# current Check_MK version. Raises an exception if not. When the Check_MK version
# can not be parsed or is a daily build, the check is simply passing without error.
def verify_check_mk_version(package):
    min_version = package["version.min_required"]
    cmk_version = cmk.__version__

    if cmk_base.utils.is_daily_build_version(min_version):
        min_branch = cmk_base.utils.branch_of_daily_build(min_version)
        if min_branch == "master":
            return # can not check exact version
        else:
            # use the branch name (e.g. 1.2.8 as min version)
            min_version = min_branch

    if cmk_base.utils.is_daily_build_version(cmk_version):
        branch = cmk_base.utils.branch_of_daily_build(cmk_version)
        if branch == "master":
            return # can not check exact version
        else:
            # use the branch name (e.g. 1.2.8 as min version)
            cmk_version = branch

    compatible = True
    try:
        compatible = cmk_base.utils.parse_check_mk_version(min_version) \
                        <= cmk_base.utils.parse_check_mk_version(cmk_version)
    except:
        # Be compatible: When a version can not be parsed, then skip this check
        if cmk.debug.enabled():
            raise
        return

    if not compatible:
        raise PackageException("The package requires Check_MK version %s, "
                               "but you have %s installed." % (min_version, cmk_version))


def files_in_dir(part, dir, prefix = ""):
    if dir == None or not os.path.exists(dir):
        return []

    # Handle case where one part-dir lies below another
    taboo_dirs = [ d for p, _unused_t, _unused_perm, d in get_package_parts() + config_parts if p != part ]
    if dir in taboo_dirs:
        return []

    result = []
    files = os.listdir(dir)
    for f in files:
        if f in [ '.', '..' ] or f.startswith('.') or f.endswith('~') or f.endswith(".pyc"):
            continue

        ignored = package_ignored_files.get(part, [])
        if prefix + f in ignored:
            continue

        path = dir + "/" + f
        if os.path.isdir(path):
            result += files_in_dir(part, path, prefix + f + "/")
        else:
            result.append(prefix + f)
    result.sort()
    return result


def unpackaged_files():
    unpackaged = {}
    for part, _unused_title, _unused_perm, dir in get_package_parts() + config_parts:
        unpackaged[part] = unpackaged_files_in_dir(part, dir)
    return unpackaged


def package_part_info():
    part_info = {}
    for part, title, perm, dir in get_package_parts() + config_parts:
        try:
            files = os.listdir(dir)
        except OSError:
            files = []

        part_info[part] = {
            "title"      : title,
            "permission" : perm,
            "path"       : dir,
            "files"      : files,
        }

    return part_info


def unpackaged_files_in_dir(part, dir):
    return [f for f in files_in_dir(part, dir)
            if f not in packaged_files_in_dir(part)]


def packaged_files_in_dir(part):
    result = []
    for pacname in all_package_names():
        package = read_package_info(pacname)
        if package:
            result += package["files"].get(part, [])
    return result


def read_package_info(pacname):
    try:
        package = parse_package_info(file(pac_dir + pacname).read())
        package["name"] = pacname # do not trust package content
        num_files = sum([len(fl) for fl in package["files"].values() ])
        package["num_files"] = num_files
        return package
    except IOError:
        return None
    except Exception:
        logger.verbose("Ignoring invalid package file '%s%s'. Please remove it from %s!", pac_dir, pacname, pac_dir)
        return None


def write_package_info(package):
    file(pac_dir + package["name"], "w").write(pprint.pformat(package) + "\n")


def remove_package_info(pacname):
     os.remove(pac_dir + pacname)


def all_package_names():
    all = [ p for p in os.listdir(pac_dir) if p not in [ '.', '..' ] ]
    all.sort()
    return all


def parse_package_info(python_string):
    return ast.literal_eval(python_string)
