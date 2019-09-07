from __future__ import print_function
import os
import subprocess
import re
import pytest  # type: ignore


def _get_omd_version(cmk_version, package_path):
    # Extract the files edition
    edition_short = _edition_short_from_pkg_path(package_path)
    demo_suffix = ".demo" if _is_demo(package_path) else ""
    return "%s.%s%s" % (cmk_version, edition_short, demo_suffix)


def _is_demo(package_path):
    # Is this a demo package?
    return ".demo" in os.path.basename(package_path)


def _edition_short_from_pkg_path(package_path):
    file_name = os.path.basename(package_path)
    if file_name.startswith("check-mk-raw-"):
        return "cre"
    elif file_name.startswith("check-mk-enterprise-"):
        return "cee"
    elif file_name.startswith("check-mk-managed-"):
        return "cme"
    raise NotImplementedError("Could not get edition from package path: %s" % package_path)


# In case packages grow/shrink this check has to be changed.
@pytest.mark.parametrize("pkg_format,min_size,max_size", [
    ("rpm", 196 * 1024 * 1024, 229 * 1024 * 1024),
    ("deb", 150 * 1024 * 1024, 165 * 1024 * 1024),
    ("cma", 290 * 1024 * 1024, 302 * 1024 * 1024),
    ("tar.gz", 350 * 1024 * 1024, 380 * 1024 * 1024),
])
def test_package_sizes(package_path, pkg_format, min_size, max_size):
    if not package_path.endswith(".%s" % pkg_format):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    if not os.path.basename(package_path).startswith("check-mk-enterprise-"):
        pytest.skip("only testing enterprise packages")

    size = os.stat(package_path).st_size
    assert min_size <= size <= max_size, \
        "Package %s size %s not between %s and %s bytes." % \
        (package_path, size, min_size, max_size)


def test_files_not_in_version_path(package_path, cmk_version):
    if not package_path.endswith(".rpm") and not package_path.endswith(".deb"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    version_allowed_patterns = [
        "/opt/omd/versions/?$",
        "/opt/omd/versions/###OMD_VERSION###/?$",
    ]

    # All files below the standard directories are allowed
    for basedir in ["bin", "etc", "include", "lib", "local", "share", "skel", "tmp", "var"]:
        version_allowed_patterns += [
            "/opt/omd/versions/###OMD_VERSION###/%s/?$" % basedir,
            "/opt/omd/versions/###OMD_VERSION###/%s/.*" % basedir,
        ]

    if package_path.endswith(".rpm"):
        allowed_patterns = [
            "/opt$",
            "/opt/omd$",
            "/opt/omd/apache$",
            "/opt/omd/sites$",
        ] + version_allowed_patterns

        paths = subprocess.check_output(["rpm", "-qlp", package_path]).splitlines()
    elif package_path.endswith(".deb"):
        allowed_patterns = [
            "/$",
            "/opt/$",
            "/opt/omd/$",
            "/opt/omd/apache/$",
            "/opt/omd/sites/$",
            "/usr/$",
            "/usr/share/$",
            "/usr/share/man/$",
            "/usr/share/man/man8/$",
            "/usr/share/doc/$",
            "/usr/share/doc/check-mk-(raw|enterprise|managed)-.*/$",
            "/usr/share/doc/check-mk-(raw|enterprise|managed)-.*/changelog.gz$",
            "/usr/share/doc/check-mk-(raw|enterprise|managed)-.*/COPYING.gz$",
            "/usr/share/doc/check-mk-(raw|enterprise|managed)-.*/TEAM$",
            "/usr/share/doc/check-mk-(raw|enterprise|managed)-.*/copyright$",
            "/usr/share/doc/check-mk-(raw|enterprise|managed)-.*/README.md$",
            "/etc/$",
            "/etc/init.d/$",
            "/etc/init.d/check-mk-(raw|enterprise|managed)-.*$",
        ] + version_allowed_patterns

        paths = []
        for line in subprocess.check_output(["dpkg", "-c", package_path]).splitlines():
            paths.append(line.split()[5].lstrip("."))
    else:
        raise NotImplementedError()

    print("Testing %s" % package_path)

    omd_version = _get_omd_version(cmk_version, package_path)
    print("Checking OMD version: %s" % omd_version)

    for path in paths:
        is_allowed = any(
            re.match(p.replace("###OMD_VERSION###", omd_version), path) for p in allowed_patterns)
        assert is_allowed, "Found unexpected global file: %s in %s" % (path, package_path)


def test_cma_only_contains_version_paths(package_path, cmk_version):
    if not package_path.endswith(".cma"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    omd_version = _get_omd_version(cmk_version, package_path)
    files = [
        line.split()[5]
        for line in subprocess.check_output(["tar", "tvf", package_path]).splitlines()
    ]
    assert len(files) > 1000
    for file_path in files:
        assert file_path.startswith(omd_version + "/")


def test_cma_specific_files(package_path, cmk_version):
    if not package_path.endswith(".cma"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    omd_version = _get_omd_version(cmk_version, package_path)
    files = [
        line.split()[5]
        for line in subprocess.check_output(["tar", "tvf", package_path]).splitlines()
    ]
    assert "%s/cma.info" % omd_version in files
    assert "%s/skel/etc/apache/conf.d/cma.conf" % omd_version in files
    assert "%s/lib/cma/post-install" % omd_version in files

    cma_info = subprocess.check_output(["tar", "xOvzf", package_path, "%s/cma.info" % omd_version])
    if _is_demo(package_path):
        assert "DEMO=1" in cma_info
    else:
        assert "DEMO=1" not in cma_info


def test_src_only_contains_relative_version_paths(package_path):
    if not package_path.endswith(".tar.gz"):
        pytest.skip("%s is another package type" % os.path.basename(package_path))

    prefix = package_path.replace(".tar.gz", "")
    for line in subprocess.check_output(["tar", "tvf", package_path]).splitlines():
        path = line.split()[5]
        assert not path.startswith(prefix + "/")
