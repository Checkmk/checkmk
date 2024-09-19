load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")

def package_wheel(wheel_target):
    """Packages a python wheel into our omd site-packages."""
    whl_filegroup(
        name = "whl_filegroup",
        whl = wheel_target,
    )

    pkg_files(
        name = "pkg_files",
        srcs = [
            ":whl_filegroup",
        ],
        # TODO: As soon as we have all omd/packages in bazel, we won't need the intermediate install target anymore.
        # Then we can also completely remove the "python3-modules" prefix - currently it will be deployed to $(DESTDIR) via
        # $(PYTHON3_MODULES_INSTALL) in python3-modules.make
        prefix = "python3-modules/lib/python%s/site-packages" % PYTHON_MAJOR_DOT_MINOR,
        strip_prefix = "whl_filegroup",
    )

    pkg_tar(
        name = "pkg_tar",
        srcs = [
            ":pkg_files",
        ],
        visibility = ["//visibility:public"],
    )
