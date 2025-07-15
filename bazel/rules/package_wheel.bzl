load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")

def package_wheel(
        name,
        whl,
        excludes = [],
        visibility = None,
        additional_files = []):
    """Packages a python wheel into our omd site-packages.

    Args:
        name: Name of this target.
        whl: Wheel to be packaged.
        excludes: Optional, exclude files from packaging.
        visibility: The visibility attribute on the target.
        additional_files: List of additional files to be put in the tar.
    """
    whl_filegroup_name = name + "_fg"
    filtered_name = name + "_filtered"
    pkg_files_name = name + "_pkg_files"
    whl_filegroup(
        name = whl_filegroup_name,
        whl = whl,
    )
    filter_directory(
        name = filtered_name,
        src = whl_filegroup_name,
        excludes = excludes,
    )

    # Filter_directory creates TreeArtifacts and Stripping
    # of TreeArtifacts is not working.
    # Dus we need to create pkg_files first which then can be
    # stripped and prefixed in the next pkg_files
    pkg_files(
        name = pkg_files_name + "1",
        srcs = [filtered_name],
    )
    pkg_files(
        name = pkg_files_name + "2",
        srcs = [pkg_files_name + "1"],
        prefix = "lib/python%s/site-packages" % PYTHON_MAJOR_DOT_MINOR,
        strip_prefix = filtered_name,
    )
    pkg_tar(
        name = name,
        srcs = [pkg_files_name + "2"] + additional_files,
        visibility = visibility,
    )
