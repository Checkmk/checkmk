"""Macro to package Python wheels into OMD site-packages tarballs."""

load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_pkg//pkg:mappings.bzl", "filter_directory", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")
load("//bazel/rules:patchelf.bzl", "set_runpath_tree")

def _package_wheel_impl(
        name,
        whl,
        excludes,
        additional_files,
        prefix,
        rpath,
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

    if rpath:
        runpath_name = name + "_runpath"
        set_runpath_tree(
            name = runpath_name,
            src = ":" + filtered_name,
            rpath = rpath,
        )
        pkg_files_src = runpath_name
    else:
        pkg_files_src = filtered_name

    # Filter_directory creates TreeArtifacts and Stripping
    # of TreeArtifacts is not working.
    # Dus we need to create pkg_files first which then can be
    # stripped and prefixed in the next pkg_files
    pkg_files(
        name = pkg_files_name + "1",
        srcs = [pkg_files_src],
    )

    pkg_files(
        name = pkg_files_name + "2",
        srcs = [pkg_files_name + "1"],
        prefix = prefix,
        strip_prefix = pkg_files_src,
    )

    pkg_tar(
        name = name,
        srcs = [pkg_files_name + "2"] + additional_files,
        mtime = 1767744000,
        portable_mtime = False,
        visibility = visibility,
    )

package_wheel = macro(
    implementation = _package_wheel_impl,
    attrs = {
        "additional_files": attr.label_list(default = [], doc = "List of additional files to put in the tar."),
        "excludes": attr.label_list(default = [], doc = "Optional, exclude files from packaging."),
        "prefix": attr.string(
            default = "lib/python%s/site-packages" % PYTHON_MAJOR_DOT_MINOR,
            doc = "Where will the python packages be deployed.",
        ),
        "rpath": attr.string(
            default = "",
            doc = "When non-empty, patch all ELF .so files in the wheel with this RUNPATH via set_runpath_tree.",
        ),
        "whl": attr.label(mandatory = True, doc = "Wheel to be packaged."),
    },
)
