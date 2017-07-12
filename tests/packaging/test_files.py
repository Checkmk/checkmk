import pytest
import os
import subprocess
import re

# Mark all tests in this file to be tests verifying build packages
pytestmark = pytest.mark.packaging

@pytest.mark.parametrize("what", [
    ("rpm"),
    ("deb"),
    ("cma"),
])
def test_package_built(version_path, what):
    files = os.listdir(version_path)
    count = len([ e for e in files if e.startswith("check-mk-") and e.endswith("."+what) ])
    assert count > 0, "Found no %s package in %s" % (what.upper(), version_path)


def _get_package_paths(version_path, what):
    for filename in os.listdir(version_path):
        if filename.startswith("check-mk-") and filename.endswith(".%s" % what):
            yield os.path.join(version_path, filename)


# In case packages grow/shrink this check has to be changed.
@pytest.mark.parametrize("what,min_size,max_size", [
    ("rpm", 119*1024*1024, 210*1024*1024),
    ("deb", 94*1024*1024,  195*1024*1024),
    ("cma", 169*1024*1024, 215*1024*1024),
])
def test_package_sizes(version_path, what, min_size, max_size):
    for pkg in _get_package_paths(version_path, what):
        size = os.stat(pkg).st_size
        assert min_size <= size <= max_size, \
            "Package %s size %s not between %s and %s bytes." % \
                (pkg, size, min_size, max_size)


@pytest.mark.parametrize("what", [
    ("rpm"),
    ("deb"),
])
def test_files_not_in_version_path(version_path, what):
    allowed_patterns = {
        "rpm": [
            "/opt",
            "/opt/omd",
            "/opt/omd/apache",
            "/opt/omd/sites",
            "/opt/omd/versions",
        ],
        "deb": [
            "/",
            "/opt/",
            "/opt/omd/",
            "/usr/",
            "/usr/share/",
            "/usr/share/man/",
            "/usr/share/man/man8/",
            "/usr/share/doc/",
            "/usr/share/doc/check-mk-(raw|enterprise)-*/",
            "/usr/share/doc/check-mk-(raw|enterprise)-*/changelog.gz",
            "/usr/share/doc/check-mk-(raw|enterprise)-*/COPYING.gz",
            "/usr/share/doc/check-mk-(raw|enterprise)-*/TEAM",
            "/usr/share/doc/check-mk-(raw|enterprise)-*/copyright",
            "/usr/share/doc/check-mk-(raw|enterprise)-*/README",
            "/usr/share/doc/check-mk-(raw|enterprise)-*/README.Debian",
            "/etc/",
            "/etc/init.d/",
            "/etc/init.d/check-mk-(raw|enterprise)-*",
        ],
    }

    for pkg in _get_package_paths(version_path, what):
        print "Testing %s" % pkg

        if what == "rpm":
            paths = subprocess.check_output(["rpm", "-qlp", pkg]).splitlines()

        elif what == "deb":
            paths = []
            for line in subprocess.check_output(["dpkg", "-c", pkg]).splitlines():
                paths.append(line.split()[5].lstrip("."))

        for path in paths:
            if not path.startswith("/opt/omd/versions/"):
                is_allowed = any(re.match(p, path) for p in allowed_patterns[what])
                assert is_allowed, "Found unexpected global file: %s" % path


def test_cma_only_contains_version_paths(version_path):
    for pkg in _get_package_paths(version_path, "cma"):
        version = os.path.basename(pkg).split("-")[3]
        for line in subprocess.check_output(["tar", "tvf", pkg]).splitlines():
            path = line.split()[5]
            assert not path.startswith(version + "/")
