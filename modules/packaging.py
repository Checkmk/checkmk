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

import pprint, tarfile

try:
    import simplejson as json
except ImportError:
    import json

pac_ext = ".mkp"

class PackageException(Exception):
    def __init__(self, reason):
        self.reason = reason
    def __str__(self):
        return self.reason

if omd_root:
    pac_dir = omd_root + "/var/check_mk/packages/"
else:
    pac_dir = var_dir + "/packages/"
try:
    os.makedirs(pac_dir)
except:
    pass

# in case of local directories (OMD) use those instead
package_parts = [ (part, title, perm, ldir and ldir or dir) for part, title, perm, dir, ldir in [
  ( "checks",        "Checks",                    0644, checks_dir,          local_checks_dir ),
  ( "notifications", "Notification scripts",      0755, notifications_dir,   local_notifications_dir ),
  ( "inventory",     "Inventory plugins",         0644, inventory_dir,       local_inventory_dir ),
  ( "checkman",      "Checks' man pages",         0644, check_manpages_dir,  local_check_manpages_dir ),
  ( "agents",        "Agents",                    0755, agents_dir,          local_agents_dir ),
  ( "web",           "Multisite extensions",      0644, web_dir,             local_web_dir ),
  ( "pnp-templates", "PNP4Nagios templates",      0644, pnp_templates_dir,   local_pnp_templates_dir ),
  ( "doc",           "Documentation files",       0644, doc_dir,             local_doc_dir ),
  ( "bin",           "Binaries",                  0755, None,                local_bin_dir ),
  ( "lib",           "Libraries",                 0644, None,                local_lib_dir),
]]

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
            sys.stderr.write("%s\n" % e)
            sys.exit(1)
    else:
        allc = commands.keys()
        allc.sort()
        allc = [ tty_bold + c + tty_normal for c in allc ]
        sys.stderr.write("Invalid packaging command. Allowed are: %s and %s.\n" %
                (", ".join(allc[:-1]), allc[-1]))
        sys.exit(1)


def package_list(args):
    if len(args) > 0:
        for name in args:
            show_package_contents(name)
    else:
        if opt_verbose:
            table = []
            for pacname in all_package_names():
                package = read_package_info(pacname)
                table.append((pacname, package["title"], package["num_files"]))
            print_table(["Name", "Title", "Files"], [ tty_bold, "", "" ], table)
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
        if opt_verbose:
            sys.stdout.write("Files in package %s:\n" % name)
            for part, title, perm, dir in get_package_parts():
                files = package["files"].get(part, [])
                if len(files) > 0:
                    sys.stdout.write("  %s%s%s:\n" % (tty_bold, title, tty_normal))
                    for f in files:
                        sys.stdout.write("    %s\n" % f)
        else:
            for part, title, perm, dir in get_package_parts():
                for fn in package["files"].get(part, []):
                    sys.stdout.write(dir + "/" + fn + "\n")


def package_create(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P create NAME")

    pacname = args[0]
    if read_package_info(pacname):
        raise PackageException("Package %s already existing." % pacname)

    verbose("Creating new package %s...\n" % pacname)
    filelists = {}
    package = {
        "title"                : "Title of %s" % pacname,
        "name"                 : pacname,
        "description"          : "Please add a description here",
        "version"              : "1.0",
        "version.packaged"     : check_mk_version,
        "version.min_required" : check_mk_version,
        "author"               : "Add your name here",
        "download_url"         : "http://example.com/%s/" % pacname,
        "files"                : filelists
    }
    num_files = 0
    for part, title, perm, dir in get_package_parts():
        files = unpackaged_files_in_dir(part, dir)
        filelists[part] = files
        num_files += len(files)
        if len(files) > 0:
            verbose("  %s%s%s:\n" % (tty_bold, title, tty_normal))
            for f in files:
                verbose("    %s\n" % f)


    write_package_info(package)
    verbose("New package %s created with %d files.\n" % (pacname, num_files))
    verbose("Please edit package details in %s%s%s\n" % (tty_bold, pac_dir + pacname, tty_normal))


def package_find(_no_args):
    first = True
    for part, title, perm, dir in get_package_parts():
        files = unpackaged_files_in_dir(part, dir)
        if len(files) > 0:
            if first:
                verbose("Unpackaged files:\n")
                first = False
            verbose("  %s%s%s:\n" % (tty_bold, title, tty_normal))
            for f in files:
                if opt_verbose:
                    sys.stdout.write("    %s\n" % f)
                else:
                    sys.stdout.write("%s/%s\n" % (dir, f))
    if first:
        verbose("No unpackaged files found.\n")


def package_release(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P release NAME")

    pacname = args[0]
    pacpath = pac_dir + pacname
    if not package_exists(pacname):
        raise PackageException("No such package %s." % pacname)
    package = read_package_info(pacname)
    verbose("Releasing files of package %s into freedom...\n" % pacname)
    if opt_verbose:
        for part, title, perm, dir in get_package_parts():
            filenames = package["files"].get(part, [])
            if len(filenames) > 0:
                verbose("  %s%s%s:\n" % (tty_bold, title, tty_normal))
                for f in filenames:
                    verbose("    %s\n" % f)
    remove_package_info(pacname)


def package_exists(pacname):
    pacpath = pac_dir + pacname
    return os.path.exists(pacpath)


def package_pack(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P pack NAME")

    # Make sure, user is not in data directories of Check_MK
    p = os.path.abspath(os.curdir)
    for dir in [var_dir] + [ dir for x,y,perm,dir in get_package_parts() ]:
        if p == dir or p.startswith(dir + "/"):
            raise PackageException("You are in %s!\n"
                               "Please leave the directories of Check_MK before creating\n"
                               "a packet file. Foreign files lying around here will mix up things." % p)

    pacname = args[0]
    package = read_package_info(pacname)
    if not package:
        raise PackageException("Package %s not existing or corrupt." % pacname)
    tarfilename = "%s-%s%s" % (pacname, package["version"], pac_ext)
    verbose("Packing %s into %s...\n" % (pacname, tarfilename))
    create_mkp_file(package, file_name=tarfilename)
    verbose("Successfully created %s\n" % tarfilename)


def create_mkp_file(package, file_name=None, file_object=None):
    package["version.packaged"] = check_mk_version

    def create_info(filename, size):
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

    info_file = fake_file(pprint.pformat(package))
    info = create_info("info", info_file.size())
    tar.addfile(info, info_file)

    info_file = fake_file(json.dumps(package))
    info = create_info("info.json", info_file.size())
    tar.addfile(info, info_file)

    # Now pack the actual files into sub tars
    for part, title, perm, dir in get_package_parts():
        filenames = package["files"].get(part, [])
        if len(filenames) > 0:
            verbose("  %s%s%s:\n" % (tty_bold, title, tty_normal))
            for f in filenames:
                verbose("    %s\n" % f)
            subtarname = part + ".tar"
            subdata = os.popen("tar cf - --dereference --force-local -C '%s' %s" % (dir, " ".join(filenames))).read()
            info = create_info(subtarname, len(subdata))
            tar.addfile(info, fake_file(subdata))
    tar.close()


def package_remove(args):
    if len(args) != 1:
        raise PackageException("Usage: check_mk -P remove NAME")
    pacname = args[0]
    package = read_package_info(pacname)
    if not package:
        raise PackageException("No such package %s." % pacname)

    verbose("Removing package %s...\n" % pacname)
    remove_package(package)
    verbose("Successfully removed package %s.\n" % pacname)


def remove_package(package):
    for part, title, perm, dir in get_package_parts():
        filenames = package["files"].get(part, [])
        if len(filenames) > 0:
            verbose("  %s%s%s\n" % (tty_bold, title, tty_normal))
            for fn in filenames:
                verbose("    %s" % fn)
                try:
                    path = dir + "/" + fn
                    os.remove(path)
                    verbose("\n")
                except Exception, e:
                    if opt_debug:
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

    for part, title, perm, dir in get_package_parts():
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
        raise PackageException("Usage: check_mk -P remove NAME")
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
        verbose("Updating %s from version %s to %s.\n" % (pacname, old_package["version"], package["version"]))
        update = True
    else:
        verbose("Installing %s version %s.\n" % (pacname, package["version"]))
        update = False

    # Before installing check for conflicts
    keep_files = {}
    for part, title, perm, dir in get_package_parts():
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
    for part, title, perm, dir in get_package_parts():
        filenames = package["files"].get(part, [])
        if len(filenames) > 0:
            verbose("  %s%s%s:\n" % (tty_bold, title, tty_normal))
            for fn in filenames:
                verbose("    %s\n" % fn)
            # make sure target directory exists
            if not os.path.exists(dir):
                verbose("    Creating directory %s\n" % dir)
                os.makedirs(dir)
            tarsource = tar.extractfile(part + ".tar")
            subtar = "tar xf - -C %s %s" % (dir, " ".join(filenames))
            tardest = os.popen(subtar, "w")
            while True:
                data = tarsource.read(4096)
                if not data:
                    break
                tardest.write(data)
            tardest.close()

            # Fix permissions of extracted files
            for filename in filenames:
                path = dir + "/" + filename
                has_perm = os.stat(path).st_mode & 07777
                if has_perm != perm:
                    verbose("    Fixing permissions of %s: %04o -> %04o\n" % (path, has_perm, perm))
                    os.chmod(path, perm)


    # In case of an update remove files from old_package not present in new one
    if update:
        for part, title, perm, dir in get_package_parts():
            filenames = old_package["files"].get(part, [])
            keep = keep_files.get(part, [])
            for fn in filenames:
                if fn not in keep:
                    path = dir + "/" + fn
                    verbose("Removing outdated file %s.\n" % path)
                    try:
                        os.remove(path)
                    except Exception, e:
                        sys.stderr.write("Error removing %s: %s\n" % (path, e))

    # Last but not least install package file
    write_package_info(package)
    return package


# Checks whether or not the minimum required Check_MK version is older than the
# current Check_MK version. Raises an exception if not. When the Check_MK version
# can not be parsed or is a daily build, the check is simply passing without error.
def verify_check_mk_version(package):
    min_version = package["version.min_required"]
    cmk_version = check_mk_version

    if is_daily_build_version(min_version):
        min_branch = branch_of_daily_build(min_version)
        if min_branch == "master":
            return # can not check exact version
        else:
            # use the branch name (e.g. 1.2.8 as min version)
            min_version = min_branch

    if is_daily_build_version(cmk_version):
        branch = branch_of_daily_build(cmk_version)
        if branch == "master":
            return # can not check exact version
        else:
            # use the branch name (e.g. 1.2.8 as min version)
            cmk_version = branch

    compatible = True
    try:
        compatible = parse_check_mk_version(min_version) <= parse_check_mk_version(cmk_version)
    except:
        # Be compatible: When a version can not be parsed, then skip this check
        if opt_debug:
            raise
        return

    if not compatible:
        raise PackageException("The package requires Check_MK version %s, "
                               "but you have %s installed." % (min_version, cmk_version))


def files_in_dir(part, dir, prefix = ""):
    if dir == None or not os.path.exists(dir):
        return []

    # Handle case where one part-dir lies below another
    taboo_dirs = [ d for p, t, perm, d in get_package_parts() if p != part ]
    if dir in taboo_dirs:
        return []

    result = []
    files = os.listdir(dir)
    for f in files:
        if f in [ '.', '..' ] or f.startswith('.') or f.endswith('~'):
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
    for part, title, perm, dir in get_package_parts():
        unpackaged[part] = unpackaged_files_in_dir(part, dir)
    return unpackaged


def package_part_info():
    part_info = {}
    for part, title, perm, dir in get_package_parts():
        part_info[part] = {
            "title" : title,
            "permission" : perm,
            "path" : dir,
            "files" : os.listdir(dir),
        }
    return part_info


def unpackaged_files_in_dir(part, dir):
    all = files_in_dir(part, dir)
    packed = packaged_files_in_dir(part)
    return [ f for f in all if f not in packed ]


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
        verbose("Ignoring invalid package file '%s%s'. Please remove it from %s!\n" % (pac_dir, pacname, pac_dir))
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
    try:
        # ast.literal_eval does not execute any code, just reads in passive
        # data structures, so it is safe. But: not available on all supported
        # Python versions
        import ast
    except:
        return eval(python_string)

    return ast.literal_eval(python_string)
