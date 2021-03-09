import os
import subprocess
import re
import pytest  # type: ignore


@pytest.mark.parametrize("what", [
    ("rpm"),
    ("deb"),
    ("cma"),
])
def test_package_built(version_path, what):
    files = os.listdir(version_path)
    count = len([e for e in files if e.startswith("check-mk-") and e.endswith("." + what)])
    assert count > 0, "Found no %s package in %s" % (what.upper(), version_path)


def _get_package_paths(version_path, what):
    for filename in os.listdir(version_path):
        if filename.startswith("check-mk-") and \
           filename.endswith(".%s" % what) and \
           "-dbgsym_" not in filename and \
           "docker" not in filename:
            yield os.path.join(version_path, filename)


def _get_omd_version(cmk_version, pkg_path):
    # Extract the files edition
    edition_short = _edition_short_from_pkg_path(pkg_path)
    demo_suffix = ".demo" if _is_demo(pkg_path) else ""
    return "%s.%s%s" % (cmk_version, edition_short, demo_suffix)


def _is_demo(pkg_path):
    # Is this a demo package?
    return ".demo" in os.path.basename(pkg_path)


def _edition_short_from_pkg_path(pkg_path):
    file_name = os.path.basename(pkg_path)
    if file_name.startswith("check-mk-raw-"):
        return "cre"
    elif file_name.startswith("check-mk-enterprise-"):
        return "cee"
    elif file_name.startswith("check-mk-managed-"):
        return "cme"
    raise NotImplementedError("Could not get edition from package path: %s" % pkg_path)


# In case packages grow/shrink this check has to be changed.
@pytest.mark.parametrize("what,min_size,max_size", [
    ("rpm", 166 * 1024 * 1024, 201 * 1024 * 1024),
    ("deb", 132 * 1024 * 1024, 145 * 1024 * 1024),
    ("cma", 240 * 1024 * 1024, 250 * 1024 * 1024),
    ("tar.gz", 330 * 1024 * 1024, 370 * 1024 * 1024),
])
@pytest.mark.skip("skip until 1.6.0p4 is out, our build container changed somehow")
def test_package_sizes(version_path, what, min_size, max_size):
    sizes = []
    for pkg in _get_package_paths(version_path, what):
        if os.path.basename(pkg).startswith("check-mk-enterprise-"):
            sizes.append(os.stat(pkg).st_size)

    print "%s: Smallest is %s and largest is %s)." % (what, min(sizes), max(sizes))

    for pkg in _get_package_paths(version_path, what):
        if os.path.basename(pkg).startswith("check-mk-enterprise-"):
            size = os.stat(pkg).st_size
            assert min_size <= size <= max_size, \
                "Package %s size %s not between %s and %s bytes." % \
                (pkg, size, min_size, max_size)


@pytest.mark.parametrize("what", [
    ("rpm"),
    ("deb"),
])
def test_files_not_in_version_path(version_path, cmk_version, what):
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

    allowed_patterns = {
        "rpm": [
            "/opt$",
            "/opt/omd$",
            "/opt/omd/apache$",
            "/opt/omd/sites$",
            "/var/lock/mkbackup$",
        ] + version_allowed_patterns,
        "deb": [
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
        ] + version_allowed_patterns,
    }

    for pkg in _get_package_paths(version_path, what):
        print "Testing %s" % pkg

        if what == "rpm":
            paths = subprocess.check_output(["rpm", "-qlp", pkg]).splitlines()

        elif what == "deb":
            paths = []
            for line in subprocess.check_output(["dpkg", "-c", pkg]).splitlines():
                paths.append(line.split()[5].lstrip("."))
        else:
            raise NotImplementedError()

        omd_version = _get_omd_version(cmk_version, pkg)
        print "Checking OMD version: %s" % omd_version

        for path in paths:
            is_allowed = any(
                re.match(p.replace("###OMD_VERSION###", omd_version), path)
                for p in allowed_patterns[what])
            assert is_allowed, "Found unexpected global file: %s in %s" % (path, pkg)


def test_cma_only_contains_version_paths(version_path, cmk_version):
    for pkg in _get_package_paths(version_path, "cma"):
        omd_version = _get_omd_version(cmk_version, pkg)
        files = [
            line.split()[5] for line in subprocess.check_output(["tar", "tvf", pkg]).splitlines()
        ]
        assert len(files) > 1000
        for file_path in files:
            assert file_path.startswith(omd_version + "/")


def test_cma_specific_files(version_path, cmk_version):
    for pkg in _get_package_paths(version_path, "cma"):
        omd_version = _get_omd_version(cmk_version, pkg)
        files = [
            line.split()[5] for line in subprocess.check_output(["tar", "tvf", pkg]).splitlines()
        ]
        assert "%s/cma.info" % omd_version in files
        assert "%s/skel/etc/apache/conf.d/cma.conf" % omd_version in files
        assert "%s/lib/cma/post-install" % omd_version in files

        cma_info = subprocess.check_output(["tar", "xOvzf", pkg, "%s/cma.info" % omd_version])
        if _is_demo(pkg):
            assert "DEMO=1" in cma_info
        else:
            assert "DEMO=1" not in cma_info


def test_src_only_contains_relative_version_paths(version_path):
    for pkg in _get_package_paths(version_path, "tar.gz"):
        prefix = pkg.replace(".tar.gz", "")
        for line in subprocess.check_output(["tar", "tvf", pkg]).splitlines():
            path = line.split()[5]
            assert not path.startswith(prefix + "/")
