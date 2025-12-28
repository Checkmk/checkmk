load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")

def _package_wheel_impl(
        name,
        whl,
        excludes,
        additional_files,
        prefix,
        visibility):
    """Packages a python wheel into our omd site-packages."""
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
        prefix = prefix,
        strip_prefix = filtered_name,
    )

    pkg_tar(
        name = name,
        srcs = [pkg_files_name + "2"] + additional_files,
        visibility = visibility,
    )

package_wheel = macro(
    implementation = _package_wheel_impl,
    attrs = {
        "whl": attr.label(mandatory = True, doc = "Wheel to be packaged."),
        "excludes": attr.label_list(default = [], doc = "Optional, exclude files from packaging."),
        "additional_files": attr.label_list(default = [], doc = "List of additional files to put in the tar."),
        "prefix": attr.string(
            default = "lib/python%s/site-packages" % PYTHON_MAJOR_DOT_MINOR,
            doc = "Where will the python packages be deployed.",
        ),
    },
)
