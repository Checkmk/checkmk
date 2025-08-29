load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")

def package_wheel(
        name,
        whl,
        visibility = None,
        additional_files = []):
    """Packages a python wheel into our omd site-packages.

    Args:
        name: Name of this target.
        whl: Wheel to be packaged.
        visibility: The visibility attribute on the target.
        additional_files: List of additional files to be put in the tar.
    """
    whl_filegroup_name = name + "_fg"
    pkg_files_name = name + "_pkg_files"
    whl_filegroup(
        name = whl_filegroup_name,
        whl = whl,
    )
    pkg_files(
        name = pkg_files_name,
        srcs = [whl_filegroup_name],
        prefix = "lib/python%s/site-packages" % PYTHON_MAJOR_DOT_MINOR,
        strip_prefix = whl_filegroup_name,
    )
    pkg_tar(
        name = name,
        srcs = [pkg_files_name] + additional_files,
        visibility = visibility,
    )
