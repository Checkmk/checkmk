import os
import ast
import logging
import pprint
import tarfile
import time
import subprocess
import json
from io import BytesIO
import sys
from typing import cast, Any, BinaryIO, Dict, Iterable, List, NamedTuple, Optional, Text  # pylint: disable=unused-import

if sys.version_info[0] >= 3:
    from pathlib import Path  # pylint: disable=import-error,unused-import
else:
    from pathlib2 import Path

import six  # pylint: disable=unused-import

# It's OK to import centralized config load logic
import cmk.ec.export as ec  # pylint: disable=cmk-module-layer-violation
from cmk.utils.log import VERBOSE
import cmk.utils.paths
import cmk.utils.tty as tty
import cmk.utils.werks
import cmk.utils.debug
import cmk.utils.misc
from cmk.utils.exceptions import MKException
from cmk.utils.encoding import ensure_unicode, ensure_bytestr


# TODO: Subclass MKGeneralException()?
class PackageException(MKException):
    pass


logger = logging.getLogger("cmk.utils.packaging")

# order matters! See function _get_permissions
PERM_MAP = (
    (cmk.utils.paths.checks_dir, 0o644),
    (str(cmk.utils.paths.local_checks_dir), 0o644),
    (str(cmk.utils.paths.notifications_dir), 0o755),
    (str(cmk.utils.paths.local_notifications_dir), 0o755),
    (cmk.utils.paths.inventory_dir, 0o644),
    (str(cmk.utils.paths.local_inventory_dir), 0o644),
    (cmk.utils.paths.check_manpages_dir, 0o644),
    (str(cmk.utils.paths.local_check_manpages_dir), 0o644),
    (cmk.utils.paths.agents_dir, 0o755),
    (str(cmk.utils.paths.local_agents_dir), 0o755),
    (cmk.utils.paths.web_dir, 0o644),
    (str(cmk.utils.paths.local_web_dir), 0o644),
    (str(cmk.utils.paths.pnp_templates_dir), 0o644),
    (str(cmk.utils.paths.local_pnp_templates_dir), 0o644),
    (str(cmk.utils.paths.doc_dir), 0o644),
    (str(cmk.utils.paths.local_doc_dir), 0o644),
    (str(cmk.utils.paths.locale_dir), 0o644),
    (str(cmk.utils.paths.local_locale_dir), 0o644),
    (str(cmk.utils.paths.local_bin_dir), 0o755),
    (str(cmk.utils.paths.local_lib_dir / "nagios" / "plugins"), 0o755),
    (str(cmk.utils.paths.local_lib_dir), 0o644),
    (str(cmk.utils.paths.local_mib_dir), 0o644),
    (os.path.join(cmk.utils.paths.share_dir, "alert_handlers"), 0o755),
    (str(cmk.utils.paths.local_share_dir / "alert_handlers"), 0o755),
    (str(ec.mkp_rule_pack_dir()), 0o644),
)


def _get_permissions(path):
    # type: (str) -> int
    """Determine permissions by the first matching beginning of 'path'"""
    for path_begin, perm in PERM_MAP:
        if path.startswith(path_begin):
            return perm
    raise PackageException("could not determine permissions for %r" % path)


PackageName = str
PartName = str
PartPath = str

PackagePart = NamedTuple("PackagePart", [
    ("ident", PartName),
    ("title", str),
    ("path", PartPath),
])

PackageInfo = Dict
Packages = Dict[PackageName, PackageInfo]
PartFiles = List[str]
PackageFiles = Dict[PartName, PartFiles]
PackagePartInfo = Dict[PartName, Any]

_package_parts = [
    PackagePart("checks", "Checks", str(cmk.utils.paths.local_checks_dir)),
    PackagePart("notifications", "Notification scripts",
                str(cmk.utils.paths.local_notifications_dir)),
    PackagePart("inventory", "Inventory plugins", str(cmk.utils.paths.local_inventory_dir)),
    PackagePart("checkman", "Checks' man pages", str(cmk.utils.paths.local_check_manpages_dir)),
    PackagePart("agents", "Agents", str(cmk.utils.paths.local_agents_dir)),
    PackagePart("web", "Multisite extensions", str(cmk.utils.paths.local_web_dir)),
    PackagePart("pnp-templates", "PNP4Nagios templates",
                str(cmk.utils.paths.local_pnp_templates_dir)),
    PackagePart("doc", "Documentation files", str(cmk.utils.paths.local_doc_dir)),
    PackagePart("locales", "Localizations", str(cmk.utils.paths.local_locale_dir)),
    PackagePart("bin", "Binaries", str(cmk.utils.paths.local_bin_dir)),
    PackagePart("lib", "Libraries", str(cmk.utils.paths.local_lib_dir)),
    PackagePart("mibs", "SNMP MIBs", str(cmk.utils.paths.local_mib_dir)),
    PackagePart("alert_handlers", "Alert handlers",
                str(cmk.utils.paths.local_share_dir / "alert_handlers")),
]

_config_parts = [
    PackagePart("ec_rule_packs", "Event Console rule packs", str(ec.mkp_rule_pack_dir())),
]

package_ignored_files = {
    "lib": ["nagios/plugins/README.txt"],
}


def package_dir():
    # type: () -> Path
    return Path(cmk.utils.paths.omd_root, "var", "check_mk", "packages")


def get_config_parts():
    # type: () -> List[PackagePart]
    return _config_parts


def get_package_parts():
    # type: () -> List[PackagePart]
    return _package_parts


def release_package(pacname):
    # type: (PackageName) -> None
    if not pacname or not _package_exists(pacname):
        raise PackageException("Package %s not installed or corrupt." % pacname)

    package = read_package_info(pacname)
    if package is None:
        raise PackageException("Package %s not installed or corrupt." % pacname)
    logger.log(VERBOSE, "Releasing files of package %s into freedom...", pacname)
    for part in get_package_parts() + get_config_parts():
        filenames = package["files"].get(part.ident, [])
        if len(filenames) > 0:
            logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for f in filenames:
                logger.log(VERBOSE, "    %s", f)
            if part.ident == 'ec_rule_packs':
                ec.release_packaged_rule_packs(filenames)
    _remove_package_info(pacname)


def create_mkp_file(package, file_object=None):
    # type: (PackageInfo, BinaryIO) -> None
    package["version.packaged"] = cmk.__version__
    tar = tarfile.open(fileobj=file_object, mode="w:gz")

    def create_tar_info(filename, size):
        # type: (str, int) -> tarfile.TarInfo
        info = tarfile.TarInfo()
        info.mtime = int(time.time())
        info.uid = 0
        info.gid = 0
        info.size = size
        info.mode = 0o644
        info.type = tarfile.REGTYPE
        info.name = filename
        return info

    def add_file(filename, data):
        # type: (str, six.binary_type) -> None
        info_file = BytesIO(data)
        info = create_tar_info(filename, len(info_file.getvalue()))
        tar.addfile(info, info_file)

    # add the regular info file (Python format)
    add_file("info", ensure_bytestr(pprint.pformat(package)))

    # add the info file a second time (JSON format) for external tools
    add_file("info.json", ensure_bytestr(json.dumps(package)))

    # Now pack the actual files into sub tars
    for part in get_package_parts() + get_config_parts():
        filenames = package["files"].get(part.ident, [])
        if len(filenames) > 0:
            logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for f in filenames:
                logger.log(VERBOSE, "    %s", f)
            subdata = subprocess.check_output(
                ["tar", "cf", "-", "--dereference", "--force-local", "-C", part.path] + filenames)
            add_file(part.ident + ".tar", subdata)
    tar.close()


def get_initial_package_info(pacname):
    # type: (str) -> PackageInfo
    return {
        "title": "Title of %s" % pacname,
        "name": pacname,
        "description": "Please add a description here",
        "version": "1.0",
        "version.packaged": cmk.__version__,
        "version.min_required": cmk.__version__,
        "version.usable_until": None,
        "author": "Add your name here",
        "download_url": "http://example.com/%s/" % pacname,
        "files": {},
    }


def remove_package(package):
    # type: (PackageInfo) -> None
    for part in get_package_parts() + get_config_parts():
        filenames = package["files"].get(part.ident, [])
        if len(filenames) > 0:
            logger.log(VERBOSE, "  %s%s%s", tty.bold, part.title, tty.normal)
            for fn in filenames:
                logger.log(VERBOSE, "    %s", fn)
                try:
                    path = part.path + "/" + fn
                    if part.ident == 'ec_rule_packs':
                        _remove_packaged_rule_packs(filenames)
                    else:
                        os.remove(path)
                except Exception as e:
                    if cmk.utils.debug.enabled():
                        raise
                    raise Exception("Cannot remove %s: %s\n" % (path, e))

    (package_dir() / package["name"]).unlink()  # pylint: disable=no-member


def create_package(pkg_info):
    # type: (PackageInfo) -> None
    pacname = pkg_info["name"]
    if _package_exists(pacname):
        raise PackageException("Packet already exists.")

    _validate_package_files(pacname, pkg_info["files"])
    write_package_info(pkg_info)


def edit_package(pacname, new_package_info):
    # type: (PackageName, PackageInfo) -> None
    if not _package_exists(pacname):
        raise PackageException("No such package")

    # Renaming: check for collision
    if pacname != new_package_info["name"]:
        if _package_exists(new_package_info["name"]):
            raise PackageException(
                "Cannot rename package: a package with that name already exists.")

    _validate_package_files(pacname, new_package_info["files"])

    _remove_package_info(pacname)
    write_package_info(new_package_info)


def install_optional_package(package_file_name):
    # type: (Path) -> PackageInfo
    if package_file_name not in [p.name for p in _get_optional_package_paths()]:
        raise PackageException("Optional package %s does not exist" % package_file_name)
    return install_package_by_path(cmk.utils.paths.optional_packages_dir / package_file_name)


def install_package_by_path(package_path):
    # type: (Path) -> PackageInfo
    with package_path.open("rb") as f:
        return install_package(file_object=cast(BinaryIO, f))


def install_package(file_object):
    # type: (BinaryIO) -> PackageInfo
    package = _get_package_info_from_package(file_object)
    file_object.seek(0)

    _verify_check_mk_version(package)

    pacname = package["name"]
    old_package = read_package_info(pacname)
    if old_package:
        logger.log(VERBOSE, "Updating %s from version %s to %s.", pacname, old_package["version"],
                   package["version"])
        update = True
    else:
        logger.log(VERBOSE, "Installing %s version %s.", pacname, package["version"])
        update = False

    tar = tarfile.open(fileobj=file_object, mode="r:gz")

    # Before installing check for conflicts
    keep_files = {}
    for part in get_package_parts() + get_config_parts():
        packaged = _packaged_files_in_dir(part.ident)
        keep = []  # type: List[Text]
        keep_files[part.ident] = keep

        if update and old_package is not None:
            old_files = old_package["files"].get(part.ident, [])

        for fn in package["files"].get(part.ident, []):
            path = os.path.join(part.path, fn)
            if update and fn in old_files:
                keep.append(fn)
            elif fn in packaged:
                raise PackageException("File conflict: %s is part of another package." % path)
            elif os.path.exists(path):
                raise PackageException("File conflict: %s already existing." % path)

    # Now install files, but only unpack files explicitely listed
    for part in get_package_parts() + get_config_parts():
        filenames = package["files"].get(part.ident, [])
        if len(filenames) > 0:
            logger.log(VERBOSE, "  %s%s%s:", tty.bold, part.title, tty.normal)
            for fn in filenames:
                logger.log(VERBOSE, "    %s", fn)

            # make sure target directory exists
            if not os.path.exists(part.path):
                logger.log(VERBOSE, "    Creating directory %s", part.path)
                os.makedirs(part.path)

            tarsource = tar.extractfile(part.ident + ".tar")
            if tarsource is None:
                raise PackageException("Failed to open %s.tar" % part.ident)

            # Important: Do not preserve the tared timestamp. Checkmk needs to know when the files
            # been installed for cache invalidation.
            tardest = subprocess.Popen(["tar", "xf", "-", "--touch", "-C", part.path] + filenames,
                                       stdin=subprocess.PIPE,
                                       shell=False,
                                       close_fds=True)
            if tardest.stdin is None:
                raise PackageException("Failed to open stdin")

            while True:
                data = tarsource.read(4096)
                if not data:
                    break
                tardest.stdin.write(data)

            tardest.stdin.close()
            tardest.wait()

            # Fix permissions of extracted files
            for filename in filenames:
                path = os.path.join(part.path, filename)
                desired_perm = _get_permissions(path)
                has_perm = os.stat(path).st_mode & 0o7777
                if has_perm != desired_perm:
                    logger.log(VERBOSE, "    Fixing permissions of %s: %04o -> %04o", path,
                               has_perm, desired_perm)
                    os.chmod(path, desired_perm)

            if part.ident == 'ec_rule_packs':
                ec.add_rule_pack_proxies(filenames)

    # In case of an update remove files from old_package not present in new one
    if update and old_package is not None:
        for part in get_package_parts() + get_config_parts():
            filenames = old_package["files"].get(part.ident, [])
            keep = keep_files.get(part.ident, [])
            for fn in filenames:
                if fn not in keep:
                    path = os.path.join(part.path, fn)
                    logger.log(VERBOSE, "Removing outdated file %s.", path)
                    try:
                        os.remove(path)
                    except Exception as e:
                        logger.error("Error removing %s: %s", path, e)

            if part.ident == 'ec_rule_packs':
                to_remove = [fn for fn in filenames if fn not in keep]
                _remove_packaged_rule_packs(to_remove, delete_export=False)

    # Last but not least install package file
    write_package_info(package)
    return package


def _remove_packaged_rule_packs(file_names, delete_export=True):
    # type: (Iterable[str], bool) -> None
    """
    This function synchronizes the rule packs in rules.mk and the packaged rule packs
    of a MKP upon deletion of that MKP. When a modified or an unmodified MKP is
    deleted the exported rule pack and the rule pack in rules.mk are both deleted.
    """
    if not file_names:
        return

    rule_packs = ec.load_rule_packs()
    rule_pack_ids = [rp['id'] for rp in rule_packs]
    affected_ids = [os.path.splitext(fn)[0] for fn in file_names]

    for id_ in affected_ids:
        index = rule_pack_ids.index(id_)
        del rule_packs[index]
        if delete_export:
            ec.remove_exported_rule_pack(id_)

    ec.save_rule_packs(rule_packs)


def _get_package_info_from_package(file_object):
    # type: (BinaryIO) -> PackageInfo
    tar = tarfile.open(fileobj=file_object, mode="r:gz")
    package_info_file = tar.extractfile("info")
    if package_info_file is None:
        raise PackageException("Failed to open package info file")
    return parse_package_info(package_info_file.read())


def _validate_package_files(pacname, files):
    # type: (PackageName, PackageFiles) -> None
    """Packaged files must either be unpackaged or already belong to that package"""
    packages = {}  # type: Packages
    for package_name in all_package_names():
        package_info = read_package_info(package_name)
        if package_info is not None:
            packages[package_name] = package_info

    for part in get_package_parts():
        _validate_package_files_part(packages, pacname, part.ident, part.path,
                                     files.get(part.ident, []))


def _validate_package_files_part(packages, pacname, part, directory, rel_paths):
    # type: (Packages, PackageName, PartName, PartPath, PartFiles) -> None
    for rel_path in rel_paths:
        path = os.path.join(directory, rel_path)
        if not os.path.exists(path):
            raise PackageException("File %s does not exist." % path)

        for other_pacname, other_package_info in packages.items():
            for other_rel_path in other_package_info["files"].get(part, []):
                if other_rel_path == rel_path and other_pacname != pacname:
                    raise PackageException("File %s does already belong to package %s" %
                                           (path, other_pacname))


def _verify_check_mk_version(package):
    # type: (PackageInfo) -> None
    """Checks whether or not the minimum required Check_MK version is older than the
    current Check_MK version. Raises an exception if not. When the Check_MK version
    can not be parsed or is a daily build, the check is simply passing without error."""
    min_version = package["version.min_required"]
    cmk_version = str(cmk.__version__)

    if cmk.utils.misc.is_daily_build_version(min_version):
        min_branch = cmk.utils.misc.branch_of_daily_build(min_version)
        if min_branch == "master":
            return  # can not check exact version
        else:
            # use the branch name (e.g. 1.2.8 as min version)
            min_version = min_branch

    if cmk.utils.misc.is_daily_build_version(cmk_version):
        branch = cmk.utils.misc.branch_of_daily_build(cmk_version)
        if branch == "master":
            return  # can not check exact version
        else:
            # use the branch name (e.g. 1.2.8 as min version)
            cmk_version = branch

    compatible = True
    try:
        compatible = cmk.utils.werks.parse_check_mk_version(min_version) \
                        <= cmk.utils.werks.parse_check_mk_version(cmk_version)
    except Exception:
        # Be compatible: When a version can not be parsed, then skip this check
        if cmk.utils.debug.enabled():
            raise
        return

    if not compatible:
        raise PackageException("The package requires Check_MK version %s, "
                               "but you have %s installed." % (min_version, cmk_version))


def get_all_package_infos():
    # type: () -> Packages
    packages = {}
    for package_name in all_package_names():
        packages[package_name] = read_package_info(package_name)

    return {
        "installed": packages,
        "unpackaged": unpackaged_files(),
        "parts": package_part_info(),
        "optional_packages": get_optional_package_infos(),
    }


def get_optional_package_infos():
    # type: () -> Dict[Text, PackageInfo]
    optional = {}
    for pkg_path in _get_optional_package_paths():
        with pkg_path.open("rb") as pkg:
            package_info = _get_package_info_from_package(cast(BinaryIO, pkg))
            optional[ensure_unicode(pkg_path.name)] = package_info

    return optional


def _get_optional_package_paths():
    # type: () -> List[Path]
    if not cmk.utils.paths.optional_packages_dir.exists():
        return []
    return list(cmk.utils.paths.optional_packages_dir.iterdir())


def unpackaged_files():
    # type: () -> Dict[PackageName, List[str]]
    unpackaged = {}
    for part in get_package_parts() + get_config_parts():
        unpackaged[part.ident] = unpackaged_files_in_dir(part.ident, part.path)
    return unpackaged


def package_part_info():
    # type: () -> PackagePartInfo
    part_info = {}  # type: PackagePartInfo
    for part in get_package_parts() + get_config_parts():
        try:
            files = os.listdir(part.path)
        except OSError:
            files = []

        part_info[part.ident] = {
            "title": part.title,
            "permissions": map(_get_permissions, [os.path.join(part.path, f) for f in files]),
            "path": part.path,
            "files": files,
        }

    return part_info


def read_package_info(pacname):
    # type: (PackageName) -> Optional[PackageInfo]
    pkg_info_path = package_dir() / pacname
    try:
        with pkg_info_path.open("r", encoding="utf-8") as f:
            package = parse_package_info(f.read())
        package["name"] = pacname  # do not trust package content
        num_files = sum([len(fl) for fl in package["files"].values()])
        package["num_files"] = num_files
        return package
    except IOError:
        return None
    except Exception as e:
        logger.log(VERBOSE,
                   "Ignoring invalid package file '%s'. Please remove it from %s! Error: %s",
                   pkg_info_path, package_dir(), e)
        return None


def _files_in_dir(part, directory, prefix=""):
    # type: (str, str, str) -> List[str]
    if directory is None or not os.path.exists(directory):
        return []

    # Handle case where one part-directory lies below another
    taboo_dirs = [p.path for p in get_package_parts() + get_config_parts() if p.ident != part]
    if directory in taboo_dirs:
        return []

    result = []  # type: List[str]
    files = os.listdir(directory)
    for f in files:
        if f in ['.', '..'] or f.startswith('.') or f.endswith('~') or f.endswith(".pyc"):
            continue

        ignored = package_ignored_files.get(part, [])
        if prefix + f in ignored:
            continue

        path = directory + "/" + f
        if os.path.isdir(path):
            result += _files_in_dir(part, path, prefix + f + "/")
        else:
            result.append(prefix + f)
    result.sort()
    return result


def unpackaged_files_in_dir(part, directory):
    # type: (PartName, str) -> List[str]
    packaged = set(_packaged_files_in_dir(part))
    return [f for f in _files_in_dir(part, directory) if f not in packaged]


def _packaged_files_in_dir(part):
    # type: (PartName) -> List[str]
    result = []  # type: List[str]
    for pacname in all_package_names():
        package = read_package_info(pacname)
        if package:
            result += package["files"].get(part, [])
    return result


def all_package_names():
    # type: () -> List[str]
    return sorted([p.name for p in package_dir().iterdir()])


def _package_exists(pacname):
    # type: (PackageName) -> bool
    return (package_dir() / pacname).exists()  # pylint: disable=no-member


def write_package_info(package):
    # type: (PackageInfo) -> None
    pkg_info_path = package_dir() / package["name"]
    with pkg_info_path.open("w", encoding="utf-8") as f:
        f.write(ensure_unicode(pprint.pformat(package) + "\n"))


def _remove_package_info(pacname):
    # type: (PackageName) -> None
    (package_dir() / pacname).unlink()  # pylint: disable=no-member


def parse_package_info(python_string):
    # type: (str) -> PackageInfo
    package_info = ast.literal_eval(python_string)
    package_info.setdefault("version.usable_until", None)
    return package_info


def rule_pack_id_to_mkp():
    # type: () -> Dict[str, Any]
    """
    Returns a dictionary of rule pack ID to MKP package for a given package_info.
    Every rule pack is contained exactly once in this mapping. If no corresponding
    MKP exists, the value of that mapping is None.
    """
    package_info = get_all_package_infos()

    def mkp_of(rule_pack_file):
        # type: (str) -> Any
        """Find the MKP for the given file"""
        for mkp, content in package_info.get('installed', {}).items():
            if rule_pack_file in content.get('files', {}).get('ec_rule_packs', []):
                return mkp
        return None

    exported_rule_packs = package_info['parts']['ec_rule_packs']['files']

    return {os.path.splitext(file_)[0]: mkp_of(file_) for file_ in exported_rule_packs}
