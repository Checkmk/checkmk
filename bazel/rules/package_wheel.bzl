"""Macro to package Python wheels into OMD site-packages tarballs."""

load("@omd_packages//omd/packages/Python:version.bzl", "PYTHON_MAJOR_DOT_MINOR")
load("@rules_pkg//pkg:mappings.bzl", "pkg_files")
load("@rules_pkg//pkg:tar.bzl", "pkg_tar")
load("@rules_python//python:pip.bzl", "whl_filegroup")
load("//bazel/rules:patchelf.bzl", "set_runpath_tree")

def _package_wheel_impl(
        name,
        whl,
        additional_files,
        rpath,
        visibility):
    """Packages a python wheel into our omd site-packages."""
    whl_filegroup_name = name + "_fg"
    pkg_files_name = name + "_pkg_files"

    whl_filegroup(
        name = whl_filegroup_name,
        whl = whl,
    )

    if rpath:
        runpath_name = name + "_runpath"
        set_runpath_tree(
            name = runpath_name,
            src = ":" + whl_filegroup_name,
            rpath = rpath,
        )
        pkg_files_src = runpath_name
    else:
        pkg_files_src = whl_filegroup_name

    # strip_prefix strips the TreeArtifact's own directory name (the name of
    # whl_filegroup/set_runpath_tree), placing the wheel contents directly under
    # the site-packages prefix.
    pkg_files(
        name = pkg_files_name,
        srcs = [pkg_files_src],
        prefix = "lib/python%s/site-packages" % PYTHON_MAJOR_DOT_MINOR,
        strip_prefix = pkg_files_src,
    )

    pkg_tar(
        name = name,
        srcs = [pkg_files_name] + additional_files,
        mtime = 1767744000,
        portable_mtime = False,
        visibility = visibility,
    )

package_wheel = macro(
    implementation = _package_wheel_impl,
    attrs = {
        "additional_files": attr.label_list(default = [], doc = "List of additional files to put in the tar."),
        "rpath": attr.string(
            default = "",
            doc = "When non-empty, patch all ELF .so files in the wheel with this RUNPATH via set_runpath_tree.",
        ),
        "whl": attr.label(mandatory = True, doc = "Wheel to be packaged."),
    },
)
